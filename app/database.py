import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# 1. Inicializamos el pool como None. No se crea al importar.
db_pool = None

def connect_to_db():
    """Crea el pool de conexiones a la base de datos."""
    global db_pool
    try:
        print("Creando el pool de conexiones a la base de datos...")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
        if db_pool:
            print("Pool de conexiones creado con éxito.")
    except psycopg2.OperationalError as e:
        print(f"ERROR: No se pudo crear el pool de conexiones: {e}")
        db_pool = None

def close_db_connection():
    """Cierra todas las conexiones en el pool."""
    global db_pool
    if db_pool:
        db_pool.closeall()
        print("Pool de conexiones cerrado.")

@contextmanager
def get_db_connection():
    """
    Obtiene una conexión del pool de forma segura.
    """
    if db_pool is None:
        raise ConnectionError("El pool de conexiones no está disponible. ¿Se inició correctamente la aplicación?")
    
    conn = None
    try:
        conn = db_pool.getconn()
        yield conn
    finally:
        if conn:
            db_pool.putconn(conn)