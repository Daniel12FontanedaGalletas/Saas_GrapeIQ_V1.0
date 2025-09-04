# Saas_GrapeIQ_V1.0/app/models.py

from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String
# IMPORTAMOS declarative_base DIRECTAMENTE DE SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base

# Creamos una 'Base' local para nuestros modelos de SQLAlchemy
Base = declarative_base()

# Modelo para la tabla de usuarios en la base de datos (SQLAlchemy)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    winery_name = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    # --- MODIFICACIÓN: Añadimos la columna 'role' ---
    # Guardará el rol del usuario (ej. "admin", "lector").
    # 'default="lector"' asigna "lector" a los nuevos usuarios si no se especifica otro rol.
    role = Column(String, default="lector")


# Modelo para los datos que devolvemos al cliente (Pydantic)
class UserInDB(BaseModel):
    username: str
    winery_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    # --- MODIFICACIÓN: Añadimos el campo 'role' ---
    # Así el frontend sabrá qué rol tiene el usuario que ha iniciado sesión.
    role: str

    class Config:
        # Pydantic V2 usa 'from_attributes' en lugar de 'orm_mode'
        from_attributes = True

# Modelo para el token de autenticación
class Token(BaseModel):
    access_token: str
    token_type: str
