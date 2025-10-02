# Saas_GrapeIQ_V1.0/app/routers/forecast.py (VERSIÓN CON EVENTOS DINÁMICOS)

from fastapi import APIRouter, Depends, HTTPException
from .. import database, schemas
from ..services import advanced_forecast
from ..services.security import get_current_user
import uuid
from typing import List

router = APIRouter(
    prefix="/api/forecast",
    tags=["Forecast"]
)

def format_forecast_output(forecast_df, component_modes, periods=90):
    if forecast_df is None: return None
    future_forecast = forecast_df.tail(periods)
    
    prediction = [
        schemas.ForecastPoint(
            date=row['ds'].strftime('%Y-%m-%d'),
            forecast=max(0, round(row['yhat'], 2)),
            forecast_lower=max(0, round(row['yhat_lower'], 2)),
            forecast_upper=max(0, round(row['yhat_upper'], 2)),
        ) for _, row in future_forecast.iterrows()
    ]

    components = {'trend': future_forecast['trend'].round(2).tolist(), 'yearly': future_forecast['yearly'].round(2).tolist(), 'weekly': future_forecast['weekly'].round(2).tolist()}
    regressor_cols = [col for col in future_forecast.columns if col not in ['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'trend', 'yearly', 'weekly']]
    if component_modes and component_modes.get('additive'):
         regressor_sum = future_forecast[regressor_cols].sum(axis=1)
         components['regressors'] = regressor_sum.round(2).tolist()
    else:
         components['regressors'] = [0] * periods
         
    return schemas.ForecastResponse(prediction=prediction, components=components)

@router.get("/sku/{product_id}", response_model=schemas.ForecastResponse)
def get_advanced_sku_forecast(product_id: uuid.UUID, current_user: schemas.User = Depends(get_current_user)):
    try:
        with database.get_db_connection() as conn:
            forecast_df, component_modes = advanced_forecast.get_advanced_forecast(conn, product_id)
    except Exception as e:
        print(f"Error en el endpoint de forecast: {e}"); raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

    formatted_output = format_forecast_output(forecast_df, component_modes)
    if formatted_output is None: raise HTTPException(status_code=404, detail="No se pudo generar el pronóstico. Datos insuficientes o producto no encontrado.")
    return formatted_output

@router.get("/total", response_model=schemas.ForecastResponse)
def get_total_sales_forecast_endpoint(current_user: schemas.User = Depends(get_current_user)):
    try:
        with database.get_db_connection() as conn:
            forecast_df, component_modes = advanced_forecast.get_total_sales_forecast(conn)
    except Exception as e:
        print(f"Error en el endpoint de forecast total: {e}"); raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

    formatted_output = format_forecast_output(forecast_df, component_modes)
    if formatted_output is None: raise HTTPException(status_code=404, detail="No se pudo generar el pronóstico. Datos insuficientes.")
    return formatted_output

@router.post("/scenario", response_model=schemas.ForecastResponse)
def get_scenario_forecast(scenario_request: schemas.ScenarioRequest, current_user: schemas.User = Depends(get_current_user)):
    """Genera una predicción basada en un escenario futuro definido por el usuario."""
    try:
        with database.get_db_connection() as conn:
            # --- MEJORA: Pasar los eventos futuros al servicio ---
            future_events_dict = [event.dict() for event in scenario_request.future_events]

            if scenario_request.product_id and scenario_request.product_id != 'total':
                product_uuid = uuid.UUID(scenario_request.product_id)
                forecast_df, component_modes = advanced_forecast.get_advanced_forecast(
                    conn, product_uuid, scenario_request.periods, 
                    [reg.dict() for reg in scenario_request.future_regressors],
                    future_events_dict
                )
            else:
                forecast_df, component_modes = advanced_forecast.get_total_sales_forecast(
                    conn, scenario_request.periods, 
                    [reg.dict() for reg in scenario_request.future_regressors],
                    future_events_dict
                )
    except Exception as e:
        print(f"Error en el endpoint de escenario: {e}"); raise HTTPException(status_code=500, detail=f"Error al simular el escenario: {e}")
        
    formatted_output = format_forecast_output(forecast_df, component_modes, scenario_request.periods)
    if formatted_output is None: raise HTTPException(status_code=404, detail="No se pudieron generar datos para este escenario.")
    return formatted_output