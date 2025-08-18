from fastapi import APIRouter, Depends, BackgroundTasks

from ..services.security import get_current_user
from ..services.forecast_job import run_forecast_job, forecast_result_storage

router = APIRouter(
    prefix="/api/forecast",
    tags=["Forecast"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/run", status_code=202)
def run_forecast(background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """
    Inicia el NUEVO trabajo de predicción en segundo plano.
    """
    tenant_id = user.get("tenant_id")
    # Limpiamos el resultado anterior antes de empezar uno nuevo
    forecast_result_storage[tenant_id] = {"status": "processing"}
    background_tasks.add_task(run_forecast_job, tenant_id)
    return {"status": "El nuevo trabajo de predicción ha comenzado."}

@router.get("/results")
def get_forecast_results(user: dict = Depends(get_current_user)):
    """
    Obtiene el estado y el resultado (la imagen del gráfico) de la última predicción.
    """
    tenant_id = user.get("tenant_id")
    return forecast_result_storage.get(tenant_id, {"status": "not_found"})