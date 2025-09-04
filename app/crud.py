from .database import get_db_connection
from . import schemas
from contextlib import closing

def get_user_by_username(username: str) -> schemas.UserInDB | None:
    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    SELECT id, username, hashed_password, role, tenant_id
                    FROM users WHERE username = %s
                    """,
                    (username,)
                )
                user_record = cur.fetchone()

                if user_record:
                    # --- ¡ESTA ES LA CORRECCIÓN CLAVE! ---
                    # Si el rol viene vacío (None) de la base de datos,
                    # le asignamos 'admin' por defecto.
                    # Esto hace que el sistema sea compatible con usuarios antiguos.
                    db_role = user_record[3] or "admin"

                    user_data = {
                        "id": user_record[0],
                        "username": user_record[1],
                        "hashed_password": user_record[2],
                        "role": db_role, # <-- Usamos el rol con el valor por defecto
                        "tenant_id": user_record[4]
                    }
                    user_obj = schemas.UserInDB.model_validate(user_data, from_attributes=True)
                    return user_obj

                return None
    except Exception as e:
        print(f"Error al obtener usuario de la base de datos: {e}")
        return None

