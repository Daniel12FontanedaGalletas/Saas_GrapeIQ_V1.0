# Saas_GrapeIQ_V1.0/app/routers/parcels.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
import json

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/parcels",
    tags=["Parcels"],
)

@router.post("/", response_model=schemas.Parcel, status_code=201)
def create_parcel(
    parcel: schemas.ParcelCreate, 
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Crea una nueva parcela en la base de datos.
    """
    query = """
        INSERT INTO parcels (tenant_id, name, variety, area_hectares, geojson_coordinates)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        RETURNING id, name, variety, area_hectares, geojson_coordinates
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Convertir el dict de geojson a un string JSON válido para la base de datos
                geojson_str = json.dumps(parcel.geojson_coordinates)
                
                cur.execute(query, (
                    str(current_user.tenant_id),
                    parcel.name,
                    parcel.variety,
                    parcel.area_hectares,
                    geojson_str
                ))
                rec = cur.fetchone()
                conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    
    return schemas.Parcel(
        id=rec[0], name=rec[1], variety=rec[2], area_hectares=rec[3], geojson_coordinates=rec[4]
    )

@router.get("/", response_model=List[schemas.Parcel])
def get_all_parcels(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """
    Obtiene todas las parcelas de un usuario.
    """
    query = "SELECT id, name, variety, area_hectares, geojson_coordinates FROM parcels WHERE tenant_id = %s ORDER BY name"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                recs = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
        
    return [schemas.Parcel(id=r[0], name=r[1], variety=r[2], area_hectares=r[3], geojson_coordinates=r[4]) for r in recs]

@router.delete("/{parcel_id}", status_code=204)
def delete_parcel(
    parcel_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Elimina una parcela.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Opcional: Verificar si la parcela está en uso antes de borrar
                cur.execute("SELECT id FROM wine_lots WHERE origin_parcel_id = %s", (str(parcel_id),))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="No se puede eliminar una parcela que ya está asociada a un lote de vino.")
                
                cur.execute(
                    "DELETE FROM parcels WHERE id = %s AND tenant_id = %s",
                    (str(parcel_id), str(current_user.tenant_id))
                )
                conn.commit()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    return