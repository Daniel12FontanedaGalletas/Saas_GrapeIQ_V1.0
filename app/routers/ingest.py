import pandas as pd
import os
import shutil
from datetime import date
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
import psycopg2.extras

from ..database import get_db_connection
from ..services.security import get_current_user

router = APIRouter(
    prefix="/api/ingest",
    tags=["Ingest"],
    dependencies=[Depends(get_current_user)]
)

task_statuses = {}

def process_sales_csv(file_path: str, tenant_id: str):
    """
    Procesa un archivo CSV de ventas subido por el usuario.
    """
    global task_statuses
    try:
        task_statuses[tenant_id] = "processing"
        chunk_size = 10000
        print(f"Iniciando procesamiento de CSV para el tenant {tenant_id}...")

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                print(f"Borrando datos antiguos de ventas y transferencias para el tenant {tenant_id}...")
                cur.execute("DELETE FROM sales WHERE tenant_id = %s", (tenant_id,))
                cur.execute("DELETE FROM inventory_transfers WHERE tenant_id = %s", (tenant_id,))
                conn.commit()
                print("Datos antiguos borrados con éxito.")

        with pd.read_csv(file_path, delimiter=',', chunksize=chunk_size, on_bad_lines='warn', low_memory=False) as reader:
            for i, chunk in enumerate(reader):
                print(f"Procesando lote #{i+1}...")

                chunk.columns = [col.strip().upper().replace(' ', '_') for col in chunk.columns]

                required_cols = {'YEAR', 'MONTH', 'RETAIL_SALES', 'ITEM_CODE', 'ITEM_DESCRIPTION', 'ITEM_TYPE', 'SUPPLIER'}
                if not required_cols.issubset(chunk.columns):
                    missing_cols = required_cols - set(chunk.columns)
                    raise ValueError(f"Faltan columnas esenciales en el archivo CSV: {missing_cols}")

                optional_numeric_cols = {'WAREHOUSE_SALES': 0, 'RETAIL_TRANSFERS': 0}
                for col, default_value in optional_numeric_cols.items():
                    if col not in chunk.columns:
                        chunk[col] = default_value
                
                numeric_cols = ['YEAR', 'MONTH', 'RETAIL_SALES', 'RETAIL_TRANSFERS', 'WAREHOUSE_SALES']
                for col in numeric_cols:
                    chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
                chunk.dropna(subset=['YEAR', 'MONTH', 'RETAIL_SALES'], inplace=True)

                if chunk.empty:
                    print(f"Lote #{i+1} vacío. Saltando.")
                    continue

                chunk['sale_date'] = chunk.apply(lambda row: date(int(row['YEAR']), int(row['MONTH']), 1), axis=1)

                products_to_insert = []
                sales_to_insert = []
                transfers_to_insert = []
                processed_skus_total = set()

                for _, row in chunk.iterrows():
                    sku = str(row['ITEM_CODE'])
                    
                    if sku not in processed_skus_total:
                        products_to_insert.append((tenant_id, sku, row['ITEM_DESCRIPTION'], row['ITEM_TYPE'], row['SUPPLIER']))
                        processed_skus_total.add(sku)

                    if row['RETAIL_SALES'] > 0:
                        sales_to_insert.append((tenant_id, row['sale_date'], sku, 'RETAIL', row['RETAIL_SALES']))
                    if row['WAREHOUSE_SALES'] > 0:
                        sales_to_insert.append((tenant_id, row['sale_date'], sku, 'WAREHOUSE', row['WAREHOUSE_SALES']))
                    if row['RETAIL_TRANSFERS'] != 0:
                        transfers_to_insert.append((tenant_id, row['sale_date'], sku, row['RETAIL_TRANSFERS']))

                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        if products_to_insert:
                            # --- CORRECCIÓN AQUÍ ---
                            psycopg2.extras.execute_values(cur, """
                                INSERT INTO products (tenant_id, sku, name, product_type, supplier) VALUES %s 
                                ON CONFLICT (tenant_id, sku) DO UPDATE SET 
                                name = EXCLUDED.name, product_type = EXCLUDED.product_type, supplier = EXCLUDED.supplier;
                            """, products_to_insert)
                        if sales_to_insert:
                            psycopg2.extras.execute_values(cur, "INSERT INTO sales (tenant_id, sale_date, sku, channel, sales_value) VALUES %s", sales_to_insert)
                        if transfers_to_insert:
                             psycopg2.extras.execute_values(cur, "INSERT INTO inventory_transfers (tenant_id, transfer_date, sku, quantity) VALUES %s", transfers_to_insert)
                        conn.commit()
                print(f"Lote #{i+1} procesado e insertado.")

        print(f"Procesamiento de CSV finalizado con éxito para el tenant {tenant_id}")
        task_statuses[tenant_id] = "complete"

    except Exception as e:
        print(f"Error procesando CSV para el tenant {tenant_id}: {e}")
        task_statuses[tenant_id] = f"failed: {str(e)}"
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Archivo temporal {file_path} borrado.")
            except OSError as e:
                print(f"Error al borrar el archivo temporal {file_path}: {e}")

@router.post("/upload/sales-csv", status_code=202)
async def upload_sales_csv(background_tasks: BackgroundTasks, user: dict = Depends(get_current_user), file: UploadFile = File(...)):
    tenant_id = user.get("tenant_id")
    if task_statuses.get(tenant_id) == "processing":
        raise HTTPException(status_code=409, detail="Ya hay un proceso de ingesta en curso. Por favor, espera a que termine.")
    
    task_statuses[tenant_id] = "starting"
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Tipo de archivo inválido. Solo se permiten archivos CSV.")
    
    temp_file_path = f"temp_{tenant_id}_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(process_sales_csv, temp_file_path, tenant_id)
    return {"status": "El archivo se ha recibido y la tarea de procesamiento ha comenzado."}

@router.get("/upload/status")
def get_upload_status(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    status = task_statuses.get(tenant_id, "not_found")
    return {"status": status}