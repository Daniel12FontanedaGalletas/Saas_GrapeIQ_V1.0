# Saas_GrapeIQ_V1.0/app/services/advanced_forecast.py (VERSIÓN CORREGIDA Y ROBUSTA)

import pandas as pd
from prophet import Prophet
import uuid
import logging
from typing import List, Dict, Optional
import numpy as np

logging.getLogger('prophet').setLevel(logging.WARNING)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

def _run_prophet_forecast(
    db_connection,
    query: str,
    query_params: Optional[Dict],
    periods: int,
    future_regressors: List[Dict] = [],
    future_events: List[Dict] = []
):
    """Función interna para ejecutar el modelo Prophet con parámetros ajustados y regresores dinámicos."""
    
    # 1. Cargar eventos (sin cambios)
    try:
        events_query = "SELECT event_name as holiday, start_date as ds FROM special_events;"
        special_events_df = pd.read_sql(events_query, db_connection)
        special_events_df['ds'] = pd.to_datetime(special_events_df['ds'])
        
        if future_events:
            user_events_df = pd.DataFrame(future_events)
            user_events_df['ds'] = pd.to_datetime(user_events_df['ds'])
            special_events_df = pd.concat([special_events_df, user_events_df], ignore_index=True)
            
    except Exception:
        special_events_df = pd.DataFrame(future_events) if future_events else None
        if special_events_df is not None:
             special_events_df['ds'] = pd.to_datetime(special_events_df['ds'])

    # 2. Cargar y procesar datos históricos (sin cambios)
    try:
        df = pd.read_sql(query, db_connection, params=query_params)
        if df.empty or len(df) < 20: return None, None
        df['ds'] = pd.to_datetime(df['ds'])

        df_daily = df.groupby('ds').agg(
            y=('y', 'sum'),
            avg_temperature=('avg_temperature', 'first'),
            is_weekend=('is_weekend', 'first'),
            on_promotion=('on_promotion', 'max')
        ).reset_index()

        channel_pivot = df.pivot_table(index='ds', columns='channel', values='y', aggfunc='sum').fillna(0)
        df = pd.merge(df_daily, channel_pivot, on='ds', how='left').fillna(0)

    except Exception as e:
        print(f"❌ Error al consultar o procesar datos: {e}"); return None, None

    # 3. Configurar y entrenar el modelo (sin cambios)
    model = Prophet(
        growth='linear',
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.5,
        seasonality_prior_scale=25.0,
        interval_width=0.90,
        holidays=special_events_df
    )
    
    channel_columns = list(channel_pivot.columns)
    regressors_to_add = ['avg_temperature', 'is_weekend', 'on_promotion'] + channel_columns
    for regressor in regressors_to_add: model.add_regressor(regressor)
    model.add_country_holidays(country_name='ES')
    model.fit(df)

    # 4. Crear dataframe futuro y rellenar TODOS los regresores
    future = model.make_future_dataframe(periods=periods)
    
    # --- INICIO DE LA CORRECCIÓN ---

    # Copiamos los regresores históricos del dataframe original
    # Esto llena los valores pasados para que no sean NaN
    regressor_cols_to_merge = ['ds'] + regressors_to_add
    future = pd.merge(future, df[regressor_cols_to_merge], on='ds', how='left')

    # Identificamos las filas que son del futuro
    last_date = df['ds'].max()
    future_dates_mask = future['ds'] > last_date
    
    # Rellenamos los NaN que puedan haber quedado en las filas futuras
    future['is_weekend'] = future['ds'].dt.weekday >= 5
    future['on_promotion'].fillna(0, inplace=True) # La promo por defecto es 0

    # Proyectamos la temperatura con un ciclo anual
    future_dates = pd.to_datetime(future[future_dates_mask]['ds'])
    day_of_year = future_dates.dt.dayofyear 
    temp_simulation = 15 + 10 * np.sin((day_of_year - 80) * (2 * np.pi / 365))
    future.loc[future_dates_mask, 'avg_temperature'] = temp_simulation
    future['avg_temperature'].fillna(df['avg_temperature'].mean(), inplace=True) # Rellenar por si acaso

    # Proyectamos los canales de venta con variabilidad
    channel_means = df[channel_columns].mean()
    channel_std = df[channel_columns].std().fillna(0)

    for col in channel_columns:
        # Rellenamos los NaN históricos que puedan quedar (aunque no deberían)
        future[col].fillna(0, inplace=True)
        mean_val = channel_means[col]
        std_val = channel_std[col]
        
        if std_val > 0:
            # np.random.normal necesita saber el tamaño exacto del futuro
            num_future_periods = len(future[future_dates_mask])
            noise = np.random.normal(0, std_val / 4, num_future_periods)
            future.loc[future_dates_mask, col] = np.maximum(0, mean_val + noise)
        else:
            future.loc[future_dates_mask, col] = mean_val
        # Rellenamos cualquier NaN que pueda haber quedado en columnas de canal
        future[col].fillna(0, inplace=True)
            
    # --- FIN DE LA CORRECCIÓN ---

    if future_regressors:
        for reg in future_regressors:
            mask = (future['ds'] >= pd.to_datetime(reg['start_date'])) & (future['ds'] <= pd.to_datetime(reg['end_date']))
            if reg['name'] in future.columns:
                future.loc[mask, reg['name']] = reg['value']

    # 5. Predecir y devolver
    forecast = model.predict(future)
    return forecast, model.component_modes

def get_advanced_forecast(db_connection, product_id: uuid.UUID, periods: int = 90, future_regressors: List[Dict] = [], future_events: List[Dict] = []):
    """Genera un pronóstico para un producto específico."""
    print(f"📈 Iniciando pronóstico para PRODUCTO: {product_id}")
    query = """
        SELECT
            s.sale_date::date AS ds,
            s.channel,
            sd.quantity as y,
            s.avg_temperature,
            s.is_weekend,
            CAST(sd.on_promotion AS INT) as on_promotion
        FROM sales s
        JOIN sale_details sd ON s.id = sd.sale_id
        WHERE sd.product_id = %(product_id)s;
    """
    params = {'product_id': str(product_id)}
    return _run_prophet_forecast(db_connection, query, params, periods, future_regressors, future_events)

def get_total_sales_forecast(db_connection, periods: int = 90, future_regressors: List[Dict] = [], future_events: List[Dict] = []):
    """Genera un pronóstico para las ventas totales."""
    print(f"📈 Iniciando pronóstico para VENTAS TOTALES...")
    query = """
        SELECT
            s.sale_date::date AS ds,
            s.channel,
            sd.quantity as y,
            s.avg_temperature,
            s.is_weekend,
            CAST(sd.on_promotion AS INT) as on_promotion
        FROM sales s
        JOIN sale_details sd ON s.id = sd.sale_id;
    """
    return _run_prophet_forecast(db_connection, query, None, periods, future_regressors, future_events)