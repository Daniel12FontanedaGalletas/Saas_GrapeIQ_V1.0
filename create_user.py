import os
import psycopg2
from dotenv import load_dotenv
from passlib.context import CryptContext
import argparse # <-- 1. Importamos argparse para leer argumentos de la terminal

# Carga las variables de entorno
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Contexto de hasheo de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_database_schema(cur):
    """Crea las tablas de la base de datos si no existen."""
    print("Verificando el esquema de la base de datos...")
    # --- MODIFICACIÓN: Añadimos la columna 'role' a la tabla de usuarios ---
    # Le damos un valor por defecto 'lector' para mantener la consistencia.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            username VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'lector',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    # El resto de las tablas se mantienen igual
    cur.execute("CREATE TABLE IF NOT EXISTS tenants (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW());")
    cur.execute("CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, tenant_id UUID, sku VARCHAR(255) NOT NULL, name VARCHAR(255), product_type VARCHAR(100), supplier VARCHAR(255), price_per_unit NUMERIC(10, 2), cost_per_unit NUMERIC(10, 2), stock_quantity INTEGER, UNIQUE(tenant_id, sku));")
    cur.execute("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, tenant_id UUID, sale_date DATE NOT NULL, sku VARCHAR(255) NOT NULL, channel VARCHAR(50), sales_value NUMERIC(10, 2));")
    cur.execute("CREATE TABLE IF NOT EXISTS inventory_transfers (id SERIAL PRIMARY KEY, tenant_id UUID, transfer_date DATE NOT NULL, sku VARCHAR(255) NOT NULL, quantity INTEGER);")
    print("Eschema de base de datos verificado.")

# --- 2. MODIFICACIÓN: Creamos una función más genérica ---
def create_user(username, password, role):
    """Crea un nuevo usuario en la base de datos con un rol específico."""
    
    hashed_password = get_password_hash(password)
    tenant_name = "Default Tenant" # Asumimos un tenant por defecto para los nuevos usuarios
    
    conn = None
    try:
        if not DATABASE_URL:
            print("ERROR: La variable DATABASE_URL no se encontró en el archivo .env")
            return
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Asegurarse de que el esquema de la BD está creado
        create_database_schema(cur)

        # Verificar si el usuario ya existe
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            print(f"El usuario '{username}' ya existe. No se creará de nuevo.")
            return

        # Verificar si el tenant por defecto existe, si no, crearlo.
        cur.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,))
        tenant_id_row = cur.fetchone()
        if not tenant_id_row:
            print(f"Creando tenant por defecto: '{tenant_name}'...")
            cur.execute("INSERT INTO tenants (name) VALUES (%s) RETURNING id;", (tenant_name,))
            tenant_id = cur.fetchone()[0]
        else:
            tenant_id = tenant_id_row[0]

        # --- MODIFICACIÓN: Insertamos el usuario con su rol ---
        print(f"Creando usuario: '{username}' con rol: '{role}'...")
        cur.execute(
            "INSERT INTO users (tenant_id, username, hashed_password, role) VALUES (%s, %s, %s, %s);",
            (tenant_id, username, hashed_password, role)
        )
        print("Usuario creado con éxito.")

        conn.commit()
        
    except Exception as e:
        print(f"\n--- ERROR ---: {e}")
        if conn:
            conn.rollback() 
    finally:
        if conn:
            conn.close()
            print("\nConexión cerrada.")

# --- 3. MODIFICACIÓN: Usamos argparse para leer los datos desde la terminal ---
if __name__ == "__main__":
    # Creamos un objeto para parsear los argumentos
    parser = argparse.ArgumentParser(description="Crear un nuevo usuario en la base de datos.")
    
    # Argumentos que el script aceptará
    parser.add_argument("username", type=str, help="El nombre de usuario.")
    parser.add_argument("password", type=str, help="La contraseña del usuario.")
    parser.add_argument("--role", type=str, default="lector", choices=['lector', 'admin'], help="El rol del usuario (lector o admin). Por defecto: lector.")
    
    # Leemos los argumentos que se pasaron por la terminal
    args = parser.parse_args()
    
    # Llamamos a la función principal con los argumentos leídos
    create_user(args.username, args.password, args.role)