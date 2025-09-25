# Saas_GrapeIQ_V1.0/app/models.py

from sqlalchemy import Column, Integer, String, Numeric, Date, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

# Creamos una 'Base' local para todos nuestros modelos de SQLAlchemy
Base = declarative_base()

# --- TABLAS DE GESTIÓN DE CUENTAS ---
class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="lector")
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

# --- TABLAS DE MÓDULOS DE NEGOCIO ---

# Módulo: Cuaderno de Campo (sin cambios)
class FieldLog(Base):
    __tablename__ = "field_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    start_datetime = Column(DateTime(timezone=True), nullable=False, index=True) 
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    activity_type = Column(String, nullable=False)
    description = Column(Text)
    plot_name = Column(String)
    all_day = Column(Boolean, default=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

# --- NUEVA ESTRUCTURA PARA GESTIÓN DE BODEGA Y TRAZABILIDAD ---

class Container(Base):
    __tablename__ = "containers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # 'Barrica' o 'Depósito'
    capacity_liters = Column(Numeric(10, 2), nullable=False)
    material = Column(String)
    location = Column(String)
    status = Column(String, default='vacío') # vacío, ocupado, limpieza
    current_volume = Column(Numeric(10, 2), default=0)
    current_lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

class WineLot(Base):
    __tablename__ = "wine_lots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    grape_variety = Column(String)
    vintage_year = Column(Integer)
    status = Column(String, default='Cosechado') # Cosechado, En Fermentación, En Crianza, Embotellado
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

class Movement(Base):
    __tablename__ = "movements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    source_container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    destination_container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    volume = Column(Numeric(10, 2), nullable=False)
    movement_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    type = Column(String, nullable=False) # Llenado Inicial, Trasiego, Embotellado
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
class WineLot(Base):
    __tablename__ = "wine_lots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    grape_variety = Column(String)
    vintage_year = Column(Integer)
    status = Column(String, default='Cosechado')
    
    # --- NUEVAS COLUMNAS PARA GESTIÓN DE VOLUMEN ---
    initial_grape_kg = Column(Numeric(10, 2), nullable=True)
    total_liters = Column(Numeric(10, 2), nullable=True)
    liters_unassigned = Column(Numeric(10, 2), nullable=True)
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)