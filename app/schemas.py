# Saas_GrapeIQ_V1.0/app/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
import uuid
from datetime import date, datetime

# --- Esquemas de Autenticación y Usuarios ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    role: str = "lector"

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    class Config:
        from_attributes = True

class UserInDB(User):
    hashed_password: str

class UserUpdateResponse(UserInDB):
    new_access_token: str
    token_type: str = "bearer"

# --- Esquemas del Cuaderno de Campo ---
class FieldLogBase(BaseModel):
    activity_type: str
    description: Optional[str] = None
    parcel_id: Optional[uuid.UUID] = None

class FieldLogCreate(FieldLogBase):
    log_date: date
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class FieldLog(FieldLogBase):
    id: uuid.UUID
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    all_day: bool
    class Config:
        from_attributes = True

# --- ESQUEMAS PARA LA ARQUITECTURA CENTRAL ---
class WineLotBase(BaseModel):
    name: str
    grape_variety: Optional[str] = None
    vintage_year: Optional[int] = None

class WineLotCreate(WineLotBase):
    initial_grape_kg: float
    origin_parcel_id: uuid.UUID

class WineLotUpdate(WineLotBase):
    initial_grape_kg: Optional[float] = None

class WineLot(WineLotBase):
    id: uuid.UUID
    status: str
    initial_grape_kg: Optional[float] = None
    total_liters: Optional[float] = None
    liters_unassigned: Optional[float] = None
    origin_parcel_id: Optional[uuid.UUID] = None
    class Config:
        from_attributes = True

class ContainerBase(BaseModel):
    name: str
    type: str
    capacity_liters: float
    material: Optional[str] = None
    location: Optional[str] = None

class ContainerCreate(ContainerBase):
    pass

class ContainerUpdate(ContainerBase):
    pass

class Container(ContainerBase):
    id: uuid.UUID
    status: str
    current_volume: float
    current_lot_id: Optional[uuid.UUID] = None
    class Config:
        from_attributes = True

class MovementCreate(BaseModel):
    lot_id: uuid.UUID
    source_container_id: Optional[uuid.UUID] = None
    destination_container_id: Optional[uuid.UUID] = None
    volume: float
    type: str

class ToppingUpCreate(BaseModel):
    lot_id: uuid.UUID
    destination_container_id: uuid.UUID
    volume: float
    type: str = "Rellenado"

class WineLotInContainer(WineLot):
    containers: List[Container] = []

class TraceabilityView(BaseModel):
    harvested: List[WineLot]
    fermenting: List[WineLotInContainer]
    aging: List[WineLotInContainer]
    ready_to_bottle: List[WineLotInContainer]
    bottled: List[WineLot]

class WineLotStatusUpdate(BaseModel):
    new_status: str

class MovementDestination(BaseModel):
    destination_container_id: uuid.UUID
    volume: float

class BulkMovementCreate(BaseModel):
    lot_id: uuid.UUID
    source_container_id: uuid.UUID
    destinations: List[MovementDestination]
    type: str = "Trasiego"

class BottlingCreate(BaseModel):
    lot_id: uuid.UUID
    source_container_ids: List[uuid.UUID]
    type: str = "Embotellado"

class BottlingToProductCreate(BaseModel):
    lot_id: uuid.UUID
    source_container_ids: List[uuid.UUID]
    product_name: str
    product_sku: str
    product_price: float
    bottles_produced: int

# --- Esquemas para el "Cerebro" ---
class ParcelBase(BaseModel):
    name: str
    variety: Optional[str] = None
    area_hectares: Optional[float] = None
    geojson_coordinates: Optional[Any] = None

class ParcelCreate(ParcelBase):
    pass

class Parcel(ParcelBase):
    id: uuid.UUID
    class Config:
        from_attributes = True

class CostParameterBase(BaseModel):
    parameter_name: str
    category: str
    value: float
    unit: Optional[str] = None

class CostParameterCreate(CostParameterBase):
    pass

class CostParameter(CostParameterBase):
    id: uuid.UUID
    last_updated: datetime
    class Config:
        from_attributes = True

class CostBase(BaseModel):
    related_lot_id: Optional[uuid.UUID] = None
    related_parcel_id: Optional[uuid.UUID] = None
    cost_type: str
    amount: float
    description: Optional[str] = None
    cost_date: date = Field(default_factory=date.today)

class CostCreate(CostBase):
    pass

class Cost(CostBase):
    id: uuid.UUID
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    sku: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    variety: Optional[str] = None

class ProductCreate(ProductBase):
    wine_lot_origin_id: Optional[uuid.UUID] = None
    stock_units: int = 0

class Product(ProductBase):
    id: uuid.UUID
    unit_cost: Optional[float] = None
    wine_lot_origin_id: Optional[uuid.UUID] = None
    stock_units: int
    class Config:
        from_attributes = True

# --- Esquemas para Ventas ---
class SaleDetailBase(BaseModel):
    product_id: uuid.UUID
    quantity: int
    unit_price: float

class SaleDetailCreate(SaleDetailBase):
    on_promotion: bool = False
    discount_percentage: float = 0.0

class SaleDetail(SaleDetailBase):
    id: uuid.UUID
    sale_id: uuid.UUID
    on_promotion: bool
    discount_percentage: float
    class Config:
        from_attributes = True

class SaleBase(BaseModel):
    customer_name: Optional[str] = None
    notes: Optional[str] = None

class SaleCreate(SaleBase):
    sale_date: date = Field(default_factory=date.today)
    details: List[SaleDetailCreate]
    is_weekend: Optional[bool] = None
    holiday_name: Optional[str] = None
    avg_temperature: Optional[float] = None

class Sale(SaleBase):
    id: uuid.UUID
    sale_date: date
    total_amount: float
    details: List[SaleDetail] = []
    is_weekend: bool
    holiday_name: Optional[str] = None
    avg_temperature: Optional[float] = None
    class Config:
        from_attributes = True
        
class CategorySummary(BaseModel):
    category: str
    total_amount: float
    percentage: float

class CostSummaryResponse(BaseModel):
    grand_total: float
    details: List[CategorySummary]
    
class TraceabilityKanbanView(BaseModel):
    harvested: List[WineLot]
    fermenting: List[WineLotInContainer]
    aging: List[WineLotInContainer]
    ready_to_bottle: List[WineLotInContainer]
    bottled: List[WineLot]

class LotStatusUpdate(BaseModel):
    new_status: str
    
class CostRecord(BaseModel):
    id: uuid.UUID
    cost_type: str
    amount: float
    description: Optional[str] = None
    cost_date: date
    related_lot_id: Optional[uuid.UUID] = None
    class Config:
        from_attributes = True
        
class PaginatedCostRecordResponse(BaseModel):
    records: list[CostRecord]
    total_records: int
    page: int
    page_size: int
    total_pages: int
    
class ProductSimple(BaseModel):
    id: uuid.UUID
    name: str
    class Config:
        from_attributes = True
        
class SunburstItem(BaseModel):
    name: str
    value: float

class SunburstCategory(BaseModel):
    name: str
    children: List[SunburstItem]

# --- ESQUEMAS PARA FORECASTING AVANZADO ---

class ForecastPoint(BaseModel):
    date: str
    forecast: float
    forecast_lower: float
    forecast_upper: float

class ForecastResponse(BaseModel):
    prediction: List[ForecastPoint]
    components: Dict[str, List[float]]

class ScenarioRegressor(BaseModel):
    start_date: date
    end_date: date
    name: str
    value: float

# --- NUEVO: Esquema para añadir eventos personalizados desde la UI ---
class FutureEvent(BaseModel):
    holiday: str # Nombre del evento, ej: "Feria del Vino Local"
    ds: date     # Fecha del evento

class ScenarioRequest(BaseModel):
    product_id: Optional[str] = 'total'
    periods: int = 90
    future_regressors: List[ScenarioRegressor] = []
    future_events: List[FutureEvent] = [] # <-- Se añade la lista de eventos