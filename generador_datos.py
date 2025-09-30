# Saas_GrapeIQ_V1.0/generador_datos.py (Versión Definitiva, Integral y Robusta)

import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from faker import Faker
import random
import uuid
import json
from datetime import date, timedelta
from passlib.context import CryptContext

# --- 1. CONFIGURACIÓN INICIAL ---
print("🚀 Iniciando el generador de datos DEFINITIVO para GrapeIQ...")
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- 2. VALIDACIÓN DE CONEXIÓN ---
if not DATABASE_URL:
    print("❌ ERROR: La variable de entorno DATABASE_URL no está definida.")
    exit()
try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    print("✅ Conexión a la base de datos establecida.")
except Exception as e:
    print(f"❌ ERROR: No se pudo conectar a la base de datos: {e}")
    exit()

# --- 3. PARÁMETROS DE LA SIMULACIÓN ---
SIM_YEARS = 4
NUM_FIELD_LOGS_PER_YEAR = 50
NUM_CONTAINERS = 40  # 10 depósitos, 30 barricas

# --- 4. DATOS BASE ---
fake = Faker('es_ES')
parcels_base = [
    {'name': 'Viña del Monte', 'area': 5.2, 'variety': 'Mencía'},
    {'name': 'El Rincón Soleado', 'area': 3.1, 'variety': 'Tempranillo'},
    {'name': 'La Cuesta Alta', 'area': 7.8, 'variety': 'Mencía'},
    {'name': 'Valle Escondido', 'area': 4.5, 'variety': 'Prieto Picudo'},
    {'name': 'Finca Albariza', 'area': 6.2, 'variety': 'Albarín'},
    {'name': 'Campo de Viento', 'area': 8.1, 'variety': 'Verdejo'}
]
products_base = [
    {'name': 'Alma de Golia', 'variety': 'Mencía', 'base_price': 15.99},
    {'name': 'El Pájaro Rojo', 'variety': 'Mencía', 'base_price': 9.95},
    {'name': 'Señorío de Nava', 'variety': 'Tempranillo', 'base_price': 8.75},
    {'name': 'Cuatro Pasos', 'variety': 'Prieto Picudo', 'base_price': 7.50},
    {'name': 'Pardevalles', 'variety': 'Albarín', 'base_price': 12.95},
    {'name': 'Verdeal', 'variety': 'Verdejo', 'base_price': 7.90}
]
container_definitions = {
    'Depósito': ['Inox', 'Hormigón'],
    'Barrica': ['Roble Francés', 'Roble Americano']
}
field_activities = ['Poda', 'Tratamiento Fitosanitario', 'Riego', 'Abonado', 'Vendimia']

cost_types = {
    'Viñedo y Vendimia': [('Mano de Obra Campo', 'Salarios', '€/año'), ('Fitosanitarios', 'Tratamientos', '€/ha'), ('Fertilizantes', 'Abonado', '€/ha'), ('Combustible', 'Maquinaria', '€/año')],
    'Vinificación': [('Levaduras', 'Fermentación', '€/L'), ('Laboratorio', 'Análisis', '€/L'), ('Energía', 'Electricidad', '€/año')],
    'Crianza y Almacenamiento': [('Mantenimiento Barricas', 'Limpieza', '€/barrica'), ('Amortización Barricas', 'Coste anual', '€/año')],
    'Embotellado y Empaquetado': [('Botellas', 'Compra', '€/ud'), ('Corchos', 'Suministro', '€/ud'), ('Etiquetas', 'Diseño', '€/ud')],
    'Comerciales y de Marketing': [('Publicidad', 'Campañas', '€/año'), ('Eventos', 'Ferias', '€/año'), ('Comisiones', 'Ventas', '%')],
    'Generales y Administrativos': [('Salarios Oficina', 'Administración', '€/año'), ('Alquiler', 'Oficinas', '€/año'), ('Gestoría', 'Asesoría', '€/año')]
}

def create_random_geojson(lat, lon, scale=0.01):
    points = []
    for _ in range(random.randint(4, 6)):
        points.append([lon + (random.random() - 0.5) * scale, lat + (random.random() - 0.5) * scale])
    points.append(points[0])
    return json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [points]}}]})

# --- 5. EJECUCIÓN DEL SCRIPT ---
try:
    print("\n⚠️  Limpiando la base de datos...")
    tables_to_delete = ["sale_details", "sales", "movements", "products", "cost_parameters", "costs", "containers", "wine_lots", "field_logs", "parcels", "users", "tenants"]
    for table in tables_to_delete:
        cur.execute(f"DELETE FROM {table};")
    print("   ...tablas limpiadas.")

    print("\n🌱 Creando activos y estructura base...")
    tenant_id = str(uuid.uuid4())
    cur.execute("INSERT INTO tenants (id, name) VALUES (%s, %s);", (tenant_id, 'Bodega de Demostración'))
    admin_user, admin_pass = 'admin', 'admin123'
    cur.execute("INSERT INTO users (id, tenant_id, username, hashed_password, role) VALUES (%s, %s, %s, %s, %s);",
                (str(uuid.uuid4()), tenant_id, admin_user, pwd_context.hash(admin_pass), 'admin'))

    parcels_data = [(str(uuid.uuid4()), tenant_id, p['name'], p['variety'], p['area'], create_random_geojson(42.55 + i * 0.015, -6.59 + i * 0.015)) for i, p in enumerate(parcels_base)]
    execute_values(cur, "INSERT INTO parcels (id, tenant_id, name, variety, area_hectares, geojson_coordinates) VALUES %s", parcels_data)
    
    containers_data = [(str(uuid.uuid4()), f"{random.choice(defs)}-{i+1}", main_type, 225 if main_type == 'Barrica' else random.choice([5000, 10000]), random.choice(defs), tenant_id) for i in range(NUM_CONTAINERS) for main_type, defs in [('Depósito' if i < 10 else 'Barrica', container_definitions['Depósito' if i < 10 else 'Barrica'])]]
    execute_values(cur, "INSERT INTO containers (id, name, type, capacity_liters, material, tenant_id) VALUES %s", containers_data)
    
    # --- CORRECCIÓN: Crear un Cost Parameter por cada tipo de coste ---
    cost_parameters_data = []
    for category, costs_in_category in cost_types.items():
        for name, _, unit in costs_in_category:
            cost_parameters_data.append((str(uuid.uuid4()), tenant_id, name, random.uniform(10, 100), unit, category))
    execute_values(cur, "INSERT INTO cost_parameters (id, tenant_id, parameter_name, value, unit, category) VALUES %s", cost_parameters_data)

    print("\n🔄 Simulando cosechas, costes y ciclo de vida por etapas...")
    start_year = date.today().year - SIM_YEARS + 1
    cur.execute("SELECT id, name, variety, area_hectares FROM parcels WHERE tenant_id = %s;", (tenant_id,))
    db_parcels = cur.fetchall()
    all_wine_lots_data = []
    all_costs = []
    all_field_logs = []

    for year in range(start_year, date.today().year + 1):
        print(f"   - Generando datos de cosecha, costes y logs para el año {year}...")
        for parcel_id, parcel_name, variety, area in db_parcels:
            for _ in range(NUM_FIELD_LOGS_PER_YEAR // len(db_parcels)):
                log_date = date(year, random.randint(1, 12), random.randint(1, 28))
                all_field_logs.append((str(uuid.uuid4()), log_date, log_date, random.choice(field_activities), fake.sentence(), tenant_id, parcel_id))
            
            for cost_type, desc, _ in cost_types['Viñedo y Vendimia']:
                amount = float(area) * random.uniform(200, 600)
                all_costs.append((str(uuid.uuid4()), tenant_id, None, cost_type, round(amount, 2), desc, date(year, random.randint(1, 12), 15), parcel_id))
            
            prod_base = next((p for p in products_base if p['variety'] == variety), None)
            if prod_base:
                initial_kg = float(area) * random.uniform(800, 1200)
                total_liters = initial_kg / 1.6
                lot_id = str(uuid.uuid4())
                all_wine_lots_data.append([lot_id, f"{variety} {year} ({parcel_name})", variety, year, 'Cosechado', tenant_id, parcel_id, initial_kg, total_liters, total_liters])
                for cost_type, desc, _ in cost_types['Vinificación']:
                    amount = total_liters * random.uniform(0.10, 0.25)
                    all_costs.append((str(uuid.uuid4()), tenant_id, lot_id, cost_type, round(amount, 2), desc, date(year, 10, 5), None))

    execute_values(cur, "INSERT INTO field_logs (id, start_datetime, end_datetime, activity_type, description, tenant_id, parcel_id) VALUES %s", all_field_logs)
    execute_values(cur, "INSERT INTO wine_lots (id, name, grape_variety, vintage_year, status, tenant_id, origin_parcel_id, initial_grape_kg, total_liters, liters_unassigned) VALUES %s", all_wine_lots_data)

    cur.execute("SELECT id, capacity_liters FROM containers WHERE tenant_id = %s AND type = 'Depósito'", (tenant_id,))
    available_deposits = [list(d) for d in cur.fetchall()]
    cur.execute("SELECT id FROM containers WHERE tenant_id = %s AND type = 'Barrica'", (tenant_id,))
    available_barrels = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id, total_liters, vintage_year FROM wine_lots WHERE tenant_id = %s AND status = 'Cosechado'", (tenant_id,))
    lots_to_process = sorted(cur.fetchall(), key=lambda x: x[2])

    lots_by_age = {i: [] for i in range(SIM_YEARS)}
    for lot in lots_to_process:
        age = date.today().year - lot[2]
        if age in lots_by_age:
            lots_by_age[age].append(lot)
    
    for age in sorted(lots_by_age.keys(), reverse=True):
        lots_in_age = sorted(lots_by_age[age], key=lambda x: x[1])
        
        if age >= 2:
            for i, (lot_id, total_liters, vintage) in enumerate(lots_in_age):
                status = 'Embotellado' if i % 2 == 0 else 'Listo para Embotellar'
                cur.execute("UPDATE wine_lots SET status = %s WHERE id = %s", (status, lot_id))
                if status == 'Embotellado':
                    num_bottles = int(float(total_liters) / 0.75)
                    for cost_type, desc, _ in cost_types['Embotellado y Empaquetado']:
                        amount = num_bottles * random.uniform(0.2, 0.5)
                        all_costs.append((str(uuid.uuid4()), tenant_id, lot_id, cost_type, round(amount, 2), desc, date(vintage + 2, 3, 1), None))
        elif age == 1:
            lots_for_aging = lots_in_age[:len(lots_in_age)//2]
            lots_for_ready = lots_in_age[len(lots_in_age)//2:]
            for lot_id, total_liters, vintage in lots_for_aging:
                liters = float(total_liters)
                num_barrels_needed = int(liters / 225) + (1 if liters % 225 > 0 else 0)
                if len(available_barrels) >= num_barrels_needed:
                    cur.execute("UPDATE wine_lots SET status = 'En Crianza' WHERE id = %s", (lot_id,))
                    barrels_for_lot = [available_barrels.pop(0) for _ in range(num_barrels_needed)]
                    for barrel_id in barrels_for_lot:
                        cur.execute("UPDATE containers SET status = 'ocupado', current_volume = 225, current_lot_id = %s WHERE id = %s", (lot_id, barrel_id))
                    for cost_type, desc, _ in cost_types['Crianza y Almacenamiento']:
                        amount = num_barrels_needed * random.uniform(20, 50)
                        all_costs.append((str(uuid.uuid4()), tenant_id, lot_id, cost_type, round(amount, 2), desc, date(vintage + 1, 6, 1), None))
                else:
                    cur.execute("UPDATE wine_lots SET status = 'Listo para Embotellar' WHERE id = %s", (lot_id,))
            for lot_id, _, _ in lots_for_ready:
                cur.execute("UPDATE wine_lots SET status = 'Listo para Embotellar' WHERE id = %s", (lot_id,))
        elif age == 0:
            lots_to_ferment = lots_in_age[:len(lots_in_age)//2]
            for lot_id, total_liters, _ in lots_to_ferment:
                liters = float(total_liters)
                deposit = next((d for d in available_deposits if d[1] >= liters), None)
                if deposit:
                    cur.execute("UPDATE wine_lots SET status = 'En Fermentación' WHERE id = %s", (lot_id,))
                    cur.execute("UPDATE containers SET status = 'ocupado', current_volume = %s, current_lot_id = %s WHERE id = %s", (liters, lot_id, deposit[0]))
                    available_deposits.remove(deposit)
    
    for year in range(start_year, date.today().year + 1):
        for category in ['Comerciales y de Marketing', 'Generales y Administrativos']:
            for cost_type, desc, _ in cost_types[category]:
                all_costs.append((str(uuid.uuid4()), tenant_id, None, cost_type, random.uniform(2000, 10000), desc, date(year, 12, 31), None))
    
    execute_values(cur, "INSERT INTO costs (id, tenant_id, related_lot_id, cost_type, amount, description, cost_date, related_parcel_id) VALUES %s", all_costs)

    print("\n📦 Creando productos finales y su historial de ventas...")
    cur.execute("SELECT w.id, w.grape_variety, w.vintage_year, w.total_liters, w.origin_parcel_id FROM wine_lots w WHERE w.tenant_id = %s AND w.status = 'Embotellado'", (tenant_id,))
    lots_for_products = cur.fetchall()
    if lots_for_products:
        products_data = []
        for lot_id, variety, vintage, liters, parcel_id in lots_for_products:
            cur.execute("SELECT SUM(amount) FROM costs WHERE related_lot_id = %s OR related_parcel_id = %s", (lot_id, parcel_id))
            total_cost = (cur.fetchone()[0] or 0)
            num_bottles = int(float(liters) / 0.75) if liters else 1
            unit_cost = float(total_cost) / num_bottles if num_bottles > 0 else 0
            prod_base = next(p for p in products_base if p['variety'] == variety)
            price = prod_base['base_price'] * random.uniform(1.0, 1.15)
            products_data.append((str(uuid.uuid4()), tenant_id, f"{prod_base['name']} {vintage}", f"{variety[:3].upper()}{vintage}{random.randint(100,999)}", round(price, 2), round(unit_cost, 2), lot_id, num_bottles))
        execute_values(cur, "INSERT INTO products (id, tenant_id, name, sku, price, unit_cost, wine_lot_origin_id, stock_units) VALUES %s", products_data)

    cur.execute("SELECT id, price FROM products WHERE tenant_id = %s;", (tenant_id,))
    db_products = cur.fetchall()
    if db_products:
        sales_to_insert, sale_details_to_insert = [], []
        total_days = (date.today() - date.fromisoformat(f"{start_year}-01-01")).days
        for day in range(total_days):
             if random.random() > 0.4:
                current_date = date.fromisoformat(f"{start_year}-01-01") + timedelta(days=day)
                for _ in range(random.randint(1, 3)):
                    sale_id, sale_total = str(uuid.uuid4()), 0
                    for prod_id, price in random.sample(db_products, k=random.randint(1, min(2, len(db_products)))):
                        qty = random.randint(1, 6)
                        sale_total += qty * float(price)
                        sale_details_to_insert.append((str(uuid.uuid4()), sale_id, prod_id, qty, price, tenant_id))
                    sales_to_insert.append((sale_id, tenant_id, current_date, fake.company(), round(sale_total, 2)))
        if sales_to_insert:
            execute_values(cur, "INSERT INTO sales (id, tenant_id, sale_date, customer_name, total_amount) VALUES %s", sales_to_insert)
        if sale_details_to_insert:
            execute_values(cur, "INSERT INTO sale_details (id, sale_id, product_id, quantity, unit_price, tenant_id) VALUES %s", sale_details_to_insert)

    conn.commit()
    print("\n🎉 ¡Proceso completado! La base de datos está lista.")
    print(f"\n🔑 Usuario: {admin_user} / Contraseña: {admin_pass}")

except Exception as e:
    conn.rollback()
    import traceback
    traceback.print_exc()
    print(f"\n❌ ERROR: Se ha hecho rollback. Causa: {e}")
finally:
    cur.close()
    conn.close()
    print("🔌 Conexión a la base de datos cerrada.")