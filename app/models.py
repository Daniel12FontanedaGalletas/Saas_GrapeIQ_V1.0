# Saas_GrapeIQ_V1.0/app/models.py (COMPLETO Y CORRECTO)

from sqlalchemy import Column, Integer, String, Numeric, Date, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

# --- TABLA NUEVA PARA EVENTOS ESPECIALES ---
class SpecialEvent(Base):
    __tablename__ = "special_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    event_name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)

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
class Parcel(Base):
    __tablename__ = "parcels"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    variety = Column(String)
    area_hectares = Column(Numeric(8, 4))
    geojson_coordinates = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class FieldLog(Base):
    __tablename__ = "field_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    start_datetime = Column(DateTime(timezone=True), default=datetime.utcnow)
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    activity_type = Column(String)
    description = Column(Text, nullable=True)
    all_day = Column(Boolean, default=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True)

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

class CostParameter(Base):
    __tablename__ = "cost_parameters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    parameter_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    value = Column(Numeric(10, 2), nullable=False)
    unit = Column(String)
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow)

class Cost(Base):
    __tablename__ = "costs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    related_lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    related_parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True)
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
    unit_cost = Column(Numeric(10, 4))
    wine_lot_origin_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    stock_units = Column(Integer, default=0)
    variety = Column(String, nullable=True)

class Sale(Base):
    __tablename__ = "sales"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    sale_date = Column(Date, default=datetime.utcnow)
    customer_name = Column(String, nullable=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)
    is_weekend = Column(Boolean, default=False)
    holiday_name = Column(String, nullable=True)
    avg_temperature = Column(Numeric(4, 1), nullable=True)
    channel = Column(String, nullable=True)

class SaleDetail(Base):
    __tablename__ = "sale_details"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    on_promotion = Column(Boolean, default=False)
    discount_percentage = Column(Numeric(5, 2), default=0.0)