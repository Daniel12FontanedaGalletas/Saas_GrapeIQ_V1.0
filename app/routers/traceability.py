# Saas_GrapeIQ_V1.0/app/routers/traceability.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
from psycopg2.extras import RealDictCursor

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/traceability",
    tags=["Trazabilidad"],
    dependencies=[Depends(security.get_current_active_user)]
)

@router.get("/kanban-view/", response_model=schemas.TraceabilityView)
def get_traceability_kanban_view(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """
    Obtiene todos los lotes de vino y los agrupa por su estado actual para la vista Kanban.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name FROM parcels WHERE tenant_id = %s", (str(current_user.tenant_id),))
                parcels = {str(p['id']): p['name'] for p in cur.fetchall()}

                cur.execute("SELECT * FROM wine_lots WHERE tenant_id = %s", (str(current_user.tenant_id),))
                all_lots_recs = cur.fetchall()
                
                cur.execute("""
                    SELECT id, name, type, capacity_liters, material, location, status, current_volume, current_lot_id
                    FROM containers
                    WHERE tenant_id = %s AND current_lot_id IS NOT NULL
                """, (str(current_user.tenant_id),))
                containers_recs = cur.fetchall()

        containers_by_lot_id = {}
        for cont in containers_recs:
            lot_id = str(cont['current_lot_id'])
            if lot_id not in containers_by_lot_id:
                containers_by_lot_id[lot_id] = []
            containers_by_lot_id[lot_id].append(schemas.Container(**cont))

        view = schemas.TraceabilityView(harvested=[], fermenting=[], aging=[], ready_to_bottle=[], bottled=[])
        
        for lot_rec in all_lots_recs:
            lot_rec['origin_parcel_name'] = parcels.get(str(lot_rec.get('origin_parcel_id')))
            lot_id_str = str(lot_rec['id'])
            
            status = lot_rec['status']
            if status == 'Cosechado':
                view.harvested.append(schemas.WineLot(**lot_rec))
            elif status in ['En Fermentación', 'En Crianza', 'Listo para Embotellar']:
                lot_with_containers = schemas.WineLotInContainer(
                    **lot_rec, 
                    containers=containers_by_lot_id.get(lot_id_str, [])
                )
                if status == 'En Fermentación':
                    view.fermenting.append(lot_with_containers)
                elif status == 'En Crianza':
                    view.aging.append(lot_with_containers)
                else:
                    view.ready_to_bottle.append(lot_with_containers)
            elif status == 'Embotellado':
                view.bottled.append(schemas.WineLot(**lot_rec))
                
        return view
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos en Trazabilidad: {e}")


# --- CORRECCIÓN AQUÍ ---
# El método debe ser GET, no POST, para que la interfaz pueda solicitar la lista de vinos.
@router.get("/wine-lots", response_model=List[schemas.WineLot])
def get_all_wine_lots(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    query = "SELECT * FROM wine_lots WHERE tenant_id = %s ORDER BY vintage_year DESC, name"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                lots = cur.fetchall()
                return lots
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")

@router.post("/wine-lots/", response_model=schemas.WineLot, status_code=201)
def create_wine_lot(lot: schemas.WineLotCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    total_liters = lot.initial_grape_kg / 1.6
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    INSERT INTO wine_lots (id, name, grape_variety, vintage_year, tenant_id, status, initial_grape_kg, total_liters, liters_unassigned, origin_parcel_id) 
                    VALUES (%s, %s, %s, %s, %s, 'Cosechado', %s, %s, %s, %s) RETURNING *
                """
                cur.execute(query, (str(uuid.uuid4()), lot.name, lot.grape_variety, lot.vintage_year, str(current_user.tenant_id), lot.initial_grape_kg, total_liters, total_liters, lot.origin_parcel_id))
                new_lot = cur.fetchone()
                conn.commit()
                return new_lot
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el lote: {e}")


@router.put("/wine-lots/{lot_id}/status", response_model=schemas.WineLot)
def update_wine_lot_status(lot_id: uuid.UUID, status_update: schemas.WineLotStatusUpdate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("UPDATE wine_lots SET status = %s WHERE id = %s AND tenant_id = %s RETURNING *",
                            (status_update.new_status, str(lot_id), str(current_user.tenant_id)))
                updated_lot = cur.fetchone()
                conn.commit()
                if not updated_lot:
                    raise HTTPException(status_code=404, detail="Lote no encontrado.")
                return updated_lot
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar estado: {e}")


@router.delete("/wine-lots/{lot_id}", status_code=204)
def delete_wine_lot(lot_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE products SET wine_lot_origin_id = NULL WHERE wine_lot_origin_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                cur.execute("DELETE FROM movements WHERE lot_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                cur.execute("DELETE FROM wine_lots WHERE id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Lote no encontrado para eliminar.")
                conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar lote: {e}")