# Saas_GrapeIQ_V1.0/app/routers/sales.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
from datetime import datetime

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/sales",
    tags=["Sales"],
    dependencies=[Depends(security.get_current_active_user)]
)

@router.post("/", response_model=schemas.Sale, status_code=201)
def create_sale(
    sale_data: schemas.SaleCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Registra una nueva venta y actualiza el stock de los productos vendidos.
    """
    total_amount = sum(item.quantity * item.unit_price for item in sale_data.details)
    sale_id = uuid.uuid4()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Crear la venta principal
                cur.execute(
                    """
                    INSERT INTO sales (id, tenant_id, customer_name, total_amount, notes, sale_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (str(sale_id), str(current_user.tenant_id), sale_data.customer_name, total_amount, sale_data.notes, datetime.utcnow())
                )

                # 2. Registrar los detalles y actualizar el stock
                for item in sale_data.details:
                    # Insertar el detalle de la venta
                    cur.execute(
                        """
                        INSERT INTO sale_details (sale_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (str(sale_id), str(item.product_id), item.quantity, item.unit_price)
                    )

                    # Actualizar el stock del producto
                    cur.execute(
                        "UPDATE products SET stock_units = stock_units - %s WHERE id = %s AND tenant_id = %s",
                        (item.quantity, str(item.product_id), str(current_user.tenant_id))
                    )
                
                conn.commit()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

    # Devolvemos el objeto completo para la confirmación
    sale_details_for_response = [schemas.SaleDetail.model_validate({**item.model_dump(), "id": uuid.uuid4(), "sale_id": sale_id}) for item in sale_data.details]
    
    return schemas.Sale(
        id=sale_id,
        sale_date=datetime.utcnow(),
        total_amount=total_amount,
        customer_name=sale_data.customer_name,
        notes=sale_data.notes,
        details=sale_details_for_response
    )

@router.get("/", response_model=List[schemas.Sale])
def get_all_sales(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """Obtiene un listado de todas las ventas."""
    query = """
        SELECT id, sale_date, customer_name, total_amount, notes 
        FROM sales 
        WHERE tenant_id = %s 
        ORDER BY sale_date DESC
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                recs = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
        
    return [schemas.Sale(id=r[0], sale_date=r[1], customer_name=r[2], total_amount=r[3], notes=r[4]) for r in recs]