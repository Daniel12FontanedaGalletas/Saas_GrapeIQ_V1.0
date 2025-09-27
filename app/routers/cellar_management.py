# Saas_GrapeIQ_V1.0/app/routers/cellar_management.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
import psycopg2 

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/cellar",
    tags=["Cellar Management"],
)

@router.get("/containers", response_model=List[schemas.Container])
def get_all_containers(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ Obtiene todos los contenedores de la bodega. """
    query = """
        SELECT id, name, type, capacity_liters, material, location, status, current_volume, current_lot_id 
        FROM containers 
        WHERE tenant_id = %s 
        ORDER BY type, name
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                recs = cur.fetchall()
        return [
            schemas.Container(
                id=r[0], name=r[1], type=r[2], capacity_liters=r[3], 
                material=r[4], location=r[5], status=r[6], 
                current_volume=r[7], current_lot_id=r[8]
            ) for r in recs
        ]
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")


@router.post("/containers", response_model=schemas.Container, status_code=201)
def create_container(container: schemas.ContainerCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ Añade un nuevo contenedor al inventario. """
    query = """
        INSERT INTO containers (name, type, capacity_liters, material, location, tenant_id) 
        VALUES (%s, %s, %s, %s, %s, %s) 
        RETURNING id, name, type, capacity_liters, material, location, status, current_volume, current_lot_id
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (container.name, container.type, container.capacity_liters, container.material, container.location, str(current_user.tenant_id)))
                rec = cur.fetchone()
                conn.commit()
        return schemas.Container(
            id=rec[0], name=rec[1], type=rec[2], capacity_liters=rec[3], 
            material=rec[4], location=rec[5], status=rec[6], 
            current_volume=rec[7], current_lot_id=rec[8]
        )
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")

@router.put("/containers/{container_id}", response_model=schemas.Container)
def update_container(
    container_id: uuid.UUID, 
    container: schemas.ContainerUpdate, 
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Actualiza la información de un contenedor existente. """
    query = """
        UPDATE containers
        SET name = %s, type = %s, capacity_liters = %s, material = %s, location = %s
        WHERE id = %s AND tenant_id = %s
        RETURNING id, name, type, capacity_liters, material, location, status, current_volume, current_lot_id
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    container.name, container.type, container.capacity_liters, 
                    container.material, container.location, 
                    str(container_id), str(current_user.tenant_id)
                ))
                rec = cur.fetchone()
                conn.commit()
        if not rec:
            raise HTTPException(status_code=404, detail="Contenedor no encontrado.")
        return schemas.Container(
            id=rec[0], name=rec[1], type=rec[2], capacity_liters=rec[3], 
            material=rec[4], location=rec[5], status=rec[6], 
            current_volume=rec[7], current_lot_id=rec[8]
        )
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")

@router.delete("/containers/{container_id}", status_code=204)
def delete_container(
    container_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Elimina un contenedor del inventario. """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM containers WHERE id = %s AND tenant_id = %s",
                    (str(container_id), str(current_user.tenant_id))
                )
                rec = cur.fetchone()
                if not rec:
                    raise HTTPException(status_code=404, detail="Contenedor no encontrado.")
                if rec[0] == 'ocupado':
                    raise HTTPException(status_code=400, detail="No se puede eliminar un contenedor que está actualmente en uso (ocupado).")

                cur.execute(
                    "DELETE FROM containers WHERE id = %s",
                    (str(container_id),)
                )
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        if isinstance(error, HTTPException):
            raise error
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")
    return

@router.post("/movements/bottling", status_code=201)
def record_bottling(
    bottling_request: schemas.BottlingCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ (Versión Antigua) Registra el embotellado. """
    if not bottling_request.source_container_ids:
        raise HTTPException(status_code=400, detail="Se debe especificar al menos un contenedor de origen.")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                total_bottled_volume = 0
                for source_id in bottling_request.source_container_ids:
                    cur.execute("SELECT current_volume FROM containers WHERE id = %s", (str(source_id),))
                    volume_to_bottle_tuple = cur.fetchone()
                    if not volume_to_bottle_tuple: continue
                    volume_to_bottle = volume_to_bottle_tuple[0]
                    total_bottled_volume += volume_to_bottle
                    
                    cur.execute("INSERT INTO movements (lot_id, source_container_id, volume, type, tenant_id) VALUES (%s, %s, %s, %s, %s)",
                                (str(bottling_request.lot_id), str(source_id), volume_to_bottle, 'Embotellado', str(current_user.tenant_id)))
                    cur.execute("UPDATE containers SET current_volume = 0, status = 'vacío', current_lot_id = NULL WHERE id = %s", (str(source_id),))
                
                cur.execute("SELECT SUM(current_volume) FROM containers WHERE current_lot_id = %s AND tenant_id = %s", (str(bottling_request.lot_id), str(current_user.tenant_id)))
                remaining_volume = (cur.fetchone() or [0])[0] or 0

                if remaining_volume < 0.01:
                    cur.execute("UPDATE wine_lots SET status = 'Embotellado' WHERE id = %s", (str(bottling_request.lot_id),))
                
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")
    return {"message": f"Embotellado simple de {total_bottled_volume}L registrado."}

@router.post("/movements/bottling-and-create-product", status_code=201)
def bottling_and_create_product(
    request: schemas.BottlingToProductCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Registra un embotellado Y crea un nuevo producto en el catálogo en una única transacción.
    """
    if not request.source_container_ids:
        raise HTTPException(status_code=400, detail="Se debe especificar al menos un contenedor de origen.")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                total_bottled_volume = 0
                for source_id in request.source_container_ids:
                    cur.execute("SELECT current_volume FROM containers WHERE id = %s AND tenant_id = %s", (str(source_id), str(current_user.tenant_id)))
                    volume_tuple = cur.fetchone()
                    if not volume_tuple:
                        raise HTTPException(status_code=404, detail=f"Contenedor de origen {source_id} no encontrado.")
                    
                    volume_to_bottle = volume_tuple[0]
                    total_bottled_volume += volume_to_bottle
                    
                    cur.execute("INSERT INTO movements (lot_id, source_container_id, volume, type, tenant_id) VALUES (%s, %s, %s, %s, %s)",
                                (str(request.lot_id), str(source_id), volume_to_bottle, 'Embotellado y Creación de Producto', str(current_user.tenant_id)))
                    
                    cur.execute("UPDATE containers SET current_volume = 0, status = 'vacío', current_lot_id = NULL WHERE id = %s", (str(source_id),))
                
                cur.execute("SELECT SUM(current_volume) FROM containers WHERE current_lot_id = %s AND tenant_id = %s", (str(request.lot_id), str(current_user.tenant_id)))
                remaining_volume = (cur.fetchone() or [0])[0] or 0

                if remaining_volume < 0.01:
                    cur.execute("UPDATE wine_lots SET status = 'Embotellado' WHERE id = %s", (str(request.lot_id),))

                # --- Lógica de Creación de Producto (MODIFICADA) ---
                new_product_id = uuid.uuid4()
                cur.execute(
                    """
                    INSERT INTO products (id, tenant_id, name, sku, price, wine_lot_origin_id, stock_units)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(new_product_id),
                        str(current_user.tenant_id),
                        request.product_name,
                        request.product_sku,
                        request.product_price,
                        str(request.lot_id),
                        request.bottles_produced
                    )
                )
                conn.commit()

    except (Exception, psycopg2.Error) as error:
        if "duplicate key" in str(error).lower():
            raise HTTPException(status_code=409, detail=f"El SKU '{request.product_sku}' ya existe.")
        raise HTTPException(status_code=500, detail=f"Error en la transacción de base de datos: {error}")

    return {"message": f"Embotellado de {total_bottled_volume}L completado. Producto '{request.product_name}' creado con {request.bottles_produced} unidades."}

@router.post("/movements/bulk-transfer", status_code=201)
def record_bulk_transfer(
    movement_request: schemas.BulkMovementCreate, 
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Registra un movimiento desde un contenedor de origen a MÚLTIPLES contenedores de destino.
    """
    total_volume_to_move = sum(dest.volume for dest in movement_request.destinations)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_volume FROM containers WHERE id = %s AND tenant_id = %s", (str(movement_request.source_container_id), str(current_user.tenant_id)))
                source_volume = cur.fetchone()
                if not source_volume or source_volume[0] < total_volume_to_move:
                    raise HTTPException(status_code=400, detail="Volumen insuficiente en el contenedor de origen.")

                for dest in movement_request.destinations:
                    cur.execute(
                        "INSERT INTO movements (lot_id, source_container_id, destination_container_id, volume, type, tenant_id) VALUES (%s, %s, %s, %s, %s, %s)",
                        (str(movement_request.lot_id), str(movement_request.source_container_id), str(dest.destination_container_id), dest.volume, movement_request.type, str(current_user.tenant_id))
                    )
                    cur.execute(
                        "UPDATE containers SET current_volume = %s, status = 'ocupado', current_lot_id = %s WHERE id = %s",
                        (dest.volume, str(movement_request.lot_id), str(dest.destination_container_id))
                    )

                cur.execute("UPDATE containers SET current_volume = current_volume - %s WHERE id = %s", (total_volume_to_move, str(movement_request.source_container_id)))
                cur.execute("UPDATE containers SET status = 'vacío', current_lot_id = NULL WHERE id = %s AND current_volume <= 0.01", (str(movement_request.source_container_id),))
                cur.execute("UPDATE wine_lots SET status = 'En Crianza' WHERE id = %s", (str(movement_request.lot_id),))
                conn.commit()

    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")

    return {"message": f"Trasiego de {total_volume_to_move}L a {len(movement_request.destinations)} contenedores registrado con éxito."}

@router.post("/movements", status_code=201)
def record_movement(movement: schemas.MovementCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ Registra un movimiento de vino (llenado inicial), actualizando los contenedores y lotes de forma segura. """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO movements (lot_id, source_container_id, destination_container_id, volume, type, tenant_id) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        str(movement.lot_id), 
                        str(movement.source_container_id) if movement.source_container_id else None, 
                        str(movement.destination_container_id) if movement.destination_container_id else None, 
                        movement.volume, 
                        movement.type, 
                        str(current_user.tenant_id)
                    )
                )

                if movement.source_container_id:
                    cur.execute("UPDATE containers SET current_volume = current_volume - %s WHERE id = %s", (movement.volume, str(movement.source_container_id)))
                    cur.execute("UPDATE containers SET status = 'vacío', current_lot_id = NULL WHERE id = %s AND current_volume <= 0.01", (str(movement.source_container_id),))
                
                if movement.destination_container_id:
                    cur.execute("UPDATE containers SET current_volume = current_volume + %s, status = 'ocupado', current_lot_id = %s WHERE id = %s", (movement.volume, str(movement.lot_id), str(movement.destination_container_id)))
                
                if movement.type == 'Llenado Inicial':
                    cur.execute("UPDATE wine_lots SET status = 'En Fermentación' WHERE id = %s", (str(movement.lot_id),))

                cur.execute("UPDATE wine_lots SET liters_unassigned = liters_unassigned - %s WHERE id = %s", (movement.volume, str(movement.lot_id)))
                conn.commit()
                
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")
            
    return {"message": "Movimiento registrado con éxito"}

@router.post("/movements/top-up", status_code=201)
def record_topping_up(
    top_up: schemas.ToppingUpCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Añade más vino a un contenedor ya ocupado por el mismo lote.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT capacity_liters, current_volume FROM containers WHERE id = %s AND current_lot_id = %s", (str(top_up.destination_container_id), str(top_up.lot_id)))
                container_data = cur.fetchone()
                if not container_data:
                    raise HTTPException(status_code=404, detail="El contenedor no existe o no contiene el lote especificado.")
                
                capacity, current_volume = container_data
                if (current_volume + top_up.volume) > capacity:
                    raise HTTPException(status_code=400, detail="El volumen a añadir supera la capacidad del contenedor.")

                cur.execute("SELECT liters_unassigned FROM wine_lots WHERE id = %s", (str(top_up.lot_id),))
                unassigned_liters = cur.fetchone()[0]
                if top_up.volume > unassigned_liters:
                    raise HTTPException(status_code=400, detail="El volumen a añadir supera los litros no asignados del lote.")

                cur.execute("INSERT INTO movements (lot_id, destination_container_id, volume, type, tenant_id) VALUES (%s, %s, %s, %s, %s)",
                    (str(top_up.lot_id), str(top_up.destination_container_id), top_up.volume, top_up.type, str(current_user.tenant_id)))

                cur.execute("UPDATE containers SET current_volume = current_volume + %s WHERE id = %s", (top_up.volume, str(top_up.destination_container_id)))
                cur.execute("UPDATE wine_lots SET liters_unassigned = liters_unassigned - %s WHERE id = %s", (top_up.volume, str(top_up.lot_id)))
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        if isinstance(error, HTTPException): raise error
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")

    return {"message": "Contenedor rellenado con éxito."}