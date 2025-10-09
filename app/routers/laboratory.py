# Saas_GrapeIQ_V1.0/app/routers/laboratory.py (CORREGIDO)

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
import uuid
import json
from psycopg2.extras import RealDictCursor, Json

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/laboratory",
    tags=["Laboratory"],
    dependencies=[Depends(security.get_current_active_user)]
)

@router.get("/room-conditions/{room_name}", response_model=schemas.RoomCondition)
def get_room_conditions(room_name: str, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ Obtiene las últimas condiciones de temperatura y humedad para una sala específica. """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM room_conditions
                    WHERE tenant_id = %s AND room_name = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (str(current_user.tenant_id), room_name))
                conditions = cur.fetchone()
                if not conditions:
                    raise HTTPException(status_code=404, detail=f"No se encontraron datos para la sala '{room_name}'.")
                return conditions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")


@router.get("/lots", response_model=List[schemas.WineLotInContainer])
def get_lots_for_laboratory(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """
    Obtiene los lotes que están en fase de vinificación o crianza y que tienen
    un contenedor asignado, indicando que están listos para control enológico.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM wine_lots 
                    WHERE tenant_id = %s AND status IN ('En Fermentación', 'En Crianza')
                """, (str(current_user.tenant_id),))
                lots = cur.fetchall()

                lot_ids = [str(lot['id']) for lot in lots]
                if not lot_ids:
                    return []
                
                cur.execute("""
                    SELECT * FROM containers 
                    WHERE tenant_id = %s AND current_lot_id = ANY(%s::uuid[])
                """, (str(current_user.tenant_id), lot_ids))
                containers = cur.fetchall()

                containers_by_lot = {lot_id: [] for lot_id in lot_ids}
                for container in containers:
                    lot_id = str(container['current_lot_id'])
                    if lot_id in containers_by_lot:
                        containers_by_lot[lot_id].append(schemas.Container.model_validate(container))

                lots_with_containers = []
                for lot in lots:
                    lot_id_str = str(lot['id'])
                    if containers_by_lot.get(lot_id_str):
                        lot_schema = schemas.WineLotInContainer.model_validate({**lot, "containers": containers_by_lot[lot_id_str]})
                        lots_with_containers.append(lot_schema)
                
                return lots_with_containers

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

@router.get("/lot-details/{lot_id}")
def get_lot_details_for_laboratory(
    lot_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Obtiene toda la información de laboratorio para un lote específico,
    combinando el registro de vinificación inicial con cada control de fermentación.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Obtener el registro de vinificación base (debería ser solo uno)
                cur.execute("""
                    SELECT * FROM winemaking_logs 
                    WHERE lot_id = %s AND tenant_id = %s
                    ORDER BY log_date ASC
                    LIMIT 1
                """, (str(lot_id), str(current_user.tenant_id)))
                base_winemaking_log = cur.fetchone()

                # 2. Obtener todos los controles de fermentación
                cur.execute("""
                    SELECT *, control_date as date FROM fermentation_controls 
                    WHERE lot_id = %s AND tenant_id = %s
                    ORDER BY control_date DESC
                """, (str(lot_id), str(current_user.tenant_id)))
                fermentation_controls = cur.fetchall()
                
                # 3. Obtener todas las analíticas de laboratorio
                cur.execute("SELECT * FROM lab_analytics WHERE lot_id = %s AND tenant_id = %s ORDER BY analysis_date DESC", (str(lot_id), str(current_user.tenant_id)))
                lab_analytics = cur.fetchall()

                # 4. Combinar los datos
                combined_logs = []
                base_log_data = dict(base_winemaking_log) if base_winemaking_log else {}

                if not fermentation_controls and base_winemaking_log:
                    # Si no hay controles pero sí un log inicial, lo mostramos
                    log_with_date = base_log_data
                    log_with_date['date'] = base_log_data.get('log_date')
                    combined_logs.append(log_with_date)
                else:
                    for control in fermentation_controls:
                        # Hacemos una copia del log base y lo actualizamos con los datos del control
                        full_log = base_log_data.copy()
                        full_log.update(dict(control))
                        combined_logs.append(full_log)

                return {
                    "fermentation_logs": combined_logs,
                    "lab_analytics": [schemas.LabAnalytic.model_validate(la) for la in lab_analytics]
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo detalles del lote: {e}")

@router.post("/fermentation-control", response_model=schemas.FermentationControl, status_code=201)
def create_fermentation_control(
    log: schemas.FermentationControlUnifiedCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Registra una nueva entrada de control de fermentación.
    Los datos de vinificación iniciales se asume que ya existen y no se modifican aquí.
    """
    query = """
        INSERT INTO fermentation_controls (
            id, lot_id, container_id, control_date, temperature, density,
            residual_sugar, potential_alcohol, ph, volatile_acidity,
            free_so2, notes, tenant_id, total_acidity
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                new_id = uuid.uuid4()

                cur.execute(query, (
                    str(new_id), str(log.lot_id), str(log.container_id), log.log_date,
                    log.temperature, log.density, log.residual_sugar, log.potential_alcohol,
                    log.ph, log.volatile_acidity, log.free_so2, log.notes,
                    str(current_user.tenant_id), log.total_acidity
                ))
                new_control = cur.fetchone()
                conn.commit()
                return new_control
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el control de fermentación: {e}")


@router.post("/lab-analytics", response_model=schemas.LabAnalytic, status_code=201)
def create_lab_analytic(
    analytic: schemas.LabAnalyticCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Crea un nuevo registro de analítica de laboratorio (para crianza)."""
    query = """
        INSERT INTO lab_analytics (
            id, lot_id, container_id, analysis_date, alcoholic_degree, total_acidity,
            volatile_acidity, ph, free_so2, total_so2, notes, tenant_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                new_id = uuid.uuid4()
                cur.execute(query, (
                    str(new_id), str(analytic.lot_id), str(analytic.container_id),
                    analytic.analysis_date, analytic.alcoholic_degree, analytic.total_acidity,
                    analytic.volatile_acidity, analytic.ph, analytic.free_so2,
                    analytic.total_so2, analytic.notes, str(current_user.tenant_id)
                ))
                new_analytic = cur.fetchone()
                conn.commit()
                return new_analytic
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar la analítica: {e}")

@router.get("/lot-evolution/{lot_id}")
def get_lot_evolution_data(
    lot_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Obtiene todos los datos históricos de un lote para graficar su evolución. """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT log_date AS date, ph, total_acidity, sugar_level, NULL as volatile_acidity, NULL as free_so2
                    FROM winemaking_logs WHERE lot_id = %s
                    UNION ALL
                    SELECT control_date AS date, ph, total_acidity, NULL as sugar_level, volatile_acidity, free_so2
                    FROM fermentation_controls WHERE lot_id = %s
                    UNION ALL
                    SELECT analysis_date AS date, ph, total_acidity, NULL as sugar_level, volatile_acidity, free_so2
                    FROM lab_analytics WHERE lot_id = %s
                    ORDER BY date ASC
                """, (str(lot_id), str(lot_id), str(lot_id)))
                
                records = cur.fetchall()

                response = {
                    "dates": [rec['date'].strftime('%Y-%m-%d') for rec in records],
                    "ph": [rec['ph'] for rec in records],
                    "total_acidity": [rec['total_acidity'] for rec in records],
                    "volatile_acidity": [rec['volatile_acidity'] for rec in records],
                    "free_so2": [rec['free_so2'] for rec in records],
                    "sugar_level": [rec['sugar_level'] for rec in records],
                }
                return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo datos de evolución: {e}")