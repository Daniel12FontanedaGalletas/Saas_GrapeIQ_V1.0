import os
import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv
from datetime import date

# Carga las variables de entorno
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def preload_data_for_user(username: str, csv_path: str):
    """
    Carga los datos de un archivo CSV para un usuario específico, borrando sus datos previos.
    """
    if not os.path.exists(csv_path):
        print(f"ERROR: No se encuentra el archivo '{csv_path}'. Asegúrate de que está en la raíz del proyecto.")
        return
    if not DATABASE_URL:
        print("ERROR: La variable DATABASE_URL no se encontró en el archivo .env")
        return

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("¡Conexión a la base de datos exitosa!")

        # 1. Obtener el tenant_id del usuario
        cur.execute("SELECT tenant_id FROM users WHERE username = %s", (username,))
        user_record = cur.fetchone()
        if not user_record:
            print(f"ERROR: No se encontró al usuario '{username}'. Ejecuta 'create_user.py' primero.")
            return
        tenant_id = str(user_record[0])
        print(f"Tenant ID para '{username}' es: {tenant_id}")

        # 2. Borrar datos antiguos (excepto el propio usuario y tenant)
        print(f"Borrando datos antiguos para el tenant {tenant_id}...")
        cur.execute("DELETE FROM sales WHERE tenant_id = %s", (tenant_id,))
        cur.execute("DELETE FROM inventory_transfers WHERE tenant_id = %s", (tenant_id,))
        cur.execute("DELETE FROM products WHERE tenant_id = %s", (tenant_id,))
        print("Datos antiguos borrados.")

        # 3. Procesar y cargar el CSV
        print(f"Iniciando el procesamiento de '{csv_path}'...")
        chunk_size = 10000
        with pd.read_csv(csv_path, delimiter=',', chunksize=chunk_size, on_bad_lines='warn', low_memory=False) as reader:
            for i, chunk in enumerate(reader):
                print(f"Procesando lote #{i+1}...")
                chunk.columns = [col.strip().upper().replace(' ', '_') for col in chunk.columns]
                
                # --- Preparación de datos ---
                required_cols = {'YEAR', 'MONTH', 'RETAIL_SALES', 'ITEM_CODE'}
                if not required_cols.issubset(chunk.columns):
                    raise ValueError(f"Faltan columnas esenciales: {required_cols - set(chunk.columns)}")
                
                for col in ['WAREHOUSE_SALES', 'RETAIL_TRANSFERS']:
                    if col not in chunk.columns: chunk[col] = 0
                
                numeric_cols = ['YEAR', 'MONTH', 'RETAIL_SALES', 'WAREHOUSE_SALES', 'RETAIL_TRANSFERS']
                for col in numeric_cols: chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
                
                chunk.dropna(subset=['YEAR', 'MONTH', 'RETAIL_SALES'], inplace=True)
                chunk['sale_date'] = chunk.apply(lambda r: date(int(r['YEAR']), int(r['MONTH']), 1), axis=1)

                products, sales, transfers = [], [], []
                processed_skus = set()
                for _, row in chunk.iterrows():
                    sku = str(row['ITEM_CODE'])
                    if sku not in processed_skus:
                        products.append((tenant_id, sku, row.get('ITEM_DESCRIPTION'), row.get('ITEM_TYPE'), row.get('SUPPLIER')))
                        processed_skus.add(sku)
                    if row['RETAIL_SALES'] > 0: sales.append((tenant_id, row['sale_date'], sku, 'RETAIL', row['RETAIL_SALES']))
                    if row['WAREHOUSE_SALES'] > 0: sales.append((tenant_id, row['sale_date'], sku, 'WAREHOUSE', row['WAREHOUSE_SALES']))
                    if row['RETAIL_TRANSFERS'] != 0: transfers.append((tenant_id, row['sale_date'], sku, row['RETAIL_TRANSFERS']))
                
                # --- Inserción en Base de Datos (con la columna correcta) ---
                if products:
                    psycopg2.extras.execute_values(cur, """
                        INSERT INTO products (tenant_id, sku, name, product_type, supplier) VALUES %s ON CONFLICT (tenant_id, sku) DO NOTHING;
                    """, products)
                if sales:
                    psycopg2.extras.execute_values(cur, "INSERT INTO sales (tenant_id, sale_date, sku, channel, sales_value) VALUES %s", sales)
                if transfers:
                    psycopg2.extras.execute_values(cur, "INSERT INTO inventory_transfers (tenant_id, transfer_date, sku, quantity) VALUES %s", transfers)
                print(f"Lote #{i+1} insertado.")

        conn.commit()
        print("\n✅ ¡Precarga de datos completada con éxito!")

    except Exception as e:
        print(f"\n--- ERROR DURANTE LA PRECARGA ---: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close(); print("\nConexión cerrada.")

if __name__ == "__main__":
    TARGET_USERNAME = "admin"
    CSV_FILENAME = "Warehouse_and_Retail_Sales.csv"
    preload_data_for_user(TARGET_USERNAME, CSV_FILENAME)