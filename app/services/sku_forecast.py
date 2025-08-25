import pandas as pd
from statsmodels.tsa.api import ExponentialSmoothing
import numpy as np

def generate_sku_forecast(csv_path: str, sku: str, forecast_periods: int = 30):
    """
    Genera una predicción de ventas para un SKU específico usando Exponential Smoothing.

    Args:
        csv_path (str): Ruta al archivo CSV de ventas.
        sku (str): El SKU del producto a predecir.
        forecast_periods (int): Número de períodos (días) a predecir.

    Returns:
        dict: Un diccionario con las fechas y las ventas predichas.
    """
    try:
        # Cargar los datos
        df = pd.read_csv(csv_path, sep=';', decimal=',')
    except Exception as e:
        raise FileNotFoundError(f"No se pudo cargar o procesar el archivo CSV: {e}")

    # Limpieza y preparación de datos
    df['ITEM CODE'] = df['ITEM CODE'].astype(str)
    
    # Filtrar por el SKU solicitado
    df_sku = df[df['ITEM CODE'] == sku].copy()

    if df_sku.empty:
        raise ValueError(f"No se encontraron datos para el SKU: {sku}")

    # Crear una columna de fecha (asumimos el día 1 de cada mes para el histórico)
    df_sku['DATE'] = pd.to_datetime(df_sku['YEAR'].astype(str) + '-' + df_sku['MONTH'].astype(str) + '-01')
    
    # Sumar todas las ventas (retail, warehouse, transfers) para tener una demanda total
    df_sku['TOTAL_SALES'] = df_sku['RETAIL SALES'] + df_sku['WAREHOUSE SALES'] + df_sku['RETAIL TRANSFERS']
    
    # Agrupar por mes para crear la serie temporal
    ts = df_sku.groupby('DATE')['TOTAL_SALES'].sum()
    
    # Re-muestrear a frecuencia mensual para asegurar que no haya huecos
    ts = ts.asfreq('MS', fill_value=0)
    
    # Asegurarnos de que tenemos suficientes datos para el modelo
    if len(ts) < 12: # Mínimo un año de datos para que el modelo sea algo fiable
        raise ValueError("No hay suficientes datos históricos (mínimo 12 meses) para este producto.")

    # Entrenar el modelo de Holt-Winters (Exponential Smoothing)
    # Este modelo es bueno para datos con tendencia y estacionalidad.
    model = ExponentialSmoothing(
        ts,
        seasonal_periods=12, # Estacionalidad anual
        trend='add', 
        seasonal='add',
        initialization_method="estimated"
    ).fit()

    # Generar la predicción
    forecast = model.forecast(steps=1) # Predecimos el siguiente mes
    
    # Como el modelo predice por mes, dividimos la predicción mensual entre los días del mes
    # para obtener una estimación diaria. Es una simplificación pero funcional.
    last_date = ts.index.max()
    future_dates = pd.to_datetime(pd.date_range(start=last_date, periods=forecast_periods + 1, freq='D')[1:])
    
    # Usamos la predicción del próximo mes y la distribuimos
    next_month_forecast = forecast.iloc[0]
    daily_forecast_value = next_month_forecast / len(future_dates)
    
    # Aplicamos una pequeña variabilidad aleatoria para que no sea una línea plana
    noise = np.random.normal(0, daily_forecast_value * 0.2, len(future_dates))
    daily_forecast = np.maximum(0, daily_forecast_value + noise) # Aseguramos que no haya ventas negativas
    
    return {
        "dates": [d.strftime('%Y-%m-%d') for d in future_dates],
        "sales": list(daily_forecast)
    }