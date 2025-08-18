from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from ..database import get_db_connection
from ..services import security

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"] # Etiqueta para la documentación automática
)

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint para el login de usuarios.
    Recibe un username y password y devuelve un token de acceso.
    """
    # Busca al usuario en la base de datos
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT hashed_password, tenant_id FROM users WHERE username = %s",
                (form_data.username,)
            )
            user_record = cur.fetchone()

            # Si el usuario no existe o la contraseña es incorrecta, devuelve un error
            if not user_record or not security.verify_password(form_data.password, user_record[0]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario o contraseña incorrectos",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            tenant_id = str(user_record[1])

            # Si las credenciales son correctas, crea el token JWT
            access_token = security.create_access_token(
                data={"sub": form_data.username, "tenant_id": tenant_id}
            )
            
            return {"access_token": access_token, "token_type": "bearer"}