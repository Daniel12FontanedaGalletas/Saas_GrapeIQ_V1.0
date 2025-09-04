from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ..database import get_db_connection
from ..services.security import role_checker
from .. import schemas

router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)

class ProductCreate(BaseModel):
    name: str
    sku: str
    price_per_unit: float
    product_type: str
    cost_per_unit: Optional[float] = None
    stock_quantity: Optional[int] = None

@router.get("/")
def get_products(
    user: schemas.User = Depends(role_checker(["admin", "lector"])),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sku_filter: Optional[str] = Query(None, alias="sku")
):
    # --- ¡CORRECCIÓN! Convertimos el UUID a string ---
    tenant_id = str(user.tenant_id)
    products = []
    
    base_query = """
        SELECT id, name, sku, product_type, price_per_unit, cost_per_unit, stock_quantity 
        FROM products 
        WHERE tenant_id = %s
    """
    params = [tenant_id]

    if sku_filter:
        base_query += " AND sku ILIKE %s"
        params.append(f"%{sku_filter}%")

    base_query += " ORDER BY name LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(base_query, tuple(params))
            for row in cur.fetchall():
                products.append({
                    "id": row[0], "name": row[1], "sku": row[2], "product_type": row[3],
                    "price_per_unit": row[4], "cost_per_unit": row[5], "stock_quantity": row[6]
                })
    return products

@router.post("/", status_code=201)
def create_product(product: ProductCreate, user: schemas.User = Depends(role_checker(["admin"]))):
    # --- ¡CORRECCIÓN! Convertimos el UUID a string ---
    tenant_id = str(user.tenant_id)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO products (tenant_id, name, sku, product_type, price_per_unit, cost_per_unit, stock_quantity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        tenant_id, product.name, product.sku, product.product_type,
                        product.price_per_unit, product.cost_per_unit, product.stock_quantity
                    )
                )
                new_product_id = cur.fetchone()[0]
                conn.commit()
                return {"id": new_product_id, **product.dict()}
            except Exception as e:
                conn.rollback()
                if "duplicate key value" in str(e).lower():
                    raise HTTPException(status_code=409, detail=f"El SKU '{product.sku}' ya existe.")
                raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")