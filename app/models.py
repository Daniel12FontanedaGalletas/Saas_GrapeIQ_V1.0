# Saas_GrapeIQ_V1.0/app/models.py

from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String
# IMPORTAMOS declarative_base DIRECTAMENTE DE SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Numeric, UniqueConstraint

from sqlalchemy import Date, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
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

class FieldLog(Base):
    __tablename__ = "field_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Renombramos y añadimos la fecha de fin
    start_datetime = Column(DateTime(timezone=True), nullable=False, index=True) 
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    activity_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    plot_name = Column(String, nullable=True)
    all_day = Column(Boolean, default=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
class GrapeLot(Base):
    __tablename__ = "grape_lots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    harvest_date = Column(Date, nullable=False)
    variety = Column(String, nullable=False)
    quantity_kg = Column(Numeric(10, 2), nullable=False)
    origin_plot = Column(String)
    status = Column(String, default='disponible')
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

class Vinification(Base):
    __tablename__ = "vinifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    description = Column(Text)
    status = Column(String, default='en_proceso')
    grape_lot_id = Column(UUID(as_uuid=True), ForeignKey("grape_lots.id"), unique=True, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

class Bottling(Base):
    __tablename__ = "bottlings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bottling_date = Column(Date, nullable=False)
    number_of_bottles = Column(Integer, nullable=False)
    batch_number = Column(String, unique=True)
    vinification_id = Column(UUID(as_uuid=True), ForeignKey("vinifications.id"), unique=True, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
