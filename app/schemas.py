from pydantic import BaseModel
from typing import Optional
from enum import Enum
import uuid

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

# --- ¡MODIFICACIÓN CLAVE! ---
# Creamos un nuevo modelo que sí incluye la contraseña hasheada.
# Este modelo solo se usará internamente en el backend.
class UserInDB(User):
    hashed_password: str

# --- El resto de tus schemas se mantienen igual ---

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

class UserUpdateResponse(UserInDB):
    new_access_token: str
    token_type: str = "bearer"
