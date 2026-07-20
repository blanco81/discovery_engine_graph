# app/core/services/inference_service.py
import logging
from app.adapters.db.sqlalchemy_adapter import SqlAlchemyAdapter
from app.adapters.agents.langgraph_adapter import LangGraphAdapter

logger = logging.getLogger(__name__)

class InferenceService:
    """
    Orquesta el flujo completo: Inferencia -> Validación -> Explicabilidad
    """
    def __init__(self):
        self.db_adapter = SqlAlchemyAdapter()
        self.orchestrator_adapter = LangGraphAdapter()

    def run_discovery_pipeline(self) -> dict:
        logger.info("Iniciando pipeline de descubrimiento completo...")
        
        # 1. Conexión y descubrimiento a ciegas (Fase A)
        self.db_adapter.connect()
        columns = self.db_adapter.get_all_columns()
        raw_pinds = self.db_adapter.discover_pinds(columns, rho_threshold=0.90)
        self.db_adapter.disconnect()
        
        # 2. Validación Multi-Agente (Fase B)
        validated_pinds = self.orchestrator_adapter.validate_pinds(raw_pinds)
        
        # 3. Simulación de Métricas de Emergencia (En producción, vendría de emergence_service.py)
        emergence_index = 0.04 
        is_emergence = False
        
        # 4. Explicabilidad (Fase C)
        report = self.orchestrator_adapter.generate_report(
            pinds=validated_pinds,
            emergence_index=emergence_index,
            is_emergence=is_emergence
        )
        
        return {
            "total_raw_pinds": len(raw_pinds),
            "total_validated_pinds": len(validated_pinds),
            "emergence_index": emergence_index,
            "is_emergence": is_emergence,
            "validated_relationships": [str(p) for p in validated_pinds],
            "executive_report": report
        }