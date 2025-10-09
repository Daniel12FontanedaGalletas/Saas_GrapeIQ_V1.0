# Saas_GrapeIQ_V1.0/app/models.py

from sqlalchemy import Column, Integer, String, Numeric, Date, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

# --- TABLA PARA DATOS DE TEMPERATURA Y HUMEDAD ---
class RoomCondition(Base):
    __tablename__ = "room_conditions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    room_name = Column(String, nullable=False) # Ej: "Sala de Depósitos", "Bodega de Crianza"
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)


# --- TABLA PARA EVENTOS ESPECIALES ---
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
    area_hectares = Column(Float)
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
    initial_grape_kg = Column(Float)
    total_liters = Column(Float)
    liters_unassigned = Column(Float)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    origin_parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True)
    wine_type = Column(String) # tinto, blanco, rosado

class Container(Base):
    __tablename__ = "containers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # Depósito, Barrica
    capacity_liters = Column(Float, nullable=False)
    material = Column(String) # Inox, Hormigón, Roble Francés, Roble Americano
    location = Column(String)
    status = Column(String, default='vacío') # vacío, ocupado, limpieza
    current_volume = Column(Float, default=0)
    current_lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    barrel_age = Column(Integer, nullable=True) # Edad o número de usos de la barrica
    toast_level = Column(String, nullable=True) # Nivel de tostado: Ligero, Medio, Fuerte
    cooperage = Column(String, nullable=True) # Tonelería o fabricante

class Movement(Base):
    __tablename__ = "movements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    source_container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    destination_container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    volume = Column(Float, nullable=False)
    movement_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    type = Column(String, nullable=False) # Llenado Inicial, Trasiego, Embotellado, Rellenado
    notes = Column(Text, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

# --- TABLAS PARA LABORATORIO ---
class WinemakingLog(Base):
    __tablename__ = "winemaking_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    log_date = Column(Date, nullable=False, default=datetime.utcnow)
    
    # Parámetros de la uva/mosto
    sugar_level = Column(Float) # Baumé o Brix
    total_acidity = Column(Float) # g/L tartárico
    ph = Column(Float, nullable=True) # pH se mide principalmente en control
    reception_temp = Column(Float) # °C
    added_so2 = Column(Integer) # mg/L
    turbidity = Column(String, nullable=True)
    color_intensity = Column(String, nullable=True)
    aromas = Column(Text, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

class FermentationControl(Base):
    __tablename__ = "fermentation_controls"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"))
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    control_date = Column(Date, nullable=False, default=datetime.utcnow)
    temperature = Column(Float)
    density = Column(Float)
    notes = Column(Text, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Nuevos campos
    residual_sugar = Column(Float, nullable=True)
    potential_alcohol = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    volatile_acidity = Column(Float, nullable=True)
    free_so2 = Column(Integer, nullable=True)
    
    # --- COLUMNA AÑADIDA Y CORREGIDA ---
    total_acidity = Column(Float, nullable=True)

class LabAnalytic(Base):
    __tablename__ = "lab_analytics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=False)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=True)
    analysis_date = Column(Date, nullable=False, default=datetime.utcnow)
    alcoholic_degree = Column(Float, nullable=True)
    total_acidity = Column(Float, nullable=True)
    volatile_acidity = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
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
    dissolved_oxygen = Column(Float, nullable=True)
    
    bottle_lot_id = Column(UUID(as_uuid=True), ForeignKey("dry_goods.id"), nullable=True)
    cork_lot_id = Column(UUID(as_uuid=True), ForeignKey("dry_goods.id"), nullable=True)
    capsule_lot_id = Column(UUID(as_uuid=True), ForeignKey("dry_goods.id"), nullable=True)
    label_lot_id = Column(UUID(as_uuid=True), ForeignKey("dry_goods.id"), nullable=True)
    
    retained_samples = Column(Integer, default=0)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

# --- TABLAS DE COSTES, PRODUCTOS Y VENTAS ---
class CostParameter(Base):
    __tablename__ = "cost_parameters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    parameter_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String)
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow)

class Cost(Base):
    __tablename__ = "costs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    related_lot_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    related_parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True)
    cost_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text)
    cost_date = Column(Date, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    sku = Column(String, unique=True)
    description = Column(Text)
    price = Column(Float)
    unit_cost = Column(Float)
    wine_lot_origin_id = Column(UUID(as_uuid=True), ForeignKey("wine_lots.id"), nullable=True)
    stock_units = Column(Integer, default=0)
    variety = Column(String, nullable=True)

class Sale(Base):
    __tablename__ = "sales"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    sale_date = Column(Date, default=datetime.utcnow)
    customer_name = Column(String, nullable=True)
    total_amount = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    is_weekend = Column(Boolean, default=False)
    holiday_name = Column(String, nullable=True)
    avg_temperature = Column(Float, nullable=True)
    channel = Column(String, nullable=True)

class SaleDetail(Base):
    __tablename__ = "sale_details"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    on_promotion = Column(Boolean, default=False)
    discount_percentage = Column(Float, default=0.0)