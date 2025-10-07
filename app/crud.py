# Saas_GrapeIQ_V1.0/app/crud.py

from .database import get_db_connection
from . import schemas
from contextlib import closing
import uuid

def get_user_by_username(username: str) -> schemas.UserInDB | None:
    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                # =================================================================
                # INICIO DE LA CORRECCIÓN
                # Eliminamos los campos 'email' y 'full_name' que no existen en la tabla
                # =================================================================
                cur.execute(
                    """
                    SELECT id, username, hashed_password, role, tenant_id
                    FROM users WHERE username = %s
                    """,
                    (username,)
                )
                # =================================================================
                # FIN DE LA CORRECCIÓN
                # =================================================================
                user_record = cur.fetchone()

                if user_record:
                    db_role = user_record[3] or "admin"
                    
                    user_data = {
                        "id": user_record[0],
                        "username": user_record[1],
                        "hashed_password": user_record[2],
                        "role": db_role,
                        "tenant_id": user_record[4],
                        # Añadimos un email por defecto para cumplir con el esquema
                        "email": f"{user_record[1]}@example.com" 
                    }
                    user_obj = schemas.UserInDB.model_validate(user_data)
                    return user_obj

                return None
    except Exception as e:
        print(f"Error al obtener usuario de la base de datos: {e}")
        return None

def get_products(tenant_id: uuid.UUID, skip: int = 0, limit: int = 100):
    """
    Recupera una lista de productos para un tenant específico.
    """
    products = []
    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    SELECT id, name, sku, description, price, unit_cost, wine_lot_origin_id, stock_units, variety
                    FROM products
                    WHERE tenant_id = %s
                    ORDER BY name
                    LIMIT %s OFFSET %s
                    """,
                    (str(tenant_id), limit, skip)
                )
                for record in cur.fetchall():
                    product_data = {
                        "id": record[0],
                        "name": record[1],
                        "sku": record[2],
                        "description": record[3],
                        "price": record[4],
                        "unit_cost": record[5],
                        "wine_lot_origin_id": record[6],
                        "stock_units": record[7],
                        "variety": record[8]
                    }
                    products.append(schemas.Product.model_validate(product_data))
    except Exception as e:
        print(f"Error al obtener los productos: {e}")
    
    return products