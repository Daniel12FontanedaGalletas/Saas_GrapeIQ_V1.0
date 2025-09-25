# Saas_GrapeIQ_V1.0/app/routers/traceability.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from contextlib import closing
import uuid
import psycopg2

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/traceability",
    tags=["Traceability"],
)

@router.get("/", response_model=schemas.TraceabilityView)
def get_traceability_view(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """
    Obtiene todos los lotes de vino y los agrupa por su estado actual para la vista Kanban.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, grape_variety, vintage_year, status, initial_grape_kg, total_liters, liters_unassigned FROM wine_lots WHERE tenant_id = %s", 
                (str(current_user.tenant_id),)
            )
            all_lots_recs = cur.fetchall()
            
            cur.execute("""
                SELECT c.id, c.name, c.type, c.capacity_liters, c.material, c.location, c.status, c.current_volume, c.current_lot_id
                FROM containers c
                WHERE c.tenant_id = %s AND c.current_lot_id IS NOT NULL
            """, (str(current_user.tenant_id),))
            containers_recs = cur.fetchall()

    all_lots = [
        schemas.WineLot(id=r[0], name=r[1], grape_variety=r[2], vintage_year=r[3], status=r[4], initial_grape_kg=r[5], total_liters=r[6], liters_unassigned=r[7]) 
        for r in all_lots_recs
    ]
    containers = [
        schemas.Container(id=r[0], name=r[1], type=r[2], capacity_liters=r[3], material=r[4], location=r[5], status=r[6], current_volume=r[7], current_lot_id=r[8]) 
        for r in containers_recs
    ]

    view = schemas.TraceabilityView(harvested=[], fermenting=[], aging=[], ready_to_bottle=[], bottled=[])
    for lot in all_lots:
        lot_in_container = schemas.WineLotInContainer(**lot.model_dump(), containers=[c for c in containers if c.current_lot_id == lot.id])
        if lot.status == 'Cosechado':
            view.harvested.append(lot)
        elif lot.status == 'En Fermentación':
            view.fermenting.append(lot_in_container)
        elif lot.status == 'En Crianza':
            view.aging.append(lot_in_container)
        elif lot.status == 'Listo para Embotellar':
            view.ready_to_bottle.append(lot_in_container)
        elif lot.status == 'Embotellado':
            view.bottled.append(lot)
            
    return view

@router.post("/wine-lots", response_model=schemas.WineLot, status_code=201)
def create_wine_lot(lot: schemas.WineLotCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ 
    Crea un nuevo lote de vino a partir de los KG de uva, calculando los litros resultantes.
    """
    total_liters = int(lot.initial_grape_kg // 1.6)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                INSERT INTO wine_lots (name, grape_variety, vintage_year, tenant_id, status, initial_grape_kg, total_liters, liters_unassigned) 
                VALUES (%s, %s, %s, %s, 'Cosechado', %s, %s, %s) 
                RETURNING id, name, grape_variety, vintage_year, status, initial_grape_kg, total_liters, liters_unassigned
            """
            cur.execute(query, (lot.name, lot.grape_variety, lot.vintage_year, str(current_user.tenant_id), lot.initial_grape_kg, total_liters, total_liters))
            rec = cur.fetchone()
            conn.commit()
    return schemas.WineLot(id=rec[0], name=rec[1], grape_variety=rec[2], vintage_year=rec[3], status=rec[4], initial_grape_kg=rec[5], total_liters=rec[6], liters_unassigned=rec[7])

@router.get("/wine-lots", response_model=List[schemas.WineLot])
def get_all_wine_lots(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ Obtiene la lista completa de todos los lotes de vino con sus datos de volumen. """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, grape_variety, vintage_year, status, initial_grape_kg, total_liters, liters_unassigned FROM wine_lots WHERE tenant_id = %s ORDER BY vintage_year DESC, name",
                (str(current_user.tenant_id),)
            )
            recs = cur.fetchall()
    return [schemas.WineLot(id=r[0], name=r[1], grape_variety=r[2], vintage_year=r[3], status=r[4], initial_grape_kg=r[5], total_liters=r[6], liters_unassigned=r[7]) for r in recs]

@router.put("/wine-lots/{lot_id}", response_model=schemas.WineLot)
def update_wine_lot(
    lot_id: uuid.UUID,
    lot_update: schemas.WineLotUpdate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Actualiza los detalles de un lote y recalcula litros si los kg cambian. """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT initial_grape_kg FROM wine_lots WHERE id = %s", (str(lot_id),))
            current_kg_tuple = cur.fetchone()
            if not current_kg_tuple:
                raise HTTPException(status_code=404, detail="Lote de vino no encontrado.")
            current_kg = current_kg_tuple[0]

            new_liters = None
            if lot_update.initial_grape_kg is not None and lot_update.initial_grape_kg != float(current_kg):
                new_liters = int(lot_update.initial_grape_kg // 1.6)

            if new_liters is not None:
                cur.execute(
                    """
                    UPDATE wine_lots SET name = %s, grape_variety = %s, vintage_year = %s, initial_grape_kg = %s, total_liters = %s, liters_unassigned = %s
                    WHERE id = %s AND tenant_id = %s
                    RETURNING id, name, grape_variety, vintage_year, status, initial_grape_kg, total_liters, liters_unassigned
                    """,
                    (lot_update.name, lot_update.grape_variety, lot_update.vintage_year, lot_update.initial_grape_kg, new_liters, new_liters, str(lot_id), str(current_user.tenant_id))
                )
            else:
                cur.execute(
                    """
                    UPDATE wine_lots SET name = %s, grape_variety = %s, vintage_year = %s 
                    WHERE id = %s AND tenant_id = %s
                    RETURNING id, name, grape_variety, vintage_year, status, initial_grape_kg, total_liters, liters_unassigned
                    """,
                    (lot_update.name, lot_update.grape_variety, lot_update.vintage_year, str(lot_id), str(current_user.tenant_id))
                )
            
            rec = cur.fetchone()
            conn.commit()

    if not rec:
        raise HTTPException(status_code=404, detail="Lote de vino no encontrado durante la actualización.")
    return schemas.WineLot(id=rec[0], name=rec[1], grape_variety=rec[2], vintage_year=rec[3], status=rec[4], initial_grape_kg=rec[5], total_liters=rec[6], liters_unassigned=rec[7])

@router.put("/wine-lots/{lot_id}/status", response_model=schemas.WineLot)
def update_wine_lot_status(
    lot_id: uuid.UUID,
    status_update: schemas.WineLotStatusUpdate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user),
):
    """ Actualiza el estado de un lote de vino. """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE wine_lots SET status = %s WHERE id = %s AND tenant_id = %s RETURNING id, name, grape_variety, vintage_year, status",
                (status_update.new_status, str(lot_id), str(current_user.tenant_id))
            )
            rec = cur.fetchone()
            conn.commit()
    if not rec:
        raise HTTPException(status_code=404, detail="Lote de vino no encontrado.")
    return schemas.WineLot(id=rec[0], name=rec[1], grape_variety=rec[2], vintage_year=rec[3], status=rec[4])

# --- ¡FUNCIÓN AÑADIDA QUE SOLUCIONA EL ERROR 405! ---
@router.delete("/wine-lots/{lot_id}", status_code=204)
def delete_wine_lot(
    lot_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Elimina un lote de vino. """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Primero, desasociar el lote de cualquier contenedor para evitar errores de clave foránea.
            cur.execute(
                "UPDATE containers SET current_lot_id = NULL, status = 'vacío', current_volume = 0 WHERE current_lot_id = %s AND tenant_id = %s",
                (str(lot_id), str(current_user.tenant_id))
            )
            # Luego, eliminar cualquier registro de movimiento asociado a este lote.
            cur.execute(
                "DELETE FROM movements WHERE lot_id = %s AND tenant_id = %s",
                (str(lot_id), str(current_user.tenant_id))
            )
            # Finalmente, eliminar el lote de vino.
            cur.execute(
                "DELETE FROM wine_lots WHERE id = %s AND tenant_id = %s",
                (str(lot_id), str(current_user.tenant_id))
            )
            conn.commit()
    return