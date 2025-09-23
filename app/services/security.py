import os
from datetime import datetime, timedelta
from typing import List
from .. import crud
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from .. import models, schemas

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)) -> schemas.UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_username(username=token_data.username)
    
    if user is None:
        raise credentials_exception
    
    return user

# --- MODIFICACIÓN: Añadimos la función que faltaba ---
def get_current_active_user(current_user: schemas.UserInDB = Depends(get_current_user)) -> schemas.UserInDB:
    """
    Esta función es una dependencia que simplemente reenvía el usuario actual.
    Sirve para mantener la consistencia con el router de usuarios que la estaba pidiendo.
    """
    # En un futuro, aquí se podría añadir lógica para comprobar si el usuario está "activo".
    # Por ahora, simplemente lo devolvemos.
    return current_user


def role_checker(required_roles: List[str]):
    def check_user_role(current_user: schemas.User = Depends(get_current_user)) -> schemas.User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos suficientes para realizar esta acción."
            )
        return current_user
        
    return check_user_role