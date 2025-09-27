import pandas as pd
from faker import Faker
import random
import uuid
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN INICIAL (Puedes modificar esto) ---
NUM_SALES_RECORDS = 15000  # Número de registros de venta a generar
OUTPUT_CSV_FILE = 'grapeiq_fictional_data.csv'

# --- 2. DATOS BASE FICTICIOS (¡Personaliza tus parcelas y vinos!) ---

# Base de Parcelas
parcels_base = [
    {'name': 'Viña del Monte', 'area': 5.2},
    {'name': 'El Rincón Soleado', 'area': 3.1},
    {'name': 'La Cuesta Alta', 'area': 7.8},
    {'name': 'Valle Escondido', 'area': 4.5},
]

# Base de Productos (Vinos). El script creará lotes a partir de esto.
products_base = [
    {'name': 'Alma de Golia Mencía', 'variety': 'Mencía', 'base_cost': 7.50, 'base_price': 14.99},
    {'name': 'El Pájaro Rojo', 'variety': 'Mencía', 'base_cost': 5.20, 'base_price': 9.95},
    {'name': 'Señorío de Nava Crianza', 'variety': 'Tempranillo', 'base_cost': 4.50, 'base_price': 8.75},
    {'name': 'Cuatro Pasos Rosado', 'variety': 'Prieto Picudo', 'base_cost': 3.80, 'base_price': 7.50},
    {'name': 'Pardevalles Albarín', 'variety': 'Albarín', 'base_cost': 6.50, 'base_price': 12.95},
    {'name': 'Verdeal Verdejo', 'variety': 'Verdejo', 'base_cost': 4.10, 'base_price': 7.90},
]

# Inicializar generador de datos falsos
fake = Faker('es_ES')

# --- 3. GENERACIÓN DE ENTIDADES CON IDs ---

print("Preparando la simulación: parcelas, lotes, productos y clientes...")

# Parcelas con IDs
parcels = []
for p in parcels_base:
    parcels.append({
        'ParcelID': str(uuid.uuid4()),
        'ParcelName': p['name'],
        'ParcelAreaHectares': p['area']
    })

# Lotes y Productos (Simulamos un lote por cada año y producto)
wines = []
for vintage in [2021, 2022, 2023]:
    for prod in products_base:
        parcel = random.choice(parcels)
        initial_kg = random.uniform(3000, 15000)
        
        # Simular coste y precio con una pequeña variación anual
        unit_cost = round(prod['base_cost'] * random.uniform(0.95, 1.05), 2)
        unit_price = round(prod['base_price'] * random.uniform(0.98, 1.03), 2)

        wines.append({
            'ProductID': str(uuid.uuid4()),
            'SKU': f"{prod['variety'][:3].upper()}{vintage}{random.randint(100, 999)}",
            'ProductName': f"{prod['name']} {vintage}",
            'WineLotID': str(uuid.uuid4()),
            'WineLotName': f"{prod['variety']} - {parcel['ParcelName']} - {vintage}",
            'GrapeVariety': prod['variety'],
            'Vintage': vintage,
            'InitialGrapeKG': round(initial_kg, 2),
            'TotalLitersProduced': round(initial_kg / 1.6, 2),
            'ParcelID': parcel['ParcelID'],
            'ParcelName': parcel['ParcelName'],
            'ParcelAreaHectares': parcel['ParcelAreaHectares'],
            'UnitCost': unit_cost,
            'UnitPrice': unit_price
        })

# Clientes
customers = [{'CustomerID': str(uuid.uuid4()), 'CustomerName': fake.company()} for _ in range(200)]

# --- 4. GENERACIÓN DE LOS DATOS DE VENTAS ---

print(f"Generando {NUM_SALES_RECORDS} registros de ventas...")
sales_data = []
start_date = datetime.now() - timedelta(days=3 * 365)
end_date = datetime.now()

for i in range(NUM_SALES_RECORDS):
    wine_sold = random.choice(wines)
    customer = random.choice(customers)
    sale_date = start_date + timedelta(seconds=random.randint(0, int((end_date - start_date).total_seconds())))

    # Simular cantidad
    quantity = random.choices([random.randint(1, 6), random.randint(6, 12), random.randint(12, 60)], weights=[60, 30, 10])[0]

    total_sale = round(quantity * wine_sold['UnitPrice'], 2)
    total_cost = round(quantity * wine_sold['UnitCost'], 2)
    profit = round(total_sale - total_cost, 2)

    sales_data.append({
        'SaleID': str(uuid.uuid4()),
        'SaleDetailID': str(uuid.uuid4()),
        'Date': sale_date.strftime('%Y-%m-%d %H:%M:%S'),
        'CustomerID': customer['CustomerID'],
        'CustomerName': customer['CustomerName'],
        'Quantity': quantity,
        'UnitPrice': wine_sold['UnitPrice'],
        'TotalSale': total_sale,
        'ProductID': wine_sold['ProductID'],
        'SKU': wine_sold['SKU'],
        'ProductName': wine_sold['ProductName'],
        'WineLotID': wine_sold['WineLotID'],
        'WineLotName': wine_sold['WineLotName'],
        'GrapeVariety': wine_sold['GrapeVariety'],
        'Vintage': wine_sold['Vintage'],
        'InitialGrapeKG': wine_sold['InitialGrapeKG'],
        'TotalLitersProduced': wine_sold['TotalLitersProduced'],
        'ParcelID': wine_sold['ParcelID'],
        'ParcelName': wine_sold['ParcelName'],
        'ParcelAreaHectares': wine_sold['ParcelAreaHectares'],
        'UnitCost': wine_sold['UnitCost'],
        'TotalCost': total_cost,
        'Profit': profit
    })
    if (i + 1) % 1000 == 0:
        print(f"  ... {i + 1}/{NUM_SALES_RECORDS} registros generados.")

# --- 5. CREAR EL DATAFRAME Y GUARDAR EN CSV ---

print("Creando el archivo CSV...")
df = pd.DataFrame(sales_data)

df.to_csv(OUTPUT_CSV_FILE, index=False, sep=';', decimal=',')

print(f"\n¡Éxito! 🚀 Se ha generado el archivo '{OUTPUT_CSV_FILE}' con {len(df)} registros.")