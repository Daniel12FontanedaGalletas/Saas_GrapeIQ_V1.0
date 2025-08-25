# Saas_GrapeIQ_V1.0/app/routers/forecast.py

from fastapi import APIRouter, HTTPException
from ..services import sku_forecast

router = APIRouter(
    prefix="/api/forecast",
    tags=["Forecast"],
    responses={404: {"description": "Not found"}},
)

# --- Endpoint Nuevo para predicción por SKU ---
@router.get("/sku/{sku}")
async def get_sku_forecast(sku: str):
    """
    Genera y devuelve una predicción de ventas para un SKU específico.
    """
    try:
        # Llama a la función que hemos modificado en el servicio
        forecast_data = sku_forecast.generate_sku_forecast(sku=sku)
        return forecast_data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # Este error se da si el SKU no existe o no hay suficientes datos
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Cualquier otro error inesperado
        raise HTTPException(status_code=500, detail=f"Ocurrió un error interno al generar la predicción: {e}")

# --- Rutas que ya tenías (las dejamos por si las usas para otra cosa) ---
# (Aquí irían las rutas /run y /results que tenías antes si existieran en tu archivo)