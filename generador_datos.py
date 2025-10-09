# Saas_GrapeIQ_V1.0/generador_datos.py (CORREGIDO Y MEJORADO)

import os
import sys
import psycopg2
from psycopg2.extras import execute_values, Json
from dotenv import load_dotenv
from faker import Faker
import random
import uuid
import json
from datetime import date, timedelta, datetime
import math
from passlib.context import CryptContext
from sqlalchemy import create_engine
import importlib.util

# --- 1. CONFIGURACIÓN INICIAL ---
print("🚀 Iniciando el generador de datos DEFINITIVO para GrapeIQ...")

try:
    spec = importlib.util.spec_from_file_location("models", os.path.join(os.path.dirname(__file__), 'app', 'models.py'))
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)
    Base = models.Base
    print("✅ Módulo 'models' cargado con éxito.")
except Exception as e:
    print(f"❌ ERROR CRÍTICO: No se pudo cargar 'app/models.py'. Revisa la estructura de archivos. Error: {e}")
    exit()

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
engine = create_engine(DATABASE_URL)

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
NUM_CONTAINERS = 40

# --- 4. DATOS BASE (COMPLETOS) ---
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
    {'name': 'Alma de Golia', 'variety': 'Mencía', 'base_price': 15.99, 'wine_type': 'tinto'},
    {'name': 'El Pájaro Rojo', 'variety': 'Mencía', 'base_price': 9.95, 'wine_type': 'tinto'},
    {'name': 'Señorío de Nava', 'variety': 'Tempranillo', 'base_price': 8.75, 'wine_type': 'tinto'},
    {'name': 'Cuatro Pasos', 'variety': 'Prieto Picudo', 'base_price': 7.50, 'wine_type': 'rosado'},
    {'name': 'Pardevalles', 'variety': 'Albarín', 'base_price': 12.95, 'wine_type': 'blanco'},
    {'name': 'Verdeal', 'variety': 'Verdejo', 'base_price': 7.90, 'wine_type': 'blanco'}
]
container_definitions = { 'Depósito': ['Inox', 'Hormigón'], 'Barrica': ['Roble Francés', 'Roble Americano'] }
cooperages = ['Radoux', 'Seguin Moreau', 'Taransaud', 'Demptos']
toast_levels = ['Ligero', 'Medio', 'Medio Plus', 'Fuerte']
field_activities = ['Poda', 'Tratamiento Fitosanitario', 'Riego', 'Abonado', 'Vendimia']
cost_types = {
    'Viñedo y Vendimia': [('Mano de Obra Campo', 'Salarios', '€/año'), ('Fitosanitarios', 'Tratamientos', '€/ha'), ('Fertilizantes', 'Abonado', '€/ha'), ('Combustible', 'Maquinaria', '€/año')],
    'Vinificación': [('Levaduras', 'Fermentación', '€/L'), ('Laboratorio', 'Análisis', '€/L'), ('Energía', 'Electricidad', '€/año')],
    'Crianza y Almacenamiento': [('Mantenimiento Barricas', 'Limpieza', '€/barrica'), ('Amortización Barricas', 'Coste anual', '€/año')],
    'Embotellado y Empaquetado': [('Botellas', 'Compra', '€/ud'), ('Corchos', 'Suministro', '€/ud'), ('Etiquetas', 'Diseño', '€/ud')],
    'Comerciales y de Marketing': [('Publicidad', 'Campañas', '€/año'), ('Eventos', 'Ferias', '€/año'), ('Comisiones', 'Ventas', '%')],
    'Generales y Administrativos': [('Salarios Oficina', 'Administración', '€/año'), ('Alquiler', 'Oficinas', '€/año'), ('Gestoría', 'Asesoría', '€/año')]
}
SALE_CHANNELS = { 'Tienda Física': 0.40, 'Online': 0.25, 'Distribuidor': 0.20, 'Exportación': 0.15 }
SPECIAL_EVENTS_BASE = [
    {'name': 'Feria del Vino de León', 'month': 6, 'day': 15, 'duration_days': 3, 'impact': 5.0},
    {'name': 'Cata Privada Anual', 'month': 9, 'day': 20, 'duration_days': 1, 'impact': 3.0},
    {'name': 'Evento Gastronómico Local', 'month': 11, 'day': 5, 'duration_days': 2, 'impact': 2.5}
]
spanish_holidays = {
    (1, 1): "Año Nuevo", (1, 6): "Epifanía del Señor", (5, 1): "Día del Trabajador", (8, 15): "Asunción de la Virgen",
    (10, 12): "Fiesta Nacional de España", (11, 1): "Todos los Santos", (12, 6): "Día de la Constitución",
    (12, 8): "Inmaculada Concepción", (12, 25): "Navidad"
}

SEASONAL_MULTIPLIER = {
    1: 0.8, 2: 0.7, 3: 0.9, 4: 1.1, 5: 1.3, 6: 1.6,
    7: 1.8, 8: 1.7, 9: 1.2, 10: 1.0, 11: 0.8, 12: 2.0
}

def get_seasonal_temperature(current_date, start_year):
    day_of_year = current_date.timetuple().tm_yday
    warming_trend = (current_date.year - start_year) * 0.1
    temp = 15 + 10 * math.sin((day_of_year - 80) * (2 * math.pi / 365)) + warming_trend
    return round(temp + random.uniform(-2.5, 2.5), 1)

def create_random_geojson(lat, lon, scale=0.01):
    points = [[lon + (random.random() - 0.5) * scale, lat + (random.random() - 0.5) * scale] for _ in range(random.randint(4, 6))]
    points.append(points[0])
    return json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [points]}}]})

# --- 5. EJECUCIÓN DEL SCRIPT ---
try:
    print("\n⚠️  Borrando y recreando la base de datos desde cero...")
    with conn.cursor() as cursor:
        all_tables = Base.metadata.sorted_tables
        for table in reversed(all_tables):
            print(f"   ...Borrando tabla '{table.name}' en cascada...")
            cursor.execute(f"DROP TABLE IF EXISTS {table.name} CASCADE;")
    conn.commit()
    print("   ...tablas antiguas eliminadas.")

    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos recreada con la estructura más reciente.")
    
    print("\n🌱 Creando activos y estructura base...")
    tenant_id = str(uuid.uuid4())
    cur.execute("INSERT INTO tenants (id, name) VALUES (%s, %s);", (tenant_id, 'Bodega de Demostración'))
    admin_user, admin_pass = 'admin', 'admin123'
    cur.execute("INSERT INTO users (id, tenant_id, username, hashed_password, role) VALUES (%s, %s, %s, %s, %s);",
                (str(uuid.uuid4()), tenant_id, admin_user, pwd_context.hash(admin_pass), 'admin'))

    parcels_data = [(str(uuid.uuid4()), tenant_id, p['name'], p['variety'], p['area'], create_random_geojson(42.55 + i * 0.015, -6.59 + i * 0.015)) for i, p in enumerate(parcels_base)]
    execute_values(cur, "INSERT INTO parcels (id, tenant_id, name, variety, area_hectares, geojson_coordinates) VALUES %s", parcels_data)
    
    containers_data = []
    for i in range(NUM_CONTAINERS):
        is_barrel = i >= 10
        main_type = 'Barrica' if is_barrel else 'Depósito'
        defs = container_definitions[main_type]
        capacity = 225 if is_barrel else random.choice([5000, 10000])
        barrel_age = random.randint(0, 4) if is_barrel else None
        toast_level = random.choice(toast_levels) if is_barrel else None
        cooperage = random.choice(cooperages) if is_barrel else None
        containers_data.append((str(uuid.uuid4()), f"{random.choice(defs)}-{i+1}", main_type, capacity, random.choice(defs), tenant_id, 'vacío', 0.0, barrel_age, toast_level, cooperage))
    execute_values(cur, "INSERT INTO containers (id, name, type, capacity_liters, material, tenant_id, status, current_volume, barrel_age, toast_level, cooperage) VALUES %s", containers_data)
    
    cost_parameters_data = [(str(uuid.uuid4()), tenant_id, name, random.uniform(10, 100), unit, category, datetime.now()) for category, costs in cost_types.items() for name, _, unit in costs]
    execute_values(cur, "INSERT INTO cost_parameters (id, tenant_id, parameter_name, value, unit, category, last_updated) VALUES %s", cost_parameters_data)
    
    print("\n🌡️  Generando datos de condiciones ambientales...")
    room_conditions_data = [
        (str(uuid.uuid4()), tenant_id, 'Sala de Depósitos', round(random.uniform(18.5, 20.5), 1), round(random.uniform(65.0, 75.0), 1), datetime.now()),
        (str(uuid.uuid4()), tenant_id, 'Bodega de Crianza', round(random.uniform(14.0, 16.0), 1), round(random.uniform(78.0, 85.0), 1), datetime.now())
    ]
    execute_values(cur, "INSERT INTO room_conditions (id, tenant_id, room_name, temperature, humidity, timestamp) VALUES %s", room_conditions_data)

    print("\n🔄 Simulando cosechas, costes y ciclo de vida por etapas...")
    start_year = date.today().year - SIM_YEARS + 1
    cur.execute("SELECT id, name, variety, area_hectares FROM parcels WHERE tenant_id = %s;", (tenant_id,)); db_parcels = cur.fetchall()
    all_wine_lots_data, all_costs, all_field_logs, all_lab_analytics, all_winemaking_logs = [], [], [], [], []

    for year in range(start_year, date.today().year + 1):
        for parcel_id, parcel_name, variety, area in db_parcels:
            for _ in range(NUM_FIELD_LOGS_PER_YEAR // len(db_parcels)):
                log_date = date(year, random.randint(1, 12), random.randint(1, 28))
                all_field_logs.append((str(uuid.uuid4()), log_date, log_date, random.choice(field_activities), fake.sentence(), tenant_id, parcel_id, True))
            for cost_type, desc, _ in cost_types['Viñedo y Vendimia']:
                all_costs.append((str(uuid.uuid4()), tenant_id, None, cost_type, round(float(area) * random.uniform(200, 600), 2), desc, date(year, random.randint(1, 12), 15), parcel_id))
            if prod_base := next((p for p in products_base if p['variety'] == variety), None):
                initial_kg = float(area) * random.uniform(800, 1200); total_liters = initial_kg / 1.6; lot_id = str(uuid.uuid4())
                all_wine_lots_data.append([lot_id, f"{variety} {year} ({parcel_name})", variety, year, 'Cosechado', tenant_id, parcel_id, initial_kg, total_liters, total_liters, prod_base['wine_type']])
                
                initial_total_acidity = round(random.uniform(4.5, 8.0), 2)
                
                # Se registran solo los parámetros iniciales de la uva/mosto
                all_winemaking_logs.append((
                    str(uuid.uuid4()), lot_id, date(year, 9, 25),
                    # Parámetros de Uva/Mosto
                    round(random.uniform(11.5, 14.5), 2),  # sugar_level
                    initial_total_acidity,   # total_acidity
                    round(random.uniform(15.0, 25.0), 1), # reception_temp
                    random.randint(20, 60),     # added_so2
                    random.choice(['Limpio', 'Algo turbio', 'Turbio']), # turbidity
                    random.choice(['Baja', 'Media', 'Alta', 'Muy Alta']), # color_intensity
                    fake.sentence(nb_words=5),  # aromas
                    tenant_id
                ))

                for cost_type, desc, _ in cost_types['Vinificación']:
                    all_costs.append((str(uuid.uuid4()), tenant_id, lot_id, cost_type, round(total_liters * random.uniform(0.10, 0.25), 2), desc, date(year, 10, 5), None))
                
                all_lab_analytics.append((str(uuid.uuid4()), lot_id, None, date(year, 11, 15), round(random.uniform(12.5, 14.5), 1), round(random.uniform(4.5, 6.0), 1), round(random.uniform(0.3, 0.6), 2), round(random.uniform(3.3, 3.8), 2), random.randint(15, 25), random.randint(40, 80), "Análisis post-fermentación alcohólica.", tenant_id))

    execute_values(cur, "INSERT INTO field_logs (id, start_datetime, end_datetime, activity_type, description, tenant_id, parcel_id, all_day) VALUES %s", all_field_logs)
    execute_values(cur, "INSERT INTO wine_lots (id, name, grape_variety, vintage_year, status, tenant_id, origin_parcel_id, initial_grape_kg, total_liters, liters_unassigned, wine_type) VALUES %s", all_wine_lots_data)
    if all_winemaking_logs:
        execute_values(cur, """
            INSERT INTO winemaking_logs (
                id, lot_id, log_date, sugar_level, total_acidity, reception_temp, added_so2,
                turbidity, color_intensity, aromas, tenant_id
            ) VALUES %s
        """, all_winemaking_logs)

    cur.execute("SELECT id, capacity_liters FROM containers WHERE tenant_id = %s AND type = 'Depósito'", (tenant_id,)); available_deposits = [list(d) for d in cur.fetchall()]
    cur.execute("SELECT id FROM containers WHERE tenant_id = %s AND type = 'Barrica'", (tenant_id,)); available_barrels_ids = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id, total_liters, vintage_year, wine_type FROM wine_lots WHERE tenant_id = %s AND status = 'Cosechado'", (tenant_id,)); lots_to_process = sorted(cur.fetchall(), key=lambda x: x[2])
    lots_by_age = {i: [] for i in range(SIM_YEARS)}; [lots_by_age[date.today().year - lot[2]].append(lot) for lot in lots_to_process if (date.today().year - lot[2]) in lots_by_age]
    
    fermentation_controls = []
    for age in sorted(lots_by_age.keys(), reverse=True):
        lots_in_age = sorted(lots_by_age[age], key=lambda x: x[1])
        if age >= 2:
            for i, (lot_id, total_liters, vintage, _) in enumerate(lots_in_age):
                status = 'Embotellado' if i % 2 == 0 else 'Listo para Embotellar'
                cur.execute("UPDATE wine_lots SET status = %s WHERE id = %s", (status, lot_id))
                if status == 'Embotellado':
                    num_bottles = int(float(total_liters) / 0.75)
                    for cost_type, desc, _ in cost_types['Embotellado y Empaquetado']:
                        all_costs.append((str(uuid.uuid4()), tenant_id, lot_id, cost_type, round(num_bottles * random.uniform(0.2, 0.5), 2), desc, date(vintage + 2, 3, 1), None))
        elif age == 1:
            lots_for_aging, lots_for_ready = lots_in_age[:len(lots_in_age)//2], lots_in_age[len(lots_in_age)//2:]
            for lot_id, _, _, _ in lots_for_ready:
                 cur.execute("UPDATE wine_lots SET status = 'Listo para Embotellar' WHERE id = %s", (lot_id,))
            for lot_id, total_liters, vintage, _ in lots_for_aging:
                liters = float(total_liters)
                barrels_needed = int(liters / 225) + (1 if liters % 225 > 0 else 0)
                if len(available_barrels_ids) >= barrels_needed:
                    cur.execute("UPDATE wine_lots SET status = 'En Crianza' WHERE id = %s", (lot_id,))
                    barrels_for_lot = [available_barrels_ids.pop(0) for _ in range(barrels_needed)]
                    for b_id in barrels_for_lot:
                        cur.execute("UPDATE containers SET status = 'ocupado', current_volume = 225, current_lot_id = %s WHERE id = %s", (lot_id, b_id))
                        for i in range(random.randint(2, 5)):
                            analysis_date = date(vintage + 1, random.randint(3,11), random.randint(1,28))
                            all_lab_analytics.append((str(uuid.uuid4()), lot_id, b_id, analysis_date, round(random.uniform(13.0, 14.0), 1), round(random.uniform(5.0, 6.5), 1), round(random.uniform(0.4, 0.7), 2), round(random.uniform(3.5, 3.9), 2), random.randint(25, 35), random.randint(70, 100), f"Control de crianza #{i+1}. Se mantiene estable.", tenant_id))

                    for cost_type, desc, _ in cost_types['Crianza y Almacenamiento']:
                        all_costs.append((str(uuid.uuid4()), tenant_id, lot_id, cost_type, round(barrels_needed * random.uniform(20, 50), 2), desc, date(vintage + 1, 6, 1), None))
                else:
                    cur.execute("UPDATE wine_lots SET status = 'Listo para Embotellar' WHERE id = %s", (lot_id,))
        elif age == 0:
            for lot_id, total_liters, vintage, wine_type in lots_in_age[:len(lots_in_age)//2]:
                if deposit := next((d for d in available_deposits if d[1] >= float(total_liters)), None):
                    cur.execute("UPDATE wine_lots SET status = 'En Fermentación' WHERE id = %s", (lot_id,))
                    cur.execute("UPDATE containers SET status = 'ocupado', current_volume = %s, current_lot_id = %s WHERE id = %s", (float(total_liters), lot_id, deposit[0]))
                    
                    lot_initial_acidity = next((log[4] for log in all_winemaking_logs if log[1] == lot_id), 6.0)

                    for day_offset in range(15):
                        current_density = round(1.090 - (day_offset * 0.0065) + random.uniform(-0.001, 0.001), 4)
                        residual_sugar = max(0, (current_density - 1.000) * 131.25 * 1.5 - (15-day_offset) * 10)
                        current_total_acidity = round(lot_initial_acidity - (day_offset * 0.03) + random.uniform(-0.02, 0.02), 2)
                        
                        fermentation_controls.append((
                            str(uuid.uuid4()), deposit[0], lot_id, date(vintage, 10, 10 + day_offset),
                            round(18 + math.sin(day_offset / 2) * 4 + random.uniform(-0.5, 0.5), 1), current_density,
                            f"Control día {day_offset+1}. Olores limpios, reductivos.", tenant_id,
                            round(residual_sugar, 1), round(13.5 + random.uniform(-0.2, 0.2), 1),
                            round(random.uniform(3.4, 3.6) - (day_offset * 0.02), 2),
                            round(random.uniform(0.2, 0.4) + (day_offset * 0.01), 2),
                            random.randint(10, 20),
                            current_total_acidity # Nuevo campo añadido
                        ))
                    available_deposits.remove(deposit)

    for year in range(start_year, date.today().year + 1):
        for category in ['Comerciales y de Marketing', 'Generales y Administrativos']:
            for cost_type, desc, _ in cost_types[category]:
                all_costs.append((str(uuid.uuid4()), tenant_id, None, cost_type, random.uniform(2000, 10000), desc, date(year, 12, 31), None))
    
    if all_costs: execute_values(cur, "INSERT INTO costs (id, tenant_id, related_lot_id, cost_type, amount, description, cost_date, related_parcel_id) VALUES %s", all_costs)
    if fermentation_controls:
        execute_values(cur, """
            INSERT INTO fermentation_controls (
                id, container_id, lot_id, control_date, temperature, density, notes, tenant_id, 
                residual_sugar, potential_alcohol, ph, volatile_acidity, free_so2, total_acidity
            ) VALUES %s
        """, fermentation_controls)
    if all_lab_analytics: execute_values(cur, "INSERT INTO lab_analytics (id, lot_id, container_id, analysis_date, alcoholic_degree, total_acidity, volatile_acidity, ph, free_so2, total_so2, notes, tenant_id) VALUES %s", all_lab_analytics)

    print("\n📅 Creando eventos especiales históricos...")
    special_events_to_insert = []
    for year in range(start_year, date.today().year + 1):
        for event in SPECIAL_EVENTS_BASE:
            start_date = date(year, event['month'], event['day']); end_date = start_date + timedelta(days=event['duration_days'] - 1)
            special_events_to_insert.append((str(uuid.uuid4()), tenant_id, event['name'], start_date, end_date, f"{event['name']} del año {year}"))
    execute_values(cur, "INSERT INTO special_events (id, tenant_id, event_name, start_date, end_date, description) VALUES %s", special_events_to_insert)
    events_lookup = {(e[3], e[4]): (e[2], next(ev['impact'] for ev in SPECIAL_EVENTS_BASE if ev['name'] == e[2])) for e in special_events_to_insert}

    print("\n🍾 Creando materiales secos y eventos de embotellado...")
    dry_goods_data = []
    for material_type, supplier in [('Botella', 'Vidrala'), ('Corcho', 'Amorim'), ('Cápsula', 'Ramondin'), ('Etiqueta', 'Gráficas Lersi')]:
        for i in range(3):
            dry_goods_data.append((str(uuid.uuid4()), tenant_id, material_type, supplier, f"REF-{random.randint(100,999)}", f"LOTE-{supplier[:3].upper()}-{date.today().year - i}-{random.randint(1,5)}"))
    execute_values(cur, "INSERT INTO dry_goods (id, tenant_id, material_type, supplier, model_reference, supplier_lot_number) VALUES %s", dry_goods_data)
    
    cur.execute("SELECT id, material_type FROM dry_goods WHERE tenant_id = %s", (tenant_id,)); all_dry_goods = cur.fetchall()
    dry_goods_map = {mtype: [g[0] for g in all_dry_goods if g[1] == mtype] for mtype in ['Botella', 'Corcho', 'Cápsula', 'Etiqueta']}

    print("\n📦 Creando productos finales y su historial de ventas con PATRONES MARCADOS...")
    cur.execute("SELECT w.id, w.grape_variety, w.vintage_year, w.total_liters, w.origin_parcel_id FROM wine_lots w WHERE w.tenant_id = %s AND w.status = 'Embotellado'", (tenant_id,)); lots_for_products = cur.fetchall()
    bottling_events_data = []
    if lots_for_products:
        products_data = []
        for lot_id, variety, vintage, liters, parcel_id in lots_for_products:
            cur.execute("SELECT SUM(amount) FROM costs WHERE related_lot_id = %s OR related_parcel_id = %s", (lot_id, parcel_id)); total_cost = (cur.fetchone()[0] or 0)
            num_bottles = int(float(liters) / 0.75) if liters else 1; unit_cost = float(total_cost) / num_bottles if num_bottles > 0 else 0
            prod_base = next(p for p in products_base if p['variety'] == variety); price = prod_base['base_price'] * random.uniform(1.0, 1.15)
            product_id = str(uuid.uuid4())
            products_data.append((product_id, tenant_id, f"{prod_base['name']} {vintage}", f"{variety[:3].upper()}{vintage}{random.randint(100,999)}", round(price, 2), round(unit_cost, 2), lot_id, num_bottles, variety))
            
            bottling_date = datetime(vintage + 2, 3, random.randint(1, 28))
            bottling_events_data.append((str(uuid.uuid4()), lot_id, product_id, bottling_date, f"L-{vintage}-{random.randint(100, 999)}", round(random.uniform(0.1, 0.5), 2), random.choice(dry_goods_map['Botella']), random.choice(dry_goods_map['Corcho']), random.choice(dry_goods_map['Cápsula']), random.choice(dry_goods_map['Etiqueta']), random.randint(12, 24), tenant_id))
        
        execute_values(cur, "INSERT INTO products (id, tenant_id, name, sku, price, unit_cost, wine_lot_origin_id, stock_units, variety) VALUES %s", products_data)
        execute_values(cur, "INSERT INTO bottling_events (id, lot_id, product_id, bottling_date, official_lot_number, dissolved_oxygen, bottle_lot_id, cork_lot_id, capsule_lot_id, label_lot_id, retained_samples, tenant_id) VALUES %s", bottling_events_data)

    cur.execute("SELECT id, price, variety FROM products WHERE tenant_id = %s;", (tenant_id,)); db_products = cur.fetchall()
    if db_products:
        sales_to_insert, sale_details_to_insert = [], []
        total_days = (date.today() - date.fromisoformat(f"{start_year}-01-01")).days
        for day in range(total_days):
            current_date = date.fromisoformat(f"{start_year}-01-01") + timedelta(days=day)
            
            growth_factor = 1 + ((current_date.year - start_year) * 0.05)
            is_weekend = current_date.weekday() >= 5
            holiday_name = spanish_holidays.get((current_date.month, current_date.day))
            avg_temperature = get_seasonal_temperature(current_date, start_year)
            seasonal_factor = SEASONAL_MULTIPLIER.get(current_date.month, 1.0)
            
            event_multiplier = 1.0
            for (start_ev, end_ev), (name, impact) in events_lookup.items():
                if start_ev <= current_date <= end_ev: 
                    event_multiplier = impact * random.uniform(0.8, 1.2)
                    break

            base_sales_today = random.randint(1, 3)
            if is_weekend: base_sales_today += random.randint(2, 5)
            if holiday_name: base_sales_today += random.randint(3, 6)
            
            num_sales_today = int(base_sales_today * seasonal_factor * growth_factor)

            for _ in range(num_sales_today):
                sale_id, sale_total = str(uuid.uuid4()), 0
                sale_channel = random.choices(list(SALE_CHANNELS.keys()), weights=list(SALE_CHANNELS.values()), k=1)[0]
                current_sale_data = [sale_id, tenant_id, current_date, fake.company(), 0, is_weekend, holiday_name, avg_temperature, sale_channel]
                
                for prod_id, price, variety in random.sample(db_products, k=random.randint(1, min(3, len(db_products)))):
                    on_promotion, discount_percentage = False, 0.0
                    if current_date.month in [12, 7, 8] and random.random() < 0.2: 
                        on_promotion, discount_percentage = True, random.choice([0.15, 0.20, 0.25])
                    
                    qty = random.randint(1, 4) + random.randint(0, 2)
                    
                    if sale_channel == 'Distribuidor': qty *= 1.6
                    if sale_channel == 'Exportación': qty *= 2.2
                    if on_promotion: qty *= (1.8 + random.uniform(-0.3, 0.3))
                    if is_weekend: qty *= 1.5
                    if avg_temperature > 25 and variety in ['Albarín', 'Verdejo']: qty *= 1.7
                    
                    qty = max(1, int(qty * event_multiplier))

                    final_price = float(price) * (1 - discount_percentage)
                    sale_total += qty * final_price
                    sale_details_to_insert.append((str(uuid.uuid4()), sale_id, prod_id, qty, round(final_price, 2), tenant_id, on_promotion, discount_percentage))
                
                current_sale_data[4] = round(sale_total, 2)
                sales_to_insert.append(tuple(current_sale_data))

        if sales_to_insert: execute_values(cur, "INSERT INTO sales (id, tenant_id, sale_date, customer_name, total_amount, is_weekend, holiday_name, avg_temperature, channel) VALUES %s", sales_to_insert)
        if sale_details_to_insert: execute_values(cur, "INSERT INTO sale_details (id, sale_id, product_id, quantity, unit_price, tenant_id, on_promotion, discount_percentage) VALUES %s", sale_details_to_insert)

    conn.commit()
    print("\n🎉 ¡Proceso completado! La base de datos está lista con datos de CANALES y EVENTOS.")
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