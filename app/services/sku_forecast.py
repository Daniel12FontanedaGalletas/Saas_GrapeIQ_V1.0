# Saas_GrapeIQ_V1.0/app/services/sku_forecast.py

import pandas as pd
from statsmodels.tsa.api import ExponentialSmoothing
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CSV_PATH = BASE_DIR / "Warehouse_and_Retail_Sales.csv"

def generate_sku_forecast(sku: str, forecast_periods: int = 90):
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"El archivo de ventas no se encuentra en la ruta esperada: {CSV_PATH}")

    try:
        # Usamos el separador de coma y manejamos líneas con errores.
        df = pd.read_csv(CSV_PATH, sep=',', on_bad_lines='warn')
    except Exception as e:
        raise ConnectionError(f"No se pudo cargar o procesar el archivo CSV. Error: {e}")

    df.columns = df.columns.str.strip()
    
    if 'ITEM CODE' not in df.columns:
        raise KeyError(f"La columna 'ITEM CODE' no se encuentra en el archivo. Columnas disponibles: {df.columns.tolist()}")
        
    df['ITEM CODE'] = df['ITEM CODE'].astype(str).str.strip()
    
    df_sku = df[df['ITEM CODE'] == sku].copy()

    if df_sku.empty:
        raise ValueError(f"No se encontraron datos de ventas para el SKU: {sku}")

    df_sku['DATE'] = pd.to_datetime(df_sku['YEAR'].astype(str) + '-' + df_sku['MONTH'].astype(str) + '-01', errors='coerce')
    df_sku.dropna(subset=['DATE'], inplace=True)

    sales_columns = ['RETAIL SALES', 'WAREHOUSE SALES', 'RETAIL TRANSFERS']
    
    for col in sales_columns:
        if col in df_sku.columns:
            df_sku[col] = pd.to_numeric(
                df_sku[col].astype(str).str.replace(',', '.'), 
                errors='coerce'
            ).fillna(0)
        else:
            df_sku[col] = 0
        
    df_sku['TOTAL_SALES'] = df_sku[sales_columns].sum(axis=1)
    
    ts = df_sku.groupby('DATE')['TOTAL_SALES'].sum().asfreq('MS', fill_value=0)
    
    # Requisito mínimo: al menos 12 meses para cualquier predicción.
    if len(ts) < 12:
        raise ValueError(f"No hay suficientes datos históricos para este SKU (se necesitan al menos 12 meses).")

    # ===== LÓGICA DEL MODELO ADAPTATIVO =====
    try:
        # Si tenemos más de 24 meses, usamos el modelo completo (tendencia + estacionalidad)
        if len(ts) >= 24:
            print(f"SKU {sku}: Usando modelo estacional (datos >= 24 meses).")
            model = ExponentialSmoothing(
                ts,
                seasonal_periods=12,
                trend='add', 
                seasonal='add',
                initialization_method="estimated"
            ).fit()
        # Si tenemos entre 12 y 23 meses, usamos un modelo más simple (solo tendencia)
        else:
            print(f"SKU {sku}: Usando modelo simple de tendencia (datos < 24 meses).")
            model = ExponentialSmoothing(
                ts,
                trend='add',
                initialization_method="estimated"
            ).fit()

    except Exception as e:
        raise ValueError(f"Error del modelo estadístico: {e}")
    # ===== FIN DE LA LÓGICA ADAPTATIVA =====

    months_to_forecast = int(np.ceil(forecast_periods / 30))
    forecast = model.forecast(steps=months_to_forecast) 
    
    last_hist_date = ts.index.max()
    future_dates = pd.date_range(start=last_hist_date + pd.DateOffset(days=1), periods=forecast_periods, freq='D')
    
    daily_forecast = []
    for date in future_dates:
        monthly_forecast_val = forecast[forecast.index.to_period('M') == date.to_period('M')]
        if not monthly_forecast_val.empty:
            days_in_month = date.days_in_month
            daily_value = monthly_forecast_val.iloc[0] / days_in_month
            daily_forecast.append(daily_value)
        else:
            daily_forecast.append(0)

    # Aseguramos que la predicción nunca sea negativa
    daily_forecast = np.maximum(0, daily_forecast)
    noise = np.random.normal(0, np.mean(daily_forecast) * 0.15, len(daily_forecast))
    final_daily_forecast = np.maximum(0, np.array(daily_forecast) + noise)
    
    return {
        "dates": [d.strftime('%Y-%m-%d') for d in future_dates],
        "sales": list(final_daily_forecast)
    }