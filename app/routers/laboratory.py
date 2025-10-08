# Saas_GrapeIQ_V1.0/app/routers/laboratory.py (CORREGIDO Y MEJORADO)

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
import uuid
import json
from psycopg2.extras import RealDictCursor

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/laboratory",
    tags=["Laboratory"],
    dependencies=[Depends(security.get_current_active_user)]
)

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
    Obtiene toda la información de laboratorio para un lote específico:
    - Registros de vinificación
    - Controles de fermentación
    - Analíticas de laboratorio
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Obtener registros de vinificación
                cur.execute("SELECT * FROM winemaking_logs WHERE lot_id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
                winemaking_logs = cur.fetchall()
                
                # Obtener controles de fermentación
                cur.execute("SELECT * FROM fermentation_controls WHERE lot_id = %s AND tenant_id = %s ORDER BY control_date ASC", (str(lot_id), str(current_user.tenant_id)))
                fermentation_controls = cur.fetchall()
                
                # Obtener analíticas
                cur.execute("SELECT * FROM lab_analytics WHERE lot_id = %s AND tenant_id = %s ORDER BY analysis_date DESC", (str(lot_id), str(current_user.tenant_id)))
                lab_analytics = cur.fetchall()

                return {
                    "winemaking_logs": [schemas.WinemakingLog.model_validate(log) for log in winemaking_logs],
                    "fermentation_controls": [schemas.FermentationControl.model_validate(fc) for fc in fermentation_controls],
                    "lab_analytics": [schemas.LabAnalytic.model_validate(la) for la in lab_analytics]
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo detalles del lote: {e}")


@router.post("/winemaking-log", response_model=schemas.WinemakingLog, status_code=201)
def create_winemaking_log(
    log: schemas.WinemakingLogCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Registra una nueva entrada en el diario de vinificación."""
    query = """
        INSERT INTO winemaking_logs (
            id, lot_id, log_date, sugar_level, total_acidity, ph, reception_temp, added_so2,
            turbidity, color_intensity, aromas, destemming_type, maceration_time, maceration_temp,
            pumping_overs, corrections, yeast_type, enzymes_added, must_sanitary_state,
            sensory_observations, incidents, tenant_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                new_id = uuid.uuid4()
                cur.execute(query, (
                    str(new_id), str(log.lot_id), log.log_date, log.sugar_level, log.total_acidity,
                    log.ph, log.reception_temp, log.added_so2, log.turbidity, log.color_intensity,
                    log.aromas, log.destemming_type, log.maceration_time, log.maceration_temp,
                    json.dumps(log.pumping_overs), log.corrections, log.yeast_type, log.enzymes_added,
                    log.must_sanitary_state, log.sensory_observations, log.incidents,
                    str(current_user.tenant_id)
                ))
                new_log = cur.fetchone()
                conn.commit()
                return new_log
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el registro de vinificación: {e}")