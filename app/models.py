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
    type = Column(String, nullable=False) # Depósito, Barrica
    capacity_liters = Column(Numeric(10, 2), nullable=False)
    material = Column(String) # Inox, Hormigón, Roble Francés, Roble Americano
    location = Column(String)
    status = Column(String, default='vacío') # vacío, ocupado, limpieza
    current_volume = Column(Numeric(10, 2), default=0)
    current_lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # --- NUEVOS CAMPOS PARA CRIANZA ---
    barrel_age = Column(Integer, nullable=True) # Edad o número de usos de la barrica
    toast_level = Column(String, nullable=True) # Nivel de tostado: Ligero, Medio, Fuerte
    cooperage = Column(String, nullable=True) # Tonelería o fabricante

class Movement(Base):
    __tablename__ = "movements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    source_container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    destination_container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    volume = Column(Numeric(10, 2), nullable=False)
    movement_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    type = Column(String, nullable=False) # Llenado Inicial, Trasiego, Embotellado, Rellenado
    notes = Column(Text, nullable=True) # --- NUEVO CAMPO PARA NOTAS DE CATA ---
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

# --- NUEVAS TABLAS PARA TRAZABILIDAD AVANZADA ---

class FermentationControl(Base):
    __tablename__ = "fermentation_controls"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    control_date = Column(Date, nullable=False, default=datetime.utcnow)
    temperature = Column(Numeric(5, 2))
    density = Column(Numeric(6, 4))
    notes = Column(Text, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

class LabAnalytic(Base):
    __tablename__ = "lab_analytics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    analysis_date = Column(Date, nullable=False, default=datetime.utcnow)
    alcoholic_degree = Column(Numeric(4, 2), nullable=True)
    total_acidity = Column(Numeric(5, 2), nullable=True)
    volatile_acidity = Column(Numeric(4, 2), nullable=True)
    ph = Column(Numeric(4, 2), nullable=True)
    free_so2 = Column(Integer, nullable=True)
    total_so2 = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

class DryGood(Base):
    __tablename__ = "dry_goods"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    material_type = Column(String, nullable=False) # Botella, Corcho, Cápsula, Etiqueta
    supplier = Column(String, nullable=True)
    model_reference = Column(String, nullable=True)
    supplier_lot_number = Column(String, nullable=True)
    
class BottlingEvent(Base):
    __tablename__ = "bottling_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    bottling_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    official_lot_number = Column(String, nullable=False) # Lote impreso en la botella
    dissolved_oxygen = Column(Numeric(5, 2), nullable=True)
    
    bottle_lot_id = Column(UUID(as_uuid=True), ForeignKey("dry_goods.id"), nullable=True)
    cork_lot_id = Column(UUID(as_uuid=True), ForeignKey("dry_goods.id"), nullable=True)
    capsule_lot_id = Column(UUID(as_uuid=True), ForeignKey("dry_goods.id"), nullable=True)
    label_lot_id = Column(UUID(as_uuid=True), ForeignKey("dry_goods.id"), nullable=True)
    
    retained_samples = Column(Integer, default=0)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

# --- TABLAS DE COSTES, PRODUCTOS Y VENTAS (SIN CAMBIOS) ---

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