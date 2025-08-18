import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# --- Configuración ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# Contexto para hashear y verificar contraseñas de forma segura
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de seguridad que FastAPI usará para la documentación y la inyección de dependencias
# Le dice a FastAPI que el token se debe esperar en la URL "/api/auth/token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# --- Funciones de Contraseña ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con un hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash seguro para una contraseña."""
    return pwd_context.hash(password)

# --- Funciones de Token JWT ---
def create_access_token(data: dict) -> str:
    """Crea un nuevo token JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Decodifica el token para obtener los datos del usuario.
    Esta función se usará como una dependencia en los endpoints protegidos.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        if username is None or tenant_id is None:
            raise credentials_exception
        
        # Devuelve un diccionario con los datos del usuario extraídos del token
        return {"username": username, "tenant_id": tenant_id}
    except JWTError:
        raise credentials_exception