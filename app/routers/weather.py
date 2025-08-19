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
    Usa la API "One Call" que nos da la predicción diaria para los próximos 8 días.
    """
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENWEATHER_API_KEY no está configurada en el servidor.")

    # URL de la API One Call 3.0 de OpenWeatherMap
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=current,minutely,hourly,alerts&appid={OPENWEATHER_API_KEY}&units=metric&lang=es"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # --- Transformamos la respuesta de OpenWeather al formato que nuestro frontend espera ---
        # Nos quedamos solo con la predicción de hoy
        today_prediction_raw = data.get('daily', [])[0]

        # Estructura simplificada similar a la que usábamos con AEMET
        formatted_prediction = {
            "nombre": data.get("timezone", "Ubicación seleccionada"), # Usamos timezone como nombre genérico
            "prediccion": {
                "dia": [
                    {
                        "fecha": datetime.fromtimestamp(today_prediction_raw.get("dt")).isoformat(),
                        "temperatura": {
                            "maxima": int(round(today_prediction_raw.get("temp", {}).get("max", 0)))
                        },
                        # OpenWeather da una probabilidad para todo el día
                        "probPrecipitacion": [
                            {
                                "value": int(today_prediction_raw.get("pop", 0) * 100), # Convertir de 0.x a porcentaje
                                "periodo": "00-24" # Indicamos que es para todo el día
                            }
                        ]
                    }
                ]
            }
        }
        
        return formatted_prediction

    except requests.exceptions.RequestException as e:
        print(f"Error al contactar con la API de OpenWeatherMap: {e}")
        raise HTTPException(status_code=503, detail=f"Error al obtener datos de OpenWeatherMap: {e}")
    except Exception as e:
        print(f"Error inesperado al procesar datos de OpenWeather: {e}")
        raise HTTPException(status_code=500, detail=f"Error inesperado en el servidor: {e}")