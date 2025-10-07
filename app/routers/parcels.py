# Saas_GrapeIQ_V1.0/app/routers/parcels.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
from psycopg2.extras import RealDictCursor
import json # <--- 1. IMPORTANTE: Importar el módulo json

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/parcels",
    tags=["Parcelas"],
    dependencies=[Depends(security.get_current_active_user)]
)

@router.post("/", response_model=schemas.Parcel, status_code=201)
def create_parcel(parcel: schemas.ParcelCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    query = """
        INSERT INTO parcels (id, name, area_hectares, variety, tenant_id, geojson_coordinates)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                new_id = str(uuid.uuid4())
                
                # --- 2. CORRECCIÓN: Usar json.dumps en lugar de str() ---
                geojson_str = json.dumps(parcel.geojson_coordinates) if parcel.geojson_coordinates else None

                cur.execute(query, (
                    new_id, parcel.name, parcel.area_hectares,
                    parcel.variety, str(current_user.tenant_id),
                    geojson_str
                ))
                new_parcel = cur.fetchone()
                conn.commit()
                return schemas.Parcel.model_validate(new_parcel)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

@router.get("/", response_model=List[schemas.Parcel])
def get_all_parcels(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    query = "SELECT * FROM parcels WHERE tenant_id = %s ORDER BY name"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                parcels = cur.fetchall()
                return parcels
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

@router.get("/{parcel_id}", response_model=schemas.Parcel)
def get_parcel(parcel_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    query = "SELECT * FROM parcels WHERE id = %s AND tenant_id = %s"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(parcel_id), str(current_user.tenant_id)))
                parcel = cur.fetchone()
                if not parcel:
                    raise HTTPException(status_code=404, detail="Parcela no encontrada.")
                return parcel
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

@router.put("/{parcel_id}", response_model=schemas.Parcel)
def update_parcel(parcel_id: uuid.UUID, parcel: schemas.ParcelCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    query = """
        UPDATE parcels
        SET name = %s, area_hectares = %s, variety = %s, geojson_coordinates = %s
        WHERE id = %s AND tenant_id = %s
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # --- 3. CORRECCIÓN: Usar json.dumps también aquí ---
                geojson_str = json.dumps(parcel.geojson_coordinates) if parcel.geojson_coordinates else None
                
                cur.execute(query, (
                    parcel.name, parcel.area_hectares,
                    parcel.variety, 
                    geojson_str,
                    str(parcel_id), str(current_user.tenant_id)
                ))
                updated_parcel = cur.fetchone()
                if not updated_parcel:
                    raise HTTPException(status_code=404, detail="Parcela no encontrada.")
                conn.commit()
                return updated_parcel
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

@router.delete("/{parcel_id}", status_code=204)
def delete_parcel(parcel_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM parcels WHERE id = %s AND tenant_id = %s", (str(parcel_id), str(current_user.tenant_id)))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Parcela no encontrada.")
                conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")