# Saas_GrapeIQ_V1.0/app/routers/analytics.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta
import random

from ..services import security
from ..database import get_db_connection
from .. import schemas

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