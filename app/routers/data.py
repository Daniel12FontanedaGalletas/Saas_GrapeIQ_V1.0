from fastapi import APIRouter, Depends
import json
from decimal import Decimal
from datetime import date

from ..database import get_db_connection
from ..services.security import get_current_user

router = APIRouter(
    prefix="/api/data",
    tags=["Data (Legacy)"],
    dependencies=[Depends(get_current_user)]
)

# Helper para convertir los resultados de la base de datos a un formato JSON compatible
def db_to_json(data, columns):
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, date):
                return obj.isoformat()
            return super(CustomEncoder, self).default(obj)

    results = [dict(zip(columns, row)) for row in data]
    return json.loads(json.dumps(results, cls=CustomEncoder))


@router.get("/products")
def get_products(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
    """
    SELECT id, name, sku, product_type, price_per_unit, cost_per_unit, stock_quantity 
    FROM products 
    WHERE tenant_id = %s 
    ORDER BY name
    """,
    (tenant_id,)
)
            columns = [desc[0] for desc in cur.description]
            products = cur.fetchall()
            return db_to_json(products, columns)

@router.get("/transfers")
def get_inventory_transfers(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT transfer_date, sku, quantity FROM inventory_transfers WHERE tenant_id = %s ORDER BY transfer_date DESC", (tenant_id,))
            columns = [desc[0] for desc in cur.description]
            transfers = cur.fetchall()
            return db_to_json(transfers, columns)

@router.get("/sales")
def get_sales_data(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT sale_date, sku, channel, sales_value FROM sales WHERE tenant_id = %s ORDER BY sale_date DESC LIMIT 500", (tenant_id,))
            columns = [desc[0] for desc in cur.description]
            sales = cur.fetchall()
            return db_to_json(sales, columns)
            
@router.get("/kpis")
def get_kpis(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(sales_value) FROM sales WHERE tenant_id = %s", (tenant_id,))
            total_sales = cur.fetchone()[0] or 0

            cur.execute("SELECT SUM(quantity) FROM inventory_transfers WHERE tenant_id = %s", (tenant_id,))
            inventory_transfers = cur.fetchone()[0] or 0
            
            return {
                "total_sales": total_sales,
                "total_inventory_transfers": inventory_transfers
            }