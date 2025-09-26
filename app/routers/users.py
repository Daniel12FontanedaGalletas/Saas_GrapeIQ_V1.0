# Saas_GrapeIQ_V1.0/app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, Form
from typing import Optional

from .. import schemas, crud
from ..services import security
from ..database import get_db_connection
from contextlib import closing

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me/", response_model=schemas.UserInDB)
async def read_users_me(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    return current_user

# --- MODIFICACIÓN: Cambiamos el 'response_model' y la lógica de retorno ---
@router.put("/me/", response_model=schemas.UserUpdateResponse)
async def update_user_me(
    username: str = Form(...),
    role: str = Form(...),
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET username = %s, role = %s
                    WHERE id = %s
                    """,
                    (username, role, str(current_user.id))
                )
                conn.commit()
        
        updated_user = crud.get_user_by_username(username)
        if not updated_user:
            raise HTTPException(status_code=404, detail="No se pudo encontrar al usuario después de actualizar.")
        
        # --- MODIFICACIÓN: Creamos un nuevo token con la información actualizada ---
        new_token = security.create_access_token(
            data={
                "sub": updated_user.username, 
                "role": updated_user.role,
                "tenant_id": str(updated_user.tenant_id)
            }
        )
            
        # Devolvemos tanto los datos del usuario como el nuevo token
        return schemas.UserUpdateResponse(
            **updated_user.model_dump(),
            new_access_token=new_token
        )

    except Exception as e:
        print(f"Error al actualizar el usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno al actualizar el perfil.")