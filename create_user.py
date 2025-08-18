import os
import psycopg2
from dotenv import load_dotenv
from passlib.context import CryptContext
import re
from urllib.parse import urlparse, urlunparse

# Cargamos las variables de entorno para obtener la URL de la BD
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Usamos el mismo contexto de hasheo que en la app
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_initial_data():
    """Crea un tenant y un usuario administrador para ese tenant."""
    
    # --- DATOS A CREAR (puedes cambiar estos valores) ---
    tenant_name = "Mi Primera Empresa"
    admin_username = "admin"
    admin_password = "password123" # ¡Cámbiala en producción!
    
    hashed_password = get_password_hash(admin_password)
    
    conn = None
    try:
        if not DATABASE_URL:
            print("ERROR: La variable DATABASE_URL no se encontró en el archivo .env")
            return
        
        # Ocultamos la contraseña de forma segura para no mostrarla en la terminal
        try:
            parsed_url = urlparse(DATABASE_URL)
            safe_netloc = f"{parsed_url.username}:<password>@{parsed_url.hostname}:{parsed_url.port}"
            safe_url = urlunparse(parsed_url._replace(netloc=safe_netloc))
            print(f"Intentando conectar a: {safe_url}")
        except Exception:
            print("No se pudo parsear la DATABASE_URL para mostrarla de forma segura.")


        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("¡Conexión exitosa!")

        # 1. Crear el Tenant
        print(f"Creando tenant: '{tenant_name}'...")
        cur.execute(
            "INSERT INTO tenants (name) VALUES (%s) RETURNING id;",
            (tenant_name,)
        )
        tenant_id = cur.fetchone()[0]
        print(f"Tenant creado con ID: {tenant_id}")

        # 2. Crear el Usuario asociado a ese Tenant
        print(f"Creando usuario: '{admin_username}'...")
        cur.execute(
            "INSERT INTO users (tenant_id, username, hashed_password) VALUES (%s, %s, %s);",
            (tenant_id, admin_username, hashed_password)
        )
        print("Usuario creado con éxito.")

        # Guardar los cambios en la base de datos
        conn.commit()
        
        print("\n¡Configuración inicial completada!")
        print(f"  -> Usuario: {admin_username}")
        print(f"  -> Contraseña: {admin_password}")

    except Exception as e:
        print("\n----------------- ERROR DETALLADO -----------------")
        print(f"TIPO DE ERROR: {type(e).__name__}")
        print(f"MENSAJE: {e}")
        print("---------------------------------------------------")
        print("\nPOSIBLE SOLUCIÓN: Verifica que la contraseña en tu archivo .env sea la misma que estableciste en el panel de Supabase.")
        if conn:
            conn.rollback() 
    finally:
        if conn:
            conn.close()
            print("\nConexión cerrada.")

if __name__ == "__main__":
    create_initial_data()