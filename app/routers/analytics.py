# Saas_GrapeIQ_V1.0/app/routers/analytics.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta
import random
import uuid
from typing import List

from ..services import security
from ..database import get_db_connection
from .. import schemas
from psycopg2.extras import RealDictCursor
from collections import defaultdict

# --- Configuración ---
DATA_FILE = 'grapeiq_fictional_data.csv'
router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics & KPIs"],
    dependencies=[Depends(security.get_current_active_user)]
)

# --- Carga y Preparación de Datos ---
def get_data():
    try:
        df = pd.read_csv(DATA_FILE, sep=';', decimal=',')
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"El archivo de datos '{DATA_FILE}' no fue encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo de datos: {e}")

# --- Endpoints (sin cambios, excepto el del catálogo) ---

@router.get("/kpis-summary")
def get_kpis_summary():
    df = get_data()
    total_sales = df['TotalSale'].sum()
    total_profit = df['Profit'].sum()
    total_quantity = df['Quantity'].sum()
    unique_customers = df['CustomerID'].nunique()
    average_sale_value = df.groupby('SaleID')['TotalSale'].sum().mean()
    today = datetime.now()
    current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = current_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    sales_current_month = df[df['Date'] >= current_month_start]['TotalSale'].sum()
    sales_last_month = df[(df['Date'] >= last_month_start) & (df['Date'] < current_month_start)]['TotalSale'].sum()
    month_over_month_change = ((sales_current_month - sales_last_month) / sales_last_month) * 100 if sales_last_month > 0 else 0
    return {
        "TotalSale": float(total_sales), "Profit": float(total_profit), "Quantity": int(total_quantity),
        "UniqueCustomers": int(unique_customers), "AverageSaleValue": float(average_sale_value),
        "MonthOverMonthChange": float(month_over_month_change),
    }

@router.get("/monthly-sales")
def get_monthly_sales():
    df = get_data()
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    return df.groupby('Month')['TotalSale'].sum().reset_index().to_dict(orient='records')

@router.get("/top-profitable-products")
def get_top_profitable_products(limit: int = 10):
    df = get_data()
    return df.groupby('ProductName')['Profit'].sum().nlargest(limit).reset_index().to_dict(orient='records')

@router.get("/top-units-products")
def get_top_units_products(limit: int = 10):
    df = get_data()
    return df.groupby(['ProductName', 'SKU'])['Quantity'].sum().nlargest(limit).reset_index().to_dict(orient='records')

@router.get("/sales-by-weekday")
def get_sales_by_weekday():
    df = get_data()
    df['weekday_num'] = df['Date'].dt.weekday + 1
    return df.groupby('weekday_num')['TotalSale'].sum().reset_index().rename(columns={'TotalSale': 'total_sales'}).to_dict(orient='records')

@router.get("/product-performance-matrix")
def get_product_performance_matrix(limit: int = 7):
    df = get_data()
    return df.groupby('ProductName').agg(Quantity=('Quantity', 'sum'), Profit=('Profit', 'sum')).nlargest(limit, 'Profit').reset_index().to_dict(orient='records')

@router.get("/available-months")
def get_available_months():
    df = get_data()
    months = df['Date'].dt.strftime('%Y-%m').unique().tolist()
    months.sort(reverse=True)
    return months

@router.get("/sales/by_sku/{sku}")
def get_sales_by_sku(sku: str, month: Optional[str] = Query(None)):
    df = get_data()
    sku_data = df[df['SKU'].str.lower() == sku.lower()]
    if sku_data.empty: raise HTTPException(status_code=404, detail="SKU no encontrado")
    product_name = sku_data['ProductName'].iloc[0]
    if month:
        sku_data = sku_data[sku_data['Date'].dt.strftime('%Y-%m') == month]
        if sku_data.empty: return {"product_name": product_name, "total_sales": 0.0}
    total_sales = sku_data['TotalSale'].sum()
    return {"product_name": product_name, "total_sales": float(total_sales)}

# --- ENDPOINT DEL CATÁLOGO HÍBRIDO (CORREGIDO) ---
@router.get("/product-catalog")
def get_product_catalog(
    limit: int = 10,
    offset: int = 0,
    sku: str = "",
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Devuelve una vista unificada del catálogo: productos reales de la BD y productos de demostración del CSV.
    """
    # 1. Obtener productos de demostración del CSV
    df_csv = get_data()
    csv_products = df_csv[['ProductName', 'SKU', 'UnitPrice', 'UnitCost']].drop_duplicates(subset=['SKU'])
    csv_products['Stock'] = csv_products['SKU'].apply(lambda s: random.randint(100, 1000))

    # 2. Obtener productos reales de la base de datos
    db_products_list = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT name, sku, price, stock_units FROM products WHERE tenant_id = %s",
                    (str(current_user.tenant_id),)
                )
                recs = cur.fetchall()
                for rec in recs:
                    price = rec[2]
                    # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
                    # Convertimos el precio (Decimal) a float antes de multiplicar
                    simulated_cost = float(price or 0) * random.uniform(0.4, 0.6)
                    
                    db_products_list.append({
                        "ProductName": rec[0], "SKU": rec[1], "UnitPrice": price,
                        "UnitCost": simulated_cost,
                        "Stock": rec[3]
                    })
    except Exception as e:
        print(f"Error al leer productos de la BD: {e}")
    
    df_db = pd.DataFrame(db_products_list)

    # 3. Combinar, filtrar y paginar
    if not df_db.empty:
        combined_df = pd.concat([df_db, csv_products], ignore_index=True)
    else:
        combined_df = csv_products
    
    combined_df.drop_duplicates(subset=['SKU'], keep='first', inplace=True)
    
    if sku:
        combined_df = combined_df[combined_df['SKU'].str.contains(sku, case=False, na=False)]

    sorted_df = combined_df.sort_values(by="ProductName")
    paginated_df = sorted_df.iloc[offset : offset + limit]

    return paginated_df.to_dict(orient='records')

# --- NUEVOS ENDPOINTS PARA GRÁFICAS ESTRATÉGICAS ---

@router.get("/parcel-performance")
def get_parcel_performance_metrics(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    query = """
    WITH ParcelCosts AS (SELECT related_parcel_id, SUM(amount) as total_cost FROM costs WHERE related_parcel_id IS NOT NULL AND tenant_id = %s GROUP BY related_parcel_id),
    ParcelProduction AS (SELECT origin_parcel_id, SUM(initial_grape_kg) as total_production_kg FROM wine_lots WHERE origin_parcel_id IS NOT NULL AND tenant_id = %s GROUP BY origin_parcel_id)
    SELECT p.id, p.name, p.area_hectares, COALESCE(pc.total_cost, 0) as cost, COALESCE(pp.total_production_kg, 0) as production_kg
    FROM parcels p LEFT JOIN ParcelCosts pc ON p.id = pc.related_parcel_id LEFT JOIN ParcelProduction pp ON p.id = pp.origin_parcel_id
    WHERE p.tenant_id = %s;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(current_user.tenant_id), str(current_user.tenant_id), str(current_user.tenant_id)))
                results = []
                for rec in cur.fetchall():
                    area = float(rec['area_hectares'] or 1.0); cost = float(rec['cost']); prod_kg = float(rec['production_kg'])
                    results.append({ "parcel_name": rec['name'], "cost_per_ha": cost / area if area > 0 else 0, "prod_per_ha": prod_kg / area if area > 0 else 0, "cost_per_kg": cost / prod_kg if prod_kg > 0 else 0 })
                return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos en parcel-performance: {e}")

# --- FUNCIÓN CORREGIDA Y RESTAURADA ---
@router.get("/cost-breakdown", response_model=List[schemas.SunburstCategory])
def get_cost_breakdown(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    query = """
    SELECT cp.category, c.cost_type, SUM(c.amount) as total
    FROM costs c JOIN cost_parameters cp ON c.cost_type = cp.parameter_name AND c.tenant_id = cp.tenant_id
    WHERE c.tenant_id = %s GROUP BY cp.category, c.cost_type ORDER BY cp.category, total DESC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                hierarchical_data = defaultdict(lambda: {'name': '', 'children': []})
                for rec in cur.fetchall():
                    category = rec['category']
                    hierarchical_data[category]['name'] = category
                    hierarchical_data[category]['children'].append({'name': rec['cost_type'], 'value': float(rec['total'])})
                final_data = list(hierarchical_data.values())
                final_data.sort(key=lambda x: sum(c['value'] for c in x['children']), reverse=True)
                return final_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos en cost-breakdown: {e}")

# --- FUNCIÓN CORREGIDA Y ROBUSTECIDA ---
@router.get("/product-profitability")
def get_product_profitability(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    query = """
    WITH ProductSales AS (
        SELECT sd.product_id, SUM(sd.quantity) as total_units_sold, SUM(sd.quantity * sd.unit_price) as total_revenue
        FROM sale_details sd JOIN sales s ON sd.sale_id = s.id
        WHERE s.tenant_id = %s GROUP BY sd.product_id
    )
    SELECT p.name as product_name, p.price as price, p.unit_cost as cost,
           COALESCE(ps.total_units_sold, 0) as units_sold, COALESCE(ps.total_revenue, 0) as revenue
    FROM products p LEFT JOIN ProductSales ps ON p.id = ps.product_id
    WHERE p.tenant_id = %s;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(current_user.tenant_id), str(current_user.tenant_id)))
                results = []
                for rec in cur.fetchall():
                    price = float(rec['price'] or 0); cost = float(rec['cost'] or 0)
                    results.append([ int(rec['units_sold']), price - cost, float(rec['revenue']), rec['product_name'] ])
                return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos en product-profitability: {e}")


@router.get("/cost-breakdown/{product_id}")
def get_single_product_cost_breakdown(product_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    product_query = """
    SELECT p.unit_cost as total_unit_cost, p.wine_lot_origin_id, wl.origin_parcel_id, (wl.total_liters / 0.75) as total_bottles
    FROM products p JOIN wine_lots wl ON p.wine_lot_origin_id = wl.id
    WHERE p.id = %s AND p.tenant_id = %s;
    """
    costs_query = """
    SELECT cp.category, c.cost_type, c.amount FROM costs c
    JOIN cost_parameters cp ON c.cost_type = cp.parameter_name AND c.tenant_id = cp.tenant_id
    WHERE c.tenant_id = %s AND (c.related_lot_id = %s OR c.related_parcel_id = %s);
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(product_query, (str(product_id), str(current_user.tenant_id)))
                product_info = cur.fetchone()
                if not product_info: raise HTTPException(status_code=404, detail="Producto no encontrado.")
                lot_id = product_info['wine_lot_origin_id']; parcel_id = product_info['origin_parcel_id']
                total_bottles = float(product_info['total_bottles'] or 1)
                total_unit_cost = float(product_info['total_unit_cost'] or 0)
                cur.execute(costs_query, (str(current_user.tenant_id), lot_id, parcel_id))
                
                aggregated_costs = defaultdict(lambda: defaultdict(float))
                for rec in cur.fetchall():
                    aggregated_costs[rec['category']][rec['cost_type']] += float(rec['amount']) / total_bottles if total_bottles > 0 else 0
                
                final_data = []
                for category, children in aggregated_costs.items():
                    child_list = [{'name': name, 'value': value} for name, value in children.items()]
                    final_data.append({'name': category, 'children': sorted(child_list, key=lambda x: x['value'], reverse=True)})
                
                return { "total_unit_cost": total_unit_cost, "breakdown": sorted(final_data, key=lambda x: sum(c['value'] for c in x['children']), reverse=True) }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")