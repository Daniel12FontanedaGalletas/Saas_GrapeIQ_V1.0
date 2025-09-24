from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
import uuid
from datetime import date, datetime, time

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None

class RoleEnum(str, Enum):
    admin = "admin"
    lector = "lector"

class UserBase(BaseModel):
    username: str
    role: Optional[RoleEnum] = RoleEnum.lector

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

class ProductBase(BaseModel):
    sku: str
    name: str
    product_type: str
    price_per_unit: float
    cost_per_unit: Optional[float] = None
    stock_quantity: Optional[int] = None

class Product(ProductBase):
    id: int
    class Config:
        from_attributes = True

class FinancialEntryBase(BaseModel):
    description: str
    amount: float
    entry_type: str

class FinancialEntry(FinancialEntryBase):
    id: int
    owner_id: uuid.UUID
    class Config:
        from_attributes = True

# --- Esquemas para el Cuaderno de Campo ---
class FieldLogBase(BaseModel):
    activity_type: str
    description: Optional[str] = None
    plot_name: Optional[str] = None

class FieldLogCreate(FieldLogBase):
    # El frontend enviará la fecha y horas opcionales de inicio y fin
    log_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None

class FieldLog(FieldLogBase):
    id: uuid.UUID
    # El backend devolverá datetimes completos de inicio y fin
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    all_day: bool

    class Config:
        from_attributes = True
        
class GrapeLotBase(BaseModel):
    harvest_date: date
    variety: str
    quantity_kg: float
    origin_plot: Optional[str] = None

class GrapeLotCreate(GrapeLotBase):
    pass

class GrapeLot(GrapeLotBase):
    id: uuid.UUID
    status: str
    class Config:
        from_attributes = True

# --- Vinificaciones ---
class VinificationBase(BaseModel):
    start_date: date
    description: Optional[str] = None

class VinificationCreate(VinificationBase):
    grape_lot_id: uuid.UUID

class Vinification(VinificationBase):
    id: uuid.UUID
    status: str
    grape_lot_id: uuid.UUID
    class Config:
        from_attributes = True

# --- Embotellados ---
class BottlingBase(BaseModel):
    bottling_date: date
    number_of_bottles: int
    batch_number: Optional[str] = None

class BottlingCreate(BottlingBase):
    vinification_id: uuid.UUID

class Bottling(BottlingBase):
    id: uuid.UUID
    vinification_id: uuid.UUID
    class Config:
        from_attributes = True

# --- Esquema combinado para el Dashboard ---
class TraceabilityDashboard(BaseModel):
    grape_lots: List[GrapeLot]
    vinifications: List[Vinification]
    bottlings: List[Bottling]