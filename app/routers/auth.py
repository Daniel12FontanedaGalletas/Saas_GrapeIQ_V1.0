from .. import crud
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..services import security
from .. import schemas

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Verifica las credenciales y devuelve un token de acceso junto con el rol del usuario.
    """
    user = crud.get_user_by_username(username=form_data.username)

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Si el usuario no tiene un rol en la base de datos (porque es antiguo),
    # le asignamos 'admin' por defecto para que pueda iniciar sesión.
    # Esto hace que el sistema sea retrocompatible.
    user_role = user.role or "admin"

    access_token = security.create_access_token(
        data={
            "sub": user.username, 
            "tenant_id": str(user.tenant_id),
            "role": user_role 
        }
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": user_role
    }

