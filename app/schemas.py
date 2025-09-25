# Saas_GrapeIQ_V1.0/app/schemas.py

from pydantic import BaseModel
from typing import Optional, List
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
    plot_name: Optional[str] = None

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

# --- ESQUEMAS PARA GESTIÓN DE BODEGA Y TRAZABILIDAD ---

# Lotes de Vino
class WineLotBase(BaseModel):
    name: str
    grape_variety: Optional[str] = None
    vintage_year: Optional[int] = None

class WineLotCreate(WineLotBase):
    initial_grape_kg: float

class WineLotUpdate(WineLotBase):
    initial_grape_kg: Optional[float] = None

class WineLot(WineLotBase):
    id: uuid.UUID
    status: str
    initial_grape_kg: Optional[float] = None
    total_liters: Optional[float] = None
    liters_unassigned: Optional[float] = None
    class Config:
        from_attributes = True

# Contenedores (Barricas y Depósitos)
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

# Movimientos
class MovementCreate(BaseModel):
    lot_id: uuid.UUID
    source_container_id: Optional[uuid.UUID] = None
    destination_container_id: Optional[uuid.UUID] = None
    volume: float
    type: str

# --- ¡NUEVO ESQUEMA PARA RELLENAR! ---
class ToppingUpCreate(BaseModel):
    lot_id: uuid.UUID
    destination_container_id: uuid.UUID
    volume: float
    type: str = "Rellenado"


# Esquemas para las Vistas de la Interfaz
class WineLotInContainer(WineLot):
    containers: List[Container]

class TraceabilityView(BaseModel):
    harvested: List[WineLot]
    fermenting: List[WineLotInContainer]
    aging: List[WineLotInContainer]
    ready_to_bottle: List[WineLotInContainer] # Nuevo estado para la vista
    bottled: List[WineLot]

# Esquema para actualizar el estado de un lote
class WineLotStatusUpdate(BaseModel):
    new_status: str

# Esquemas para el Trasiego a Múltiples Destinos
class MovementDestination(BaseModel):
    destination_container_id: uuid.UUID
    volume: float

class BulkMovementCreate(BaseModel):
    lot_id: uuid.UUID
    source_container_id: uuid.UUID
    destinations: List[MovementDestination]
    type: str = "Trasiego"

# Esquema para Embotellado
class BottlingCreate(BaseModel):
    lot_id: uuid.UUID
    source_container_ids: List[uuid.UUID]
    type: str = "Embotellado"