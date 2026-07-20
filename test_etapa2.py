import sys, os
sys.path.insert(0, os.path.abspath('./app'))

from adapters.db.sqlalchemy_adapter import SqlAlchemyAdapter
from adapters.db.neo4j_adapter import Neo4jAdapter
from core.domain.metrics import calculate_netsimile

def main():
    print("--- INICIO DEL PIPELINE (ETAPA 1 Y 2) ---")
    
    # 1. Fase A: Inferencia a ciegas (SQL)
    print("\n[1] Conectando al pozo relacional y descubriendo pINDs...")
    db_adapter = SqlAlchemyAdapter()
    db_adapter.connect()
    columns = db_adapter.get_all_columns()
    pinds = db_adapter.discover_pinds(columns, rho_threshold=0.95)
    db_adapter.disconnect()
    
    # 2. Fase B: Materialización en Neo4j
    print("\n[2] Materializando grafo en Neo4j...")
    neo4j_adapter = Neo4jAdapter()
    neo4j_adapter.connect()
    neo4j_adapter.save_pinds(pinds)
    
    # 3. Cálculo de la Firma Estructural (NetSimile)
    print("\n[3] Calculando Firma Estructural (NetSimile)...")
    G = neo4j_adapter.get_networkx_graph()
    neo4j_adapter.disconnect()
    
    if G.number_of_nodes() > 0:
        fs_signature = calculate_netsimile(G)
        print("\n--- FIRMA ESTRUCTURAL (Fs) CALCULADA ---")
        print(f"Vector NetSimile (longitud {len(fs_signature)}):")
        # Mostrar solo los primeros 5 valores para no llenar la consola
        print(fs_signature[:5], "...")
    else:
        print("El grafo está vacío, no se pudo calcular la firma.")

if __name__ == "__main__":
    main()