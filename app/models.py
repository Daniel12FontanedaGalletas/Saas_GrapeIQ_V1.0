# Saas_GrapeIQ_V1.0/app/models.py

from sqlalchemy import Column, Integer, String, Numeric, Date, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

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
    # ... otros campos
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True)
    all_day = Column(Boolean, default=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

# --- ESTRUCTURA CENTRAL DE BODEGA Y TRAZABILIDAD ---

class WineLot(Base):
    __tablename__ = "wine_lots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    grape_variety = Column(String)
    vintage_year = Column(Integer)
    status = Column(String, default='Cosechado')
    initial_grape_kg = Column(Numeric(10, 2))
    total_liters = Column(Numeric(10, 2))
    liters_unassigned = Column(Numeric(10, 2))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    origin_parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True)

class Container(Base):
    __tablename__ = "containers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    capacity_liters = Column(Numeric(10, 2), nullable=False)
    material = Column(String)
    location = Column(String)
    status = Column(String, default='vacío')
    current_volume = Column(Numeric(10, 2), default=0)
    current_lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

class Movement(Base):
    __tablename__ = "movements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    source_container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    destination_container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    volume = Column(Numeric(10, 2), nullable=False)
    movement_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    type = Column(String, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

# --- NUEVAS TABLAS PARA EL "CEREBRO" DEL SAAS ---

class Parcel(Base):
    __tablename__ = "parcels"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    variety = Column(String)
    area_hectares = Column(Numeric(8, 4))
    geojson_coordinates = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class CostParameter(Base):
    __tablename__ = "cost_parameters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    parameter_name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False) # <--- NUEVA COLUMNA
    value = Column(Numeric(10, 2), nullable=False)
    unit = Column(String)
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow)

class Cost(Base):
    __tablename__ = "costs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    related_lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True) # <-- MODIFICADO
    related_parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True) # <-- NUEVA COLUMNA
    cost_type = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    cost_date = Column(Date, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    sku = Column(String, unique=True)
    description = Column(Text)
    price = Column(Numeric(10, 2))
    unit_cost = Column(Numeric(10, 4)) # <--- NUEVA COLUMNA
    wine_lot_origin_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    stock_units = Column(Integer, default=0)
    
class Sale(Base):
    __tablename__ = "sales"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    sale_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    customer_name = Column(String, nullable=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)

class SaleDetail(Base):
    __tablename__ = "sale_details"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)