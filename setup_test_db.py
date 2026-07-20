import sqlite3
import random

DB_NAME = "test_blind.db"

def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Limpiar tablas si ya existen
    cursor.execute("DROP TABLE IF EXISTS observations;")
    cursor.execute("DROP TABLE IF EXISTS patients;")
    cursor.execute("DROP TABLE IF EXISTS cities;")
    cursor.execute("DROP TABLE IF EXISTS inventory;")

    # Crear tablas SIN claves foráneas explícitas (Esquema opaco)
    cursor.execute('''
        CREATE TABLE cities (
            city_id INTEGER PRIMARY KEY,
            city_name TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE patients (
            patient_id INTEGER PRIMARY KEY,
            patient_name TEXT,
            home_city_id INTEGER,  -- Sabemos que relaciona, pero el esquema no lo dice
            age INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE observations (
            obs_id INTEGER PRIMARY KEY,
            obs_patient_code INTEGER, -- Relación oculta con patients.patient_id
            diagnosis_code TEXT,
            timestamp TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE inventory (
            item_id INTEGER PRIMARY KEY,
            item_name TEXT,
            quantity INTEGER
        )
    ''')

    # 1. Poblar Cities
    cities = [(1, 'Madrid'), (2, 'Barcelona'), (3, 'Valencia'), (4, 'Sevilla'), (5, 'Bilbao')]
    cursor.executemany("INSERT INTO cities VALUES (?, ?)", cities)

    # 2. Poblar Patients (100 pacientes)
    patients = []
    for i in range(1, 101):
        name = f"Paciente_{i}"
        city_id = random.choice([1, 2, 3, 4, 5]) # Todos apuntan a ciudades válidas
        age = random.randint(1, 90)
        patients.append((i, name, city_id, age))
    cursor.executemany("INSERT INTO patients VALUES (?, ?, ?, ?)", patients)

    # 3. Poblar Observations (500 observaciones)
    # Vamos a inyectar un 2% de ruido (violaciones) para probar el umbral rho
    observations = []
    for i in range(1, 501):
        # 98% de las veces usa un patient_id válido (1-100)
        # 2% de las veces usa un ID inexistente (ej. 999) para crear una pIND con rho=0.98
        if random.random() < 0.98:
            pat_code = random.randint(1, 100)
        else:
            pat_code = 999 # Ruido intencional
        
        diag_code = f"DX_{random.randint(1, 10)}"
        timestamp = f"2023-10-{random.randint(1, 28)}"
        observations.append((i, pat_code, diag_code, timestamp))
    
    cursor.executemany("INSERT INTO observations VALUES (?, ?, ?, ?)", observations)

    # 4. Poblar Inventory (Tabla no relacionada para probar falsos positivos)
    inventory = [(1, 'Guantes', 100), (2, 'Jeringas', 50), (3, 'Mascarillas', 200)]
    cursor.executemany("INSERT INTO inventory VALUES (?, ?, ?)", inventory)

    conn.commit()
    conn.close()
    print(f"✅ Base de datos de prueba '{DB_NAME}' creada con éxito.")
    print("   - Tablas: cities, patients, observations, inventory")
    print("   - Relaciones ocultas esperadas:")
    print("     * patients.home_city_id -> cities.city_id (rho = 1.0)")
    print("     * observations.obs_patient_code -> patients.patient_id (rho ≈ 0.98)")

if __name__ == "__main__":
    create_database()