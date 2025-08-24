import os
import psycopg2
from dotenv import load_dotenv
from passlib.context import CryptContext

# Carga las variables de entorno
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Contexto de hasheo de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_database_schema(cur):
    """Crea las tablas de la base de datos si no existen."""
    print("Creando el esquema de la base de datos (si es necesario)...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            username VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    # --- CORRECCIÓN CLAVE: Se usa 'product_type' consistentemente ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            sku VARCHAR(255) NOT NULL,
            name VARCHAR(255),
            product_type VARCHAR(100),
            supplier VARCHAR(255),
            price_per_unit NUMERIC(10, 2),
            cost_per_unit NUMERIC(10, 2),
            stock_quantity INTEGER,
            UNIQUE(tenant_id, sku)
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            sale_date DATE NOT NULL,
            sku VARCHAR(255) NOT NULL,
            channel VARCHAR(50),
            sales_value NUMERIC(10, 2)
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory_transfers (
            id SERIAL PRIMARY KEY,
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            transfer_date DATE NOT NULL,
            sku VARCHAR(255) NOT NULL,
            quantity INTEGER
        );
    """)
    print("Esquema de base de datos verificado/creado con éxito.")

def create_initial_data():
    """Crea un tenant y un usuario administrador inicial."""
    tenant_name = "Mi Primera Empresa"
    admin_username = "admin"
    admin_password = "password123"
    
    hashed_password = get_password_hash(admin_password)
    
    conn = None
    try:
        if not DATABASE_URL:
            print("ERROR: La variable DATABASE_URL no se encontró en el archivo .env")
            return
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("¡Conexión a la base de datos exitosa!")

        # Crear tablas
        create_database_schema(cur)

        # Verificar si el usuario ya existe
        cur.execute("SELECT id FROM users WHERE username = %s", (admin_username,))
        if cur.fetchone():
            print(f"El usuario '{admin_username}' ya existe. No se creará de nuevo.")
            conn.commit()
            return

        # 1. Crear el Tenant
        print(f"Creando tenant: '{tenant_name}'...")
        cur.execute("INSERT INTO tenants (name) VALUES (%s) RETURNING id;", (tenant_name,))
        tenant_id = cur.fetchone()[0]
        print(f"Tenant creado con ID: {tenant_id}")

        # 2. Crear el Usuario
        print(f"Creando usuario: '{admin_username}'...")
        cur.execute(
            "INSERT INTO users (tenant_id, username, hashed_password) VALUES (%s, %s, %s);",
            (tenant_id, admin_username, hashed_password)
        )
        print("Usuario creado con éxito.")

        conn.commit()
        
        print("\n¡Configuración inicial completada!")
        print(f"  -> Usuario: {admin_username}")
        print(f"  -> Contraseña: {admin_password}")

    except Exception as e:
        print(f"\n--- ERROR ---: {e}")
        if conn:
            conn.rollback() 
    finally:
        if conn:
            conn.close()
            print("\nConexión cerrada.")

if __name__ == "__main__":
    create_initial_data()