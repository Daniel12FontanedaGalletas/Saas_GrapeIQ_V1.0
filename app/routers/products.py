# Saas_GrapeIQ_V1.0/app/routers/products.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import uuid
from psycopg2.extras import RealDictCursor

from .. import schemas
from ..services.security import get_current_user, role_checker, get_current_active_user
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)

@router.get("/", response_model=List[schemas.Product])
def get_products(
    user: schemas.UserInDB = Depends(get_current_active_user),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sku_filter: Optional[str] = Query(None, alias="sku")
):
    """
    Recupera una lista de todos los productos del tenant actual.
    Este endpoint es usado por el frontend de pronóstico para poblar el selector.
    """
    tenant_id = str(user.tenant_id)
    products = []
    
    base_query = """
        SELECT id, name, sku, description, price, unit_cost, wine_lot_origin_id, stock_units, variety 
        FROM products 
        WHERE tenant_id = %s
    """
    params = [tenant_id]

    if sku_filter:
        base_query += " AND sku ILIKE %s"
        params.append(f"%{sku_filter}%")

    base_query += " ORDER BY name LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(base_query, tuple(params))
                results = cur.fetchall()
                for row in results:
                    # Usar model_validate para una conversión segura
                    products.append(schemas.Product.model_validate(row))
            return products
    except Exception as e:
        print(f"Error detallado al obtener productos: {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar los productos.")


@router.post("/", status_code=201, response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, user: schemas.UserInDB = Depends(role_checker(["admin"]))):
    tenant_id = str(user.tenant_id)
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO products (tenant_id, name, sku, variety, price, unit_cost, stock_units, description, wine_lot_origin_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (
                        tenant_id, product.name, product.sku, product.variety,
                        product.price, product.unit_cost, product.stock_units, product.description,
                        product.wine_lot_origin_id
                    )
                )
                new_product_record = cur.fetchone()
                conn.commit()
                return schemas.Product.model_validate(new_product_record)
            except Exception as e:
                conn.rollback()
                if "duplicate key value" in str(e).lower():
                    raise HTTPException(status_code=409, detail=f"El SKU '{product.sku}' ya existe.")
                raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: uuid.UUID, current_user: schemas.UserInDB = Depends(get_current_active_user)):
    """
    Elimina un producto del catálogo y, si está asociado a un lote de vino,
    elimina también el lote de vino correspondiente para mantener la consistencia.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Buscar el producto para obtener el ID del lote de vino de origen
                cur.execute(
                    "SELECT wine_lot_origin_id FROM products WHERE id = %s AND tenant_id = %s",
                    (str(product_id), str(current_user.tenant_id))
                )
                product = cur.fetchone()

                if not product:
                    # Si no se encuentra, la operación se considera exitosa (idempotente)
                    return

                wine_lot_id = product.get('wine_lot_origin_id')

                # 2. Eliminar el producto
                cur.execute("DELETE FROM products WHERE id = %s", (str(product_id),))

                # 3. Si hay un lote de vino asociado, eliminarlo también
                if wine_lot_id:
                    cur.execute("DELETE FROM wine_lots WHERE id = %s AND tenant_id = %s", (str(wine_lot_id), str(current_user.tenant_id)))
                
                conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos al eliminar el producto: {e}")

@router.get("/list", response_model=List[schemas.ProductSimple])
def get_products_list_simple(
    user: schemas.UserInDB = Depends(get_current_active_user)
):
    """
    Devuelve una lista simple de todos los productos (ID y nombre) para desplegables.
    """
    tenant_id = str(user.tenant_id)
    query = "SELECT id, name FROM products WHERE tenant_id = %s ORDER BY name"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (tenant_id,))
                products = cur.fetchall()
                return products
    except Exception as e:
        print(f"Error en /api/products/list: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")