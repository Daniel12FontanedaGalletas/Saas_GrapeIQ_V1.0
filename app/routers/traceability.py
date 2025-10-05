# Saas_GrapeIQ_V1.0/app/routers/traceability.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
from psycopg2.extras import RealDictCursor
import psycopg2

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/traceability",
    tags=["Trazabilidad"],
    dependencies=[Depends(security.get_current_active_user)]
)

# --- VISTA KANBAN Y GESTIÓN DE LOTES ---

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
                cur.execute(query, (str(uuid.uuid4()), lot.name, lot.grape_variety, lot.vintage_year, str(current_user.tenant_id), lot.initial_grape_kg, total_liters, total_liters, str(lot.origin_parcel_id)))
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

# =================================================================
# INICIO DE LA CORRECCIÓN
# =================================================================
@router.delete("/wine-lots/{lot_id}", status_code=204)
def delete_wine_lot(lot_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """
    Elimina un lote de vino y toda su información asociada, liberando los contenedores.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE containers SET current_lot_id = NULL, current_volume = 0, status = 'vacío' WHERE current_lot_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                cur.execute("UPDATE products SET wine_lot_origin_id = NULL WHERE wine_lot_origin_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                cur.execute("DELETE FROM movements WHERE lot_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                cur.execute("DELETE FROM lab_analytics WHERE lot_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                cur.execute("DELETE FROM costs WHERE related_lot_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                cur.execute("DELETE FROM wine_lots WHERE id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar lote: {e}")

@router.put("/wine-lots/{lot_id}/prepare-for-bottling", response_model=schemas.WineLot)
def prepare_lot_for_bottling(lot_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """
    Prepara el vino en barricas para embotellar. Si queda vino en depósitos, 
    divide el lote para gestionar las barricas de forma independiente.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM wine_lots WHERE id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                original_lot = cur.fetchone()
                if not original_lot:
                    raise HTTPException(status_code=404, detail="Lote no encontrado.")

                cur.execute("SELECT * FROM containers WHERE current_lot_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                all_containers = cur.fetchall()
                
                barrels = [c for c in all_containers if c['type'] == 'Barrica' and float(c['current_volume'] or 0) > 0]
                tanks = [c for c in all_containers if c['type'] == 'Depósito' and float(c['current_volume'] or 0) > 0]

                if not barrels:
                    raise HTTPException(status_code=400, detail="Este lote no tiene vino en barricas para preparar.")

                if tanks:
                    total_volume_in_barrels = sum(float(b['current_volume'] or 0) for b in barrels)
                    new_lot_id = uuid.uuid4()
                    new_lot_name = f"{original_lot['name']} (Barricas)"
                    
                    original_total_liters = float(original_lot['total_liters'] or 0)
                    proportion_in_barrels = total_volume_in_barrels / original_total_liters if original_total_liters > 0 else 0
                    
                    new_lot_initial_kg = float(original_lot['initial_grape_kg'] or 0) * proportion_in_barrels
                    
                    cur.execute(
                        """
                        INSERT INTO wine_lots (id, name, grape_variety, vintage_year, status, tenant_id, origin_parcel_id, initial_grape_kg, total_liters, liters_unassigned)
                        VALUES (%s, %s, %s, %s, 'Listo para Embotellar', %s, %s, %s, %s, 0) RETURNING *
                        """,
                        (str(new_lot_id), new_lot_name, original_lot['grape_variety'], original_lot['vintage_year'], str(current_user.tenant_id), str(original_lot['origin_parcel_id']) if original_lot['origin_parcel_id'] else None, new_lot_initial_kg, total_volume_in_barrels)
                    )
                    new_lot = cur.fetchone()

                    barrel_ids = [str(b['id']) for b in barrels]
                    cur.execute("UPDATE containers SET current_lot_id = %s WHERE id = ANY(%s::uuid[])", (str(new_lot_id), barrel_ids))
                    
                    remaining_liters = original_total_liters - total_volume_in_barrels
                    remaining_initial_kg = float(original_lot['initial_grape_kg'] or 0) - new_lot_initial_kg
                    cur.execute(
                        "UPDATE wine_lots SET total_liters = %s, initial_grape_kg = %s WHERE id = %s",
                        (remaining_liters, remaining_initial_kg, str(lot_id))
                    )
                    
                    conn.commit()
                    return new_lot
                else:
                    cur.execute(
                        "UPDATE wine_lots SET status = 'Listo para Embotellar' WHERE id = %s RETURNING *", (str(lot_id),)
                    )
                    updated_lot = cur.fetchone()
                    conn.commit()
                    return updated_lot

    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        if isinstance(error, HTTPException): raise error
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(error)}")
# =================================================================
# FIN DE LA CORRECCIÓN
# =================================================================

# --- NUEVOS ENDPOINTS PARA TRAZABILIDAD AVANZADA ---

@router.post("/lab-analytics/", response_model=schemas.LabAnalytic, status_code=201)
def add_lab_analytic(analytic: schemas.LabAnalyticCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """Registra un nuevo análisis de laboratorio para un lote de vino."""
    query = """
        INSERT INTO lab_analytics (id, lot_id, analysis_date, alcoholic_degree, total_acidity, volatile_acidity, ph, free_so2, total_so2, notes, tenant_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                new_id = str(uuid.uuid4())
                cur.execute(query, (new_id, str(analytic.lot_id), analytic.analysis_date, analytic.alcoholic_degree, analytic.total_acidity, analytic.volatile_acidity, analytic.ph, analytic.free_so2, analytic.total_so2, analytic.notes, str(current_user.tenant_id)))
                new_analytic = cur.fetchone()
                conn.commit()
                return new_analytic
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el análisis: {e}")

@router.get("/dry-goods/", response_model=List[schemas.DryGood])
def get_all_dry_goods(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """Obtiene todos los lotes de materiales secos (botellas, corchos, etc.)."""
    query = "SELECT * FROM dry_goods WHERE tenant_id = %s ORDER BY material_type"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener materiales: {e}")

@router.post("/bottling-events/", response_model=schemas.BottlingEvent, status_code=201)
def record_bottling_event(event: schemas.BottlingEventCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """Registra un evento de embotellado completo con todos sus detalles de trazabilidad."""
    query = """
        INSERT INTO bottling_events (id, lot_id, product_id, official_lot_number, dissolved_oxygen, bottle_lot_id, cork_lot_id, capsule_lot_id, label_lot_id, retained_samples, tenant_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                new_id = str(uuid.uuid4())
                cur.execute(query, (new_id, str(event.lot_id), str(event.product_id), event.official_lot_number, event.dissolved_oxygen, str(event.bottle_lot_id) if event.bottle_lot_id else None, str(event.cork_lot_id) if event.cork_lot_id else None, str(event.capsule_lot_id) if event.capsule_lot_id else None, str(event.label_lot_id) if event.label_lot_id else None, event.retained_samples, str(current_user.tenant_id)))
                new_event = cur.fetchone()
                conn.commit()
                return new_event
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar el embotellado: {e}")