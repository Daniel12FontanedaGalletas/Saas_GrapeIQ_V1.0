# Saas_GrapeIQ_V1.0/app/routers/parcels.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
import json
from psycopg2.extras import RealDictCursor

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/parcels",
    tags=["Parcels"],
    dependencies=[Depends(security.get_current_active_user)]
)

@router.post("/", response_model=schemas.Parcel, status_code=201)
def create_parcel(parcel: schemas.ParcelCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    geojson_str = json.dumps(parcel.geojson_coordinates) if parcel.geojson_coordinates else None
    query = """
        INSERT INTO parcels (id, tenant_id, name, variety, area_hectares, geojson_coordinates)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(uuid.uuid4()), str(current_user.tenant_id), parcel.name, parcel.variety, parcel.area_hectares, geojson_str))
                new_parcel = cur.fetchone()
                conn.commit()
                return new_parcel
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

@router.delete("/{parcel_id}", status_code=204)
def delete_parcel(parcel_id: uuid.UUID, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM wine_lots WHERE origin_parcel_id = %s", (str(parcel_id),))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="No se puede eliminar una parcela que ya está asociada a un lote de vino.")
                
                cur.execute("DELETE FROM parcels WHERE id = %s AND tenant_id = %s", (str(parcel_id), str(current_user.tenant_id)))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Parcela no encontrada.")
                conn.commit()
    except HTTPException as e:
        raise e
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")