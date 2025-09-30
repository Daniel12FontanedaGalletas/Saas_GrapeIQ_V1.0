# Saas_GrapeIQ_V1.0/app/routers/financials.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
import uuid
import math
from collections import defaultdict

from .. import schemas
from ..services import security
from ..database import get_db_connection
from ..services.security import get_current_active_user
from contextlib import closing

router = APIRouter(
    prefix="/api/financials",
    tags=["Financials"],
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
        INSERT INTO cost_parameters (tenant_id, parameter_name, category, value, unit)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, parameter_name, category, value, unit, last_updated
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    str(current_user.tenant_id),
                    parameter.parameter_name,
                    parameter.category, # <-- Nuevo campo
                    parameter.value,
                    parameter.unit
                ))
                rec = cur.fetchone()
                conn.commit()
    except Exception as e:
        # Mejorar el manejo de errores para claves duplicadas
        if "unique constraint" in str(e):
             raise HTTPException(status_code=409, detail=f"El parámetro de coste '{parameter.parameter_name}' ya existe.")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    return schemas.CostParameter(id=rec[0], parameter_name=rec[1], category=rec[2], value=rec[3], unit=rec[4], last_updated=rec[5])

@router.get("/cost-parameters/", response_model=List[schemas.CostParameter])
def get_all_cost_parameters(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """Obtiene todos los parámetros de coste."""
    query = "SELECT id, parameter_name, category, value, unit, last_updated FROM cost_parameters WHERE tenant_id = %s ORDER BY category, parameter_name"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                recs = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    return [schemas.CostParameter(id=r[0], parameter_name=r[1], category=r[2], value=r[3], unit=r[4], last_updated=r[5]) for r in recs]

# --- NUEVO ENDPOINT PARA LA INTERFAZ ---
@router.get("/cost-categories/", response_model=Dict[str, List[schemas.CostParameter]])
def get_cost_parameters_by_category(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """Obtiene todos los parámetros de coste agrupados por categoría."""
    
    # Usamos defaultdict para facilitar la agrupación
    categorized_costs = defaultdict(list)
    
    query = "SELECT id, parameter_name, category, value, unit, last_updated FROM cost_parameters WHERE tenant_id = %s ORDER BY category, parameter_name"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                recs = cur.fetchall()
                for r in recs:
                    cost_param = schemas.CostParameter(id=r[0], parameter_name=r[1], category=r[2], value=r[3], unit=r[4], last_updated=r[5])
                    categorized_costs[r[2]].append(cost_param)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    
    return categorized_costs

@router.put("/cost-parameters/{parameter_id}", response_model=schemas.CostParameter)
def update_cost_parameter(
    parameter_id: uuid.UUID,
    parameter: schemas.CostParameterCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Actualiza un parámetro de coste."""
    query = """
        UPDATE cost_parameters
        SET parameter_name = %s, category = %s, value = %s, unit = %s, last_updated = NOW()
        WHERE id = %s AND tenant_id = %s
        RETURNING id, parameter_name, category, value, unit, last_updated
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    parameter.parameter_name,
                    parameter.category, # <-- Nuevo campo
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
    return schemas.CostParameter(id=rec[0], parameter_name=rec[1], category=rec[2], value=rec[3], unit=rec[4], last_updated=rec[5])

@router.delete("/cost-parameters/{parameter_id}", status_code=204)
def delete_cost_parameter(
    parameter_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Elimina un parámetro de coste."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Primero verificamos si existe para dar un 404 si no
                cur.execute("SELECT id FROM cost_parameters WHERE id = %s AND tenant_id = %s", (str(parameter_id), str(current_user.tenant_id)))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Parámetro no encontrado.")
                
                cur.execute(
                    "DELETE FROM cost_parameters WHERE id = %s AND tenant_id = %s",
                    (str(parameter_id), str(current_user.tenant_id))
                )
                conn.commit()
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    return

# Al final de app/routers/financials.py

@router.get("/costs-by-parameter/{parameter_name}", response_model=schemas.PaginatedCostRecordResponse)
def get_cost_records_by_parameter(
    parameter_name: str,
    page: int = 1,
    page_size: int = 5, # Por defecto, 5 registros por página
    current_user: schemas.User = Depends(get_current_active_user)
):
    """
    Obtiene los registros de costes paginados para un TIPO de coste específico.
    """
    tenant_id_str = str(current_user.tenant_id)
    offset = (page - 1) * page_size

    # Query para contar el total de registros
    count_query = "SELECT COUNT(*) FROM costs WHERE tenant_id = %s AND cost_type = %s;"
    
    # Query para obtener los registros de la página actual
    records_query = """
        SELECT id, cost_type, amount, description, cost_date, related_lot_id 
        FROM costs 
        WHERE tenant_id = %s AND cost_type = %s
        ORDER BY cost_date DESC
        LIMIT %s OFFSET %s;
    """
    
    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                # Contamos el total
                cur.execute(count_query, (tenant_id_str, parameter_name))
                total_records = cur.fetchone()[0]
                if total_records == 0:
                    return schemas.PaginatedCostRecordResponse(
                        records=[], total_records=0, page=page, 
                        page_size=page_size, total_pages=0
                    )
                
                # Obtenemos los registros de la página
                cur.execute(records_query, (tenant_id_str, parameter_name, page_size, offset))
                records_tuples = cur.fetchall()

                # Creamos la lista de objetos
                cost_records = [
                    schemas.CostRecord(
                        id=rec[0], cost_type=rec[1], amount=rec[2],
                        description=rec[3], cost_date=rec[4], related_lot_id=rec[5]
                    ) for rec in records_tuples
                ]
                
                total_pages = math.ceil(total_records / page_size)

                return schemas.PaginatedCostRecordResponse(
                    records=cost_records,
                    total_records=total_records,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages
                )
    except Exception as e:
        print(f"Error al obtener registros de costes paginados: {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar los costes.")


# --- ¡NUEVO ENDPOINT PARA CALCULAR PORCENTAJES! ---
@router.get("/costs-summary/", response_model=schemas.CostSummaryResponse)
def get_costs_summary(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """
    Calcula el total de costes incurridos y el desglose porcentual por categoría.
    """
    # Esta consulta asume que la columna 'cost_type' en la tabla 'costs'
    # se corresponde con un 'parameter_name' en la tabla 'cost_parameters'.
    query = """
    WITH CategoryCosts AS (
        SELECT
            cp.category,
            SUM(c.amount) as total_amount
        FROM costs c
        JOIN cost_parameters cp ON c.cost_type = cp.parameter_name AND c.tenant_id = cp.tenant_id
        WHERE c.tenant_id = %s
        GROUP BY cp.category
    ),
    GrandTotal AS (
        SELECT SUM(total_amount) as total FROM CategoryCosts
    )
    SELECT
        cc.category,
        cc.total_amount,
        (cc.total_amount / gt.total) * 100 as percentage,
        gt.total as grand_total
    FROM CategoryCosts cc, GrandTotal gt
    ORDER BY cc.total_amount DESC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                records = cur.fetchall()

                if not records:
                    return {"grand_total": 0.0, "details": []}

                grand_total = records[0][3] if records else 0.0
                summary_details = [
                    schemas.CategorySummary(
                        category=rec[0],
                        total_amount=float(rec[1]),
                        percentage=float(rec[2])
                    ) for rec in records
                ]
                return {"grand_total": float(grand_total), "details": summary_details}

    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")