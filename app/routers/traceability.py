# Saas_GrapeIQ_V1.0/app/routers/traceability.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from contextlib import closing
import uuid

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/traceability",
    tags=["Traceability"],
)

# --- DASHBOARD ---
@router.get("/", response_model=schemas.TraceabilityDashboard)
def get_traceability_dashboard(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("SELECT id, harvest_date, variety, quantity_kg, origin_plot, status FROM grape_lots WHERE tenant_id = %s ORDER BY harvest_date DESC", (str(current_user.tenant_id),))
                lots = [schemas.GrapeLot(id=r[0], harvest_date=r[1], variety=r[2], quantity_kg=r[3], origin_plot=r[4], status=r[5]) for r in cur.fetchall()]
                cur.execute("SELECT id, start_date, description, status, grape_lot_id FROM vinifications WHERE tenant_id = %s ORDER BY start_date DESC", (str(current_user.tenant_id),))
                vinifications = [schemas.Vinification(id=r[0], start_date=r[1], description=r[2], status=r[3], grape_lot_id=r[4]) for r in cur.fetchall()]
                cur.execute("SELECT id, bottling_date, number_of_bottles, batch_number, vinification_id FROM bottlings WHERE tenant_id = %s ORDER BY bottling_date DESC", (str(current_user.tenant_id),))
                bottlings = [schemas.Bottling(id=r[0], bottling_date=r[1], number_of_bottles=r[2], batch_number=r[3], vinification_id=r[4]) for r in cur.fetchall()]
        return schemas.TraceabilityDashboard(grape_lots=lots, vinifications=vinifications, bottlings=bottlings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener datos de trazabilidad: {e}")

# --- GRAPE LOTS ---
@router.post("/grape-lots", response_model=schemas.GrapeLot, status_code=201)
def create_grape_lot(lot: schemas.GrapeLotCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("INSERT INTO grape_lots (harvest_date, variety, quantity_kg, origin_plot, tenant_id) VALUES (%s, %s, %s, %s, %s) RETURNING id, harvest_date, variety, quantity_kg, origin_plot, status", 
                        (lot.harvest_date, lot.variety, lot.quantity_kg, lot.origin_plot, str(current_user.tenant_id)))
            rec = cur.fetchone()
            conn.commit()
    return schemas.GrapeLot(id=rec[0], harvest_date=rec[1], variety=rec[2], quantity_kg=rec[3], origin_plot=rec[4], status=rec[5])

@router.get("/grape-lots/{lot_id}", response_model=schemas.GrapeLot)
def get_grape_lot(lot_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, harvest_date, variety, quantity_kg, origin_plot, status FROM grape_lots WHERE id = %s AND tenant_id = %s", (str(lot_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
    if not rec: raise HTTPException(status_code=404, detail="Lote de uva no encontrado.")
    return schemas.GrapeLot(id=rec[0], harvest_date=rec[1], variety=rec[2], quantity_kg=rec[3], origin_plot=rec[4], status=rec[5])

@router.put("/grape-lots/{lot_id}", response_model=schemas.GrapeLot)
def update_grape_lot(lot_id: uuid.UUID, lot: schemas.GrapeLotCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE grape_lots SET harvest_date=%s, variety=%s, quantity_kg=%s, origin_plot=%s WHERE id=%s AND tenant_id=%s RETURNING id, harvest_date, variety, quantity_kg, origin_plot, status",
                        (lot.harvest_date, lot.variety, lot.quantity_kg, lot.origin_plot, str(lot_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
            conn.commit()
    if not rec: raise HTTPException(status_code=404, detail="Lote de uva no encontrado para actualizar.")
    return schemas.GrapeLot(id=rec[0], harvest_date=rec[1], variety=rec[2], quantity_kg=rec[3], origin_plot=rec[4], status=rec[5])

@router.delete("/grape-lots/{lot_id}", status_code=204)
def delete_grape_lot(lot_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM grape_lots WHERE id=%s AND tenant_id=%s", (str(lot_id), str(current_user.tenant_id)))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Lote no encontrado.")
            cur.execute("DELETE FROM bottlings WHERE vinification_id IN (SELECT id FROM vinifications WHERE grape_lot_id = %s)", (str(lot_id),))
            cur.execute("DELETE FROM vinifications WHERE grape_lot_id = %s", (str(lot_id),))
            cur.execute("DELETE FROM grape_lots WHERE id = %s", (str(lot_id),))
            conn.commit()

# --- VINIFICATIONS ---
@router.post("/vinifications", response_model=schemas.Vinification, status_code=201)
def create_vinification(vini: schemas.VinificationCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE grape_lots SET status = 'vinificando' WHERE id = %s AND tenant_id = %s", (str(vini.grape_lot_id), str(current_user.tenant_id)))
            cur.execute("INSERT INTO vinifications (start_date, description, grape_lot_id, tenant_id) VALUES (%s, %s, %s, %s) RETURNING id, start_date, description, status, grape_lot_id", (vini.start_date, vini.description, str(vini.grape_lot_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
            conn.commit()
    return schemas.Vinification(id=rec[0], start_date=rec[1], description=rec[2], status=rec[3], grape_lot_id=rec[4])

@router.get("/vinifications/{vini_id}", response_model=schemas.Vinification)
def get_vinification(vini_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, start_date, description, status, grape_lot_id FROM vinifications WHERE id = %s AND tenant_id = %s", (str(vini_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
    if not rec: raise HTTPException(status_code=404, detail="Vinificación no encontrada.")
    return schemas.Vinification(id=rec[0], start_date=rec[1], description=rec[2], status=rec[3], grape_lot_id=rec[4])

@router.put("/vinifications/{vini_id}", response_model=schemas.Vinification)
def update_vinification(vini_id: uuid.UUID, vini: schemas.VinificationBase, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE vinifications SET start_date=%s, description=%s WHERE id=%s AND tenant_id=%s RETURNING id, start_date, description, status, grape_lot_id",
                        (vini.start_date, vini.description, str(vini_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
            conn.commit()
    if not rec: raise HTTPException(status_code=404, detail="Vinificación no encontrada para actualizar.")
    return schemas.Vinification(id=rec[0], start_date=rec[1], description=rec[2], status=rec[3], grape_lot_id=rec[4])

@router.delete("/vinifications/{vini_id}", status_code=204)
def delete_vinification(vini_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT grape_lot_id FROM vinifications WHERE id=%s AND tenant_id=%s", (str(vini_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
            if not rec: raise HTTPException(status_code=404, detail="Vinificación no encontrada.")
            grape_lot_id = rec[0]
            cur.execute("DELETE FROM bottlings WHERE vinification_id = %s", (str(vini_id),))
            cur.execute("DELETE FROM vinifications WHERE id=%s", (str(vini_id),))
            cur.execute("UPDATE grape_lots SET status='disponible' WHERE id=%s", (str(grape_lot_id),))
            conn.commit()

# --- BOTTLINGS ---
@router.post("/bottlings", response_model=schemas.Bottling, status_code=201)
def create_bottling(bottling: schemas.BottlingCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE vinifications SET status = 'finalizada' WHERE id = %s AND tenant_id = %s", (str(bottling.vinification_id), str(current_user.tenant_id)))
            cur.execute("INSERT INTO bottlings (bottling_date, number_of_bottles, batch_number, vinification_id, tenant_id) VALUES (%s, %s, %s, %s, %s) RETURNING id, bottling_date, number_of_bottles, batch_number, vinification_id", 
                        (bottling.bottling_date, bottling.number_of_bottles, bottling.batch_number, str(bottling.vinification_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
            conn.commit()
    return schemas.Bottling(id=rec[0], bottling_date=rec[1], number_of_bottles=rec[2], batch_number=rec[3], vinification_id=rec[4])

@router.get("/bottlings/{bottling_id}", response_model=schemas.Bottling)
def get_bottling(bottling_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, bottling_date, number_of_bottles, batch_number, vinification_id FROM bottlings WHERE id=%s AND tenant_id=%s", (str(bottling_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
    if not rec: raise HTTPException(status_code=404, detail="Embotellado no encontrado.")
    return schemas.Bottling(id=rec[0], bottling_date=rec[1], number_of_bottles=rec[2], batch_number=rec[3], vinification_id=rec[4])

@router.put("/bottlings/{bottling_id}", response_model=schemas.Bottling)
def update_bottling(bottling_id: uuid.UUID, bottling: schemas.BottlingBase, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE bottlings SET bottling_date=%s, number_of_bottles=%s, batch_number=%s WHERE id=%s AND tenant_id=%s RETURNING id, bottling_date, number_of_bottles, batch_number, vinification_id",
                        (bottling.bottling_date, bottling.number_of_bottles, bottling.batch_number, str(bottling_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
            conn.commit()
    if not rec: raise HTTPException(status_code=404, detail="Embotellado no encontrado para actualizar.")
    return schemas.Bottling(id=rec[0], bottling_date=rec[1], number_of_bottles=rec[2], batch_number=rec[3], vinification_id=rec[4])

@router.delete("/bottlings/{bottling_id}", status_code=204)
def delete_bottling(bottling_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    with get_db_connection() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT vinification_id FROM bottlings WHERE id=%s AND tenant_id=%s", (str(bottling_id), str(current_user.tenant_id)))
            rec = cur.fetchone()
            if not rec: raise HTTPException(status_code=404, detail="Embotellado no encontrado.")
            vinification_id = rec[0]
            cur.execute("DELETE FROM bottlings WHERE id=%s", (str(bottling_id),))
            cur.execute("UPDATE vinifications SET status='en_proceso' WHERE id=%s", (str(vinification_id),))
            conn.commit()