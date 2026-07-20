import sys, os
sys.path.insert(0, os.path.abspath('./app'))

from adapters.db.sqlalchemy_adapter import SqlAlchemyAdapter
from adapters.agents.langgraph_adapter import LangGraphAdapter

def main():
    print("--- INICIO DEL PIPELINE (ETAPA 1 Y 3) ---")
    
    # 1. Fase A: Inferencia a ciegas (SQL)
    print("\n[1] Descubriendo pINDs a ciegas...")
    db_adapter = SqlAlchemyAdapter()
    db_adapter.connect()
    columns = db_adapter.get_all_columns()
    pinds = db_adapter.discover_pinds(columns, rho_threshold=0.90)
    db_adapter.disconnect()
    
    # 2. Fase B: Validación Multi-Agente (LangGraph + GLM-4)
    print(f"\n[2] Iniciando debate Socrático para {len(pinds)} pINDs...")
    # Limitamos a las primeras 5 para que la prueba con la API sea rápida
    #pinds_to_test = pinds[:5] 
    pinds_to_test = pinds

    
    orchestrator = LangGraphAdapter()
    validated_pinds = orchestrator.validate_pinds(pinds_to_test)
    
    print("\n--- RESULTADO FINAL ---")
    print(f"De {len(pinds_to_test)} pINDs matemáticas, los agentes validaron {len(validated_pinds)}:")
    for p in validated_pinds:
        print(f"  ✔️ {p.dependent.table_name}.{p.dependent.column_name} -> {p.referenced.table_name}.{p.referenced.column_name}")

if __name__ == "__main__":
    main()