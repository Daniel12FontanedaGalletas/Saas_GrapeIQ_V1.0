import pandas as pd
import matplotlib
# CORRECCIÓN 1: Se añade esta línea para usar un backend de Matplotlib que no necesita pantalla.
# Debe ir ANTES de importar pyplot.
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from prophet import Prophet
import base64
from io import BytesIO

from ..database import get_db_connection

# Variable global para guardar el resultado
forecast_result_storage = {}

def run_forecast_job(tenant_id: str):
    """
    Ejecuta el trabajo de predicción de demanda global y genera un gráfico.
    """
    global forecast_result_storage
    print(f"Iniciando NUEVO trabajo de predicción para el tenant: {tenant_id}")
    
    try:
        with get_db_connection() as conn:
            query = """
                SELECT sale_date, SUM(sales_value) as total_sales
                FROM sales 
                WHERE tenant_id = %s
                GROUP BY sale_date
                ORDER BY sale_date;
            """
            df = pd.read_sql(query, conn, params=(tenant_id,), parse_dates=['sale_date'])

        if df.empty or len(df) < 2:
            print(f"No hay suficientes datos para la predicción para el tenant {tenant_id}.")
            forecast_result_storage[tenant_id] = {"status": "error", "message": "No hay suficientes datos para generar una predicción."}
            return

        df.rename(columns={'sale_date': 'ds', 'total_sales': 'y'}, inplace=True)

        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=90)
        forecast = model.predict(future)

        fig, ax = plt.subplots(figsize=(10, 6))
        model.plot(forecast, ax=ax)
        ax.set_title('Predicción de Ventas Totales (Próximos 3 Meses)')
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Ventas (€)')
        plt.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        # CORRECCIÓN 2: Se añade esta línea para cerrar la figura y liberar memoria.
        plt.close(fig)
        
        forecast_result_storage[tenant_id] = {"status": "complete", "image": f"data:image/png;base64,{image_base64}"}
        print(f"Predicción y gráfico generados con éxito para el tenant: {tenant_id}")

    except Exception as e:
        print(f"ERROR durante el NUEVO trabajo de predicción para el tenant {tenant_id}: {e}")
        forecast_result_storage[tenant_id] = {"status": "error", "message": str(e)}