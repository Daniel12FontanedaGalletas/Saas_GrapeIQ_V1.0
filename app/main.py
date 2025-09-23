from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# IMPORTA LAS FUNCIONES DE DATABASE Y LOS ROUTERS
from .database import connect_to_db, close_db_connection
# Se añade el nuevo router 'products'
from .routers import auth, ingest, data, forecast, weather, products, users, field_log

app = FastAPI(
    title="GrapeIQ API",
    description="API para el análisis de ventas y predicción de demanda.",
    version="1.0.0"
)
# AÑADE LOS EVENTOS DE STARTUP Y SHUTDOWN
@app.on_event("startup")
def startup_event():
    connect_to_db()

@app.on_event("shutdown")
def shutdown_event():
    close_db_connection()


# --- Configuración de CORS ---
# Esta es la lista corregida
origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://127.0.0.1:5500", 
    "null"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Bienvenido a la API de GrapeIQ"}

# --- Inclusión de Routers ---
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(data.router)
app.include_router(forecast.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(field_log.router)