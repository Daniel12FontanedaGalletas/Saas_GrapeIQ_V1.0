# Saas_GrapeIQ_V1.0/app/routers/financials.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid

# ¡IMPORTANTE! Asegurarse de que los imports sean correctos
from .. import schemas
from ..services import security
from ..database import get_db_connection
# No necesitamos 'models' directamente aquí porque usamos raw SQL y schemas

router = APIRouter(
    prefix="/api/financials",
    tags=["financials"],
    dependencies=[Depends(security.get_current_active_user)] 
)

# --- GESTIÓN DE PARÁMETROS DE COSTE ---

@router.post("/cost-parameters/", response_model=schemas.CostParameter, status_code=201)
def create_cost_parameter(
    parameter: schemas.CostParameterCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Crea un nuevo parámetro de coste."""
    query = """
        INSERT INTO cost_parameters (tenant_id, parameter_name, value, unit)
        VALUES (%s, %s, %s, %s)
        RETURNING id, parameter_name, value, unit, last_updated
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    str(current_user.tenant_id),
                    parameter.parameter_name,
                    parameter.value,
                    parameter.unit
                ))
                rec = cur.fetchone()
                conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    return schemas.CostParameter(id=rec[0], parameter_name=rec[1], value=rec[2], unit=rec[3], last_updated=rec[4])

@router.get("/cost-parameters/", response_model=List[schemas.CostParameter])
def get_all_cost_parameters(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """Obtiene todos los parámetros de coste."""
    query = "SELECT id, parameter_name, value, unit, last_updated FROM cost_parameters WHERE tenant_id = %s ORDER BY parameter_name"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                recs = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    return [schemas.CostParameter(id=r[0], parameter_name=r[1], value=r[2], unit=r[3], last_updated=r[4]) for r in recs]

@router.put("/cost-parameters/{parameter_id}", response_model=schemas.CostParameter)
def update_cost_parameter(
    parameter_id: uuid.UUID,
    parameter: schemas.CostParameterCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Actualiza un parámetro de coste."""
    query = """
        UPDATE cost_parameters
        SET parameter_name = %s, value = %s, unit = %s, last_updated = NOW()
        WHERE id = %s AND tenant_id = %s
        RETURNING id, parameter_name, value, unit, last_updated
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    parameter.parameter_name,
                    parameter.value,
                    parameter.unit,
                    str(parameter_id),
                    str(current_user.tenant_id)
                ))
                rec = cur.fetchone()
                conn.commit()
        if not rec:
            raise HTTPException(status_code=404, detail="Parámetro no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    return schemas.CostParameter(id=rec[0], parameter_name=rec[1], value=rec[2], unit=rec[3], last_updated=rec[4])

@router.delete("/cost-parameters/{parameter_id}", status_code=204)
def delete_cost_parameter(
    parameter_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Elimina un parámetro de coste."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM cost_parameters WHERE id = %s AND tenant_id = %s",
                    (str(parameter_id), str(current_user.tenant_id))
                )
                conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    return