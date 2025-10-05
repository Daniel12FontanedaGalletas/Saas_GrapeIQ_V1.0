# Saas_GrapeIQ_V1.0/app/routers/cellar_management.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
import psycopg2 
from psycopg2.extras import RealDictCursor
from datetime import datetime

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/cellar",
    tags=["Cellar Management"],
    dependencies=[Depends(security.get_current_active_user)]
)

# --- GESTIÓN DE CONTENEDORES (SIN CAMBIOS) ---
@router.get("/containers", response_model=List[schemas.Container])
def get_all_containers(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ Obtiene todos los contenedores de la bodega. """
    query = "SELECT * FROM containers WHERE tenant_id = %s ORDER BY type, name"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                containers = cur.fetchall()
                return containers
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")


@router.post("/containers", response_model=schemas.Container, status_code=201)
def create_container(container: schemas.ContainerCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ Añade un nuevo contenedor al inventario. """
    query = """
        INSERT INTO containers (id, name, type, capacity_liters, material, location, tenant_id, barrel_age, toast_level, cooperage) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                new_id = str(uuid.uuid4())
                cur.execute(query, (new_id, container.name, container.type, container.capacity_liters, container.material, container.location, str(current_user.tenant_id), container.barrel_age, container.toast_level, container.cooperage))
                new_container = cur.fetchone()
                conn.commit()
                return new_container
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
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
        SET name = %s, type = %s, capacity_liters = %s, material = %s, location = %s,
            barrel_age = %s, toast_level = %s, cooperage = %s
        WHERE id = %s AND tenant_id = %s
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (
                    container.name, container.type, container.capacity_liters, 
                    container.material, container.location, 
                    container.barrel_age, container.toast_level, container.cooperage,
                    str(container_id), str(current_user.tenant_id)
                ))
                updated_container = cur.fetchone()
                conn.commit()
                if not updated_container:
                    raise HTTPException(status_code=404, detail="Contenedor no encontrado.")
                return updated_container
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")

@router.delete("/containers/{container_id}", status_code=204)
def delete_container(
    container_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Elimina un contenedor del inventario. """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT status FROM containers WHERE id = %s AND tenant_id = %s",
                    (str(container_id), str(current_user.tenant_id))
                )
                rec = cur.fetchone()
                if not rec:
                    raise HTTPException(status_code=404, detail="Contenedor no encontrado.")
                if rec['status'] == 'ocupado':
                    raise HTTPException(status_code=400, detail="No se puede eliminar un contenedor que está actualmente en uso (ocupado).")

                cur.execute(
                    "DELETE FROM containers WHERE id = %s",
                    (str(container_id),)
                )
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        if isinstance(error, HTTPException):
            raise error
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")
    return

# --- NUEVOS ENDPOINTS PARA CONTROL DE VINIFICACIÓN ---

@router.post("/fermentation-controls/", response_model=schemas.FermentationControl, status_code=201)
def add_fermentation_control_entry(
    entry: schemas.FermentationControlCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Añade una nueva entrada de control de fermentación (temperatura/densidad)."""
    query = """
        INSERT INTO fermentation_controls (id, container_id, lot_id, control_date, temperature, density, notes, tenant_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                new_id = str(uuid.uuid4())
                cur.execute(query, (new_id, str(entry.container_id), str(entry.lot_id), entry.control_date, entry.temperature, entry.density, entry.notes, str(current_user.tenant_id)))
                new_entry = cur.fetchone()
                conn.commit()
                return new_entry
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el control: {e}")

@router.get("/fermentation-controls/{lot_id}/{container_id}", response_model=List[schemas.FermentationControl])
def get_fermentation_controls_for_container(
    lot_id: uuid.UUID,
    container_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """Obtiene el historial de controles de fermentación para un lote en un contenedor específico."""
    query = """
        SELECT * FROM fermentation_controls
        WHERE lot_id = %s AND container_id = %s AND tenant_id = %s
        ORDER BY control_date ASC
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(lot_id), str(container_id), str(current_user.tenant_id)))
                entries = cur.fetchall()
                return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener controles: {e}")

# --- MOVIMIENTOS DE VINO ---

@router.post("/movements/bulk-transfer", status_code=201)
def record_bulk_transfer(
    movement_request: schemas.BulkMovementCreate, 
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Registra un movimiento desde un contenedor de origen a MÚLTIPLES contenedores de destino. """
    total_volume_to_move = sum(dest.volume for dest in movement_request.destinations)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT current_volume FROM containers WHERE id = %s AND tenant_id = %s", (str(movement_request.source_container_id), str(current_user.tenant_id)))
                source_volume_rec = cur.fetchone()
                if not source_volume_rec or float(source_volume_rec['current_volume']) < total_volume_to_move:
                    raise HTTPException(status_code=400, detail="Volumen insuficiente en el contenedor de origen.")

                for dest in movement_request.destinations:
                    cur.execute(
                        "INSERT INTO movements (id, lot_id, source_container_id, destination_container_id, volume, type, tenant_id, movement_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (str(uuid.uuid4()), str(movement_request.lot_id), str(movement_request.source_container_id), str(dest.destination_container_id), dest.volume, movement_request.type, str(current_user.tenant_id), datetime.utcnow())
                    )
                    cur.execute(
                        "UPDATE containers SET current_volume = current_volume + %s, status = 'ocupado', current_lot_id = %s WHERE id = %s",
                        (dest.volume, str(movement_request.lot_id), str(dest.destination_container_id))
                    )

                cur.execute("UPDATE containers SET current_volume = current_volume - %s WHERE id = %s", (total_volume_to_move, str(movement_request.source_container_id)))
                cur.execute("UPDATE containers SET status = 'vacío', current_lot_id = NULL WHERE id = %s AND current_volume <= 0.01", (str(movement_request.source_container_id),))
                cur.execute("UPDATE wine_lots SET status = 'En Crianza' WHERE id = %s", (str(movement_request.lot_id),))
                conn.commit()

    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")

    return {"message": f"Trasiego de {total_volume_to_move}L a {len(movement_request.destinations)} contenedores registrado con éxito."}

@router.post("/movements", status_code=201)
def record_movement(movement: schemas.MovementCreate, current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """ Registra un movimiento de vino (llenado inicial), actualizando los contenedores y lotes de forma segura. """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO movements (id, lot_id, source_container_id, destination_container_id, volume, type, tenant_id, notes, movement_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        str(uuid.uuid4()),
                        str(movement.lot_id), 
                        str(movement.source_container_id) if movement.source_container_id else None, 
                        str(movement.destination_container_id) if movement.destination_container_id else None, 
                        movement.volume, 
                        movement.type, 
                        str(current_user.tenant_id),
                        movement.notes,
                        datetime.utcnow()
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
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")
            
    return {"message": "Movimiento registrado con éxito"}

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
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                total_bottled_volume = 0
                for source_id in bottling_request.source_container_ids:
                    cur.execute("SELECT current_volume FROM containers WHERE id = %s", (str(source_id),))
                    volume_rec = cur.fetchone()
                    if not volume_rec: continue
                    
                    volume_to_bottle = float(volume_rec['current_volume'])
                    total_bottled_volume += volume_to_bottle
                    
                    cur.execute(
                        "INSERT INTO movements (id, lot_id, source_container_id, volume, type, tenant_id, movement_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (str(uuid.uuid4()), str(bottling_request.lot_id), str(source_id), volume_to_bottle, 'Embotellado', str(current_user.tenant_id), datetime.utcnow())
                    )
                    cur.execute("UPDATE containers SET current_volume = 0, status = 'vacío', current_lot_id = NULL WHERE id = %s", (str(source_id),))
                
                cur.execute("SELECT SUM(current_volume) as total FROM containers WHERE current_lot_id = %s AND tenant_id = %s", (str(bottling_request.lot_id), str(current_user.tenant_id)))
                remaining_volume_rec = cur.fetchone()
                remaining_volume = (remaining_volume_rec['total'] or 0) if remaining_volume_rec else 0

                if remaining_volume < 0.01:
                    cur.execute("UPDATE wine_lots SET status = 'Embotellado' WHERE id = %s", (str(bottling_request.lot_id),))
                
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")
    return {"message": f"Embotellado simple de {total_bottled_volume}L registrado."}
    
# =================================================================
# INICIO DE LA CORRECCIÓN
# =================================================================
@router.post("/movements/bottling-and-create-product", status_code=201)
def bottling_and_create_product(
    request: schemas.BottlingToProductCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Registra un embotellado, calcula el coste y crea el producto. """
    if not request.source_container_ids:
        raise HTTPException(status_code=400, detail="Se debe especificar al menos un contenedor de origen.")
    if request.bottles_produced <= 0:
        raise HTTPException(status_code=400, detail="El número de botellas producidas debe ser mayor que cero.")

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT origin_parcel_id FROM wine_lots WHERE id = %s", (str(request.lot_id),))
                origin_parcel_record = cur.fetchone()
                
                total_cost_parcel = 0
                if origin_parcel_record and origin_parcel_record['origin_parcel_id']:
                    origin_parcel_id = str(origin_parcel_record['origin_parcel_id'])
                    cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM costs WHERE related_parcel_id = %s", (origin_parcel_id,))
                    total_cost_parcel = cur.fetchone()['total']

                cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM costs WHERE related_lot_id = %s", (str(request.lot_id),))
                total_cost_lot = cur.fetchone()['total']
                
                total_production_cost = float(total_cost_lot) + float(total_cost_parcel)
                unit_cost = total_production_cost / request.bottles_produced if request.bottles_produced > 0 else 0

                total_bottled_volume = 0
                for source_id in request.source_container_ids:
                    cur.execute("SELECT current_volume FROM containers WHERE id = %s AND tenant_id = %s", (str(source_id), str(current_user.tenant_id)))
                    volume_rec = cur.fetchone()
                    if not volume_rec:
                        raise HTTPException(status_code=404, detail=f"Contenedor de origen {source_id} no encontrado.")
                    
                    volume_to_bottle = float(volume_rec['current_volume'])
                    total_bottled_volume += volume_to_bottle
                    
                    cur.execute(
                        "INSERT INTO movements (id, lot_id, source_container_id, volume, type, tenant_id, movement_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (str(uuid.uuid4()), str(request.lot_id), str(source_id), volume_to_bottle, 'Embotellado y Creación de Producto', str(current_user.tenant_id), datetime.utcnow())
                    )
                    
                    cur.execute("UPDATE containers SET current_volume = 0, status = 'vacío', current_lot_id = NULL WHERE id = %s", (str(source_id),))
                
                cur.execute("SELECT SUM(current_volume) as total FROM containers WHERE current_lot_id = %s AND tenant_id = %s", (str(request.lot_id), str(current_user.tenant_id)))
                remaining_volume_rec = cur.fetchone()
                remaining_volume = float(remaining_volume_rec['total'] or 0) if remaining_volume_rec else 0

                if remaining_volume < 0.01:
                    cur.execute("UPDATE wine_lots SET status = 'Embotellado' WHERE id = %s", (str(request.lot_id),))

                new_product_id = uuid.uuid4()
                cur.execute(
                    """
                    INSERT INTO products (id, tenant_id, name, sku, price, unit_cost, wine_lot_origin_id, stock_units)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (str(new_product_id), str(current_user.tenant_id), request.product_name, request.product_sku, request.product_price, unit_cost, str(request.lot_id), request.bottles_produced)
                )
                conn.commit()

    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        if isinstance(error, HTTPException):
            raise error
        if "duplicate key" in str(error).lower():
            raise HTTPException(status_code=409, detail=f"El SKU '{request.product_sku}' ya existe.")
        raise HTTPException(status_code=500, detail=f"Error en la transacción de base de datos: {error}")

    return {
        "message": f"Embotellado completado. Producto '{request.product_name}' creado con {request.bottles_produced} unidades.",
        "calculated_unit_cost": f"{unit_cost:.4f}",
        "new_product_id": str(new_product_id)
    }
# =================================================================
# FIN DE LA CORRECCIÓN
# =================================================================

@router.post("/movements/top-up", status_code=201)
def record_topping_up(
    top_up: schemas.ToppingUpCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """ Añade más vino a un contenedor ya ocupado por el mismo lote. """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT capacity_liters, current_volume FROM containers WHERE id = %s AND current_lot_id = %s", (str(top_up.destination_container_id), str(top_up.lot_id)))
                container_data = cur.fetchone()
                if not container_data:
                    raise HTTPException(status_code=404, detail="El contenedor no existe o no contiene el lote especificado.")
                
                capacity = float(container_data['capacity_liters'])
                current_volume = float(container_data['current_volume'])
                if (current_volume + top_up.volume) > capacity:
                    raise HTTPException(status_code=400, detail="El volumen a añadir supera la capacidad del contenedor.")

                cur.execute("SELECT liters_unassigned FROM wine_lots WHERE id = %s", (str(top_up.lot_id),))
                unassigned_liters_rec = cur.fetchone()
                if not unassigned_liters_rec:
                    raise HTTPException(status_code=404, detail="Lote no encontrado.")
                
                unassigned_liters = float(unassigned_liters_rec['liters_unassigned'])
                if top_up.volume > unassigned_liters:
                    raise HTTPException(status_code=400, detail="El volumen a añadir supera los litros no asignados del lote.")

                cur.execute("INSERT INTO movements (id, lot_id, destination_container_id, volume, type, tenant_id) VALUES (%s, %s, %s, %s, %s, %s)",
                    (str(uuid.uuid4()), str(top_up.lot_id), str(top_up.destination_container_id), top_up.volume, top_up.type, str(current_user.tenant_id)))

                cur.execute("UPDATE containers SET current_volume = current_volume + %s WHERE id = %s", (top_up.volume, str(top_up.destination_container_id)))
                cur.execute("UPDATE wine_lots SET liters_unassigned = liters_unassigned - %s WHERE id = %s", (top_up.volume, str(top_up.lot_id)))
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        if isinstance(error, HTTPException): raise error
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {error}")

    return {"message": "Contenedor rellenado con éxito."}