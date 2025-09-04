from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import modelss
from ..database import get_db
from ..services.security import get_current_active_admin # Cambiado a admin
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/financials",
    tags=["financials"],
    # --- PROTECCIÓN A NIVEL DE ROUTER ---
    dependencies=[Depends(get_current_active_admin)] 
)

class FinancialEntryCreate(BaseModel):
    description: str
    amount: float
    entry_type: str

class FinancialEntry(BaseModel):
    id: int
    description: str
    amount: float
    entry_type: str
    class Config:
        orm_mode = True

@router.post("/", response_model=FinancialEntry)
def create_financial_entry(
    entry: FinancialEntryCreate, 
    db: Session = Depends(get_db), 
    current_user: modelss.User = Depends(get_current_active_admin)
):
    db_entry = modelss.FinancialEntry(**entry.dict(), owner_id=current_user.id)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@router.get("/", response_model=List[FinancialEntry])
def read_financial_entries(db: Session = Depends(get_db), current_user: modelss.User = Depends(get_current_active_admin)):
    return db.query(modelss.FinancialEntry).filter(modelss.FinancialEntry.owner_id == current_user.id).all()

@router.delete("/{entry_id}", status_code=204)
def delete_financial_entry(
    entry_id: int, 
    db: Session = Depends(get_db), 
    current_user: modelss.User = Depends(get_current_active_admin)
):
    entry = db.query(modelss.FinancialEntry).filter(modelss.FinancialEntry.id == entry_id, modelss.FinancialEntry.owner_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"ok": True}