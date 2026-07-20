# test_blind_connection.py

import sys
import os
# Añadir la carpeta 'app' al path de Python
sys.path.insert(0, os.path.abspath('./app'))

from adapters.db.sqlalchemy_adapter import SqlAlchemyAdapter

def main():
    # 1. Inicializar el adaptador que implementa el puerto
    db_adapter = SqlAlchemyAdapter()
    
    try:
        # 2. Conectar a ciegas
        db_adapter.connect()
        
        # 3. Descubrir el esquema (Atributos)
        columns = db_adapter.get_all_columns()
        print("\n--- Columnas Descubiertas a Ciegas ---")
        for col in columns[:5]: # Mostrar solo las 5 primeras para no llenar la consola
            print(f"- {col} (Tipo: {col.data_type})")
            
        # 4. Descubrir Relaciones ocultas (pINDs)
        # Usamos un umbral rho de 0.90 para ser un poco más permisivos en la prueba
        pinds = db_adapter.discover_pinds(columns, rho_threshold=0.90)
        print("\n--- pINDs Descubiertas (Aristas del Grafo) ---")
        for pind in pinds:
            print(f"- {pind.dependent} apunta a {pind.referenced} (ρ = {pind.rho})")
            
    finally:
        db_adapter.disconnect()

if __name__ == "__main__":
    main()