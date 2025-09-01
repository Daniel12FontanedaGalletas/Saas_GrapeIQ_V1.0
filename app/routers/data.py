# app/routers/data.py

from fastapi import APIRouter, Depends, HTTPException
import json
from decimal import Decimal
from datetime import date, timedelta
import psycopg2.extras

from ..database import get_db_connection
from ..services.security import get_current_user

router = APIRouter(
    prefix="/api/data",
    tags=["Data & Analytics"],
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

# --- ENDPOINTS LEGACY (Se mantienen por si otra parte de la app los usa) ---
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
            
# --- ENDPOINTS PARA EL NUEVO DASHBOARD DE ANALÍTICA AVANZADA ---

@router.get("/kpis")
def get_main_kpis(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            
            # 1. Ventas Totales (calculado sobre todas las ventas)
            cur.execute("SELECT SUM(sales_value) as total_sales FROM sales WHERE tenant_id = %s;", (tenant_id,))
            total_sales = cur.fetchone()['total_sales'] or 0

            # 2. Coste Total (calculado solo sobre ventas de productos con coste definido)
            cur.execute("""
                SELECT SUM( (s.sales_value / NULLIF(p.price_per_unit, 0)) * p.cost_per_unit) as total_cogs
                FROM sales s
                LEFT JOIN products p ON s.sku = p.sku AND s.tenant_id = p.tenant_id
                WHERE s.tenant_id = %s AND p.cost_per_unit IS NOT NULL;
            """, (tenant_id,))
            total_cogs = cur.fetchone()['total_cogs'] or 0

            # 3. Margen de Beneficio Bruto
            gross_profit_margin = ((total_sales - total_cogs) / total_sales) * 100 if total_sales > 0 else 0

            # 4. Unidades Transferidas
            cur.execute("SELECT SUM(quantity) as total_transfers FROM inventory_transfers WHERE tenant_id = %s", (tenant_id,))
            inventory_transfers = cur.fetchone()['total_transfers'] or 0
            
            # 5. Comparativa MoM (Month-over-Month)
            today = date.today()
            first_day_current_month = today.replace(day=1)
            last_day_prev_month = first_day_current_month - timedelta(days=1)
            first_day_prev_month = last_day_prev_month.replace(day=1)
            
            cur.execute("SELECT SUM(sales_value) FROM sales WHERE tenant_id = %s AND sale_date >= %s", (tenant_id, first_day_current_month))
            current_month_sales = cur.fetchone()[0] or 0
            cur.execute("SELECT SUM(sales_value) FROM sales WHERE tenant_id = %s AND sale_date BETWEEN %s AND %s", (tenant_id, first_day_prev_month, last_day_prev_month))
            prev_month_sales = cur.fetchone()[0] or 0
            
            mom_change = ((current_month_sales - prev_month_sales) / prev_month_sales) * 100 if prev_month_sales > 0 else 0

            return {
                "total_sales": total_sales,
                "total_inventory_transfers": inventory_transfers,
                "gross_profit_margin": gross_profit_margin,
                "month_over_month_change": mom_change
            }

@router.get("/analytics/monthly-sales")
def get_monthly_sales(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    TO_CHAR(sale_date, 'YYYY-MM') as month,
                    SUM(sales_value) as monthly_sales
                FROM sales
                WHERE tenant_id = %s AND sale_date >= NOW() - INTERVAL '12 months'
                GROUP BY month
                ORDER BY month;
            """, (tenant_id,))
            columns = [desc[0] for desc in cur.description]
            return db_to_json(cur.fetchall(), columns)

@router.get("/analytics/top-profitable-products")
def get_top_profitable_products(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.sku,
                    p.name,
                    SUM(s.sales_value - ( (s.sales_value / NULLIF(p.price_per_unit, 0)) * p.cost_per_unit)) as total_profit
                FROM sales s
                LEFT JOIN products p ON s.sku = p.sku AND s.tenant_id = p.tenant_id
                WHERE s.tenant_id = %s AND p.cost_per_unit IS NOT NULL
                GROUP BY p.sku, p.name
                ORDER BY total_profit DESC
                LIMIT 10;
            """, (tenant_id,))
            columns = [desc[0] for desc in cur.description]
            return db_to_json(cur.fetchall(), columns)

@router.get("/analytics/sales-by-weekday")
def get_sales_by_weekday(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    EXTRACT(ISODOW FROM sale_date) as weekday_num,
                    SUM(sales_value) as total_sales
                FROM sales
                WHERE tenant_id = %s
                GROUP BY weekday_num
                ORDER BY weekday_num;
            """, (tenant_id,))
            columns = [desc[0] for desc in cur.description]
            return db_to_json(cur.fetchall(), columns)

@router.get("/analytics/top-units-products")
def get_top_products_by_units(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    s.sku,
                    SUM(s.sales_value / NULLIF(p.price_per_unit, 0)) as total_units
                FROM sales s
                LEFT JOIN products p ON s.sku = p.sku AND s.tenant_id = p.tenant_id
                WHERE s.tenant_id = %s
                GROUP BY s.sku
                ORDER BY total_units DESC
                LIMIT 10;
            """, (tenant_id,))
            columns = [desc[0] for desc in cur.description]
            return db_to_json(cur.fetchall(), columns)

@router.get("/analytics/sales-by-channel")
def get_sales_by_channel(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT channel, SUM(sales_value) as total_sales
                FROM sales
                WHERE tenant_id = %s
                GROUP BY channel;
            """, (tenant_id,))
            columns = [desc[0] for desc in cur.description]
            return db_to_json(cur.fetchall(), columns)

@router.get("/sales/by_sku/{sku}")
def get_sales_by_sku(sku: str, user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT p.name, SUM(s.sales_value) as total_sales
                FROM sales s
                LEFT JOIN products p ON s.sku = p.sku AND s.tenant_id = p.tenant_id
                WHERE s.sku ILIKE %s AND s.tenant_id = %s
                GROUP BY p.name;
            """, (f"%{sku}%", tenant_id))
            result = cur.fetchone()
            if not result or not result["name"]:
                raise HTTPException(status_code=404, detail=f"No se encontraron ventas para el SKU '{sku}'.")
            return {"product_name": result["name"], "total_sales": result["total_sales"]}