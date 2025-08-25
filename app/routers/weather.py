import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from ..services.security import get_current_user
from datetime import datetime

router = APIRouter(
    prefix="/api/weather",
    tags=["Weather"],
    dependencies=[Depends(get_current_user)]
)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

@router.get("/prediction/{lat}/{lon}")
def get_weather_prediction(lat: float, lon: float):
    """
    Obtiene la predicción del tiempo para unas coordenadas específicas desde OpenWeatherMap.
    """
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENWEATHER_API_KEY no está configurada en el servidor.")

    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=current,minutely,hourly,alerts&appid={OPENWEATHER_API_KEY}&units=metric&lang=es"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        today_prediction_raw = data.get('daily', [])[0]

        formatted_prediction = {
            "nombre": data.get("timezone", "Ubicación seleccionada"),
            "prediccion": {
                "dia": [{
                    "fecha": datetime.fromtimestamp(today_prediction_raw.get("dt")).isoformat(),
                    "temperatura": { "maxima": int(round(today_prediction_raw.get("temp", {}).get("max", 0))) },
                    "probPrecipitacion": [{
                        "value": int(today_prediction_raw.get("pop", 0) * 100),
                        "periodo": "00-24"
                    }]
                }]
            }
        }
        return formatted_prediction
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Error al obtener datos de OpenWeatherMap: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado en el servidor: {e}")

@router.get("/current/{lat}/{lon}")
def get_current_weather(lat: float, lon: float):
    """
    Obtiene el tiempo actual para unas coordenadas desde OpenWeatherMap.
    """
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENWEATHER_API_KEY no configurada.")

    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily,alerts&appid={OPENWEATHER_API_KEY}&units=metric&lang=es"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get("current", {})
        formatted_data = {
            "temp": int(round(data.get("temp", 0))),
            "description": data.get("weather", [{}])[0].get("description", "No disponible").capitalize(),
            "icon": data.get("weather", [{}])[0].get("icon", "01d")
        }
        return formatted_data
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Error al obtener datos de OpenWeatherMap: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")