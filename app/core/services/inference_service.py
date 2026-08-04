# app/core/services/inference_service.py
import logging
from app.adapters.db.sqlalchemy_adapter import SqlAlchemyAdapter
from app.adapters.agents.langgraph_adapter import LangGraphAdapter
from app.adapters.db.neo4j_adapter import Neo4jAdapter
from app.core.domain.emergence import EmergenceEngine

logger = logging.getLogger(__name__)

class InferenceService:
    def __init__(self):
        self.orchestrator_adapter = LangGraphAdapter()
        self.neo4j_adapter = Neo4jAdapter()
        self.emergence_engine = EmergenceEngine()

    async def run_discovery_pipeline(self, db_url: str, rho_threshold: float = 0.90) -> dict:
        logger.info("Iniciando pipeline asíncrono completo (Etapas 1 a 4)...")
        
        # 1. Conexión y descubrimiento a ciegas (Fase A)
        db_adapter = SqlAlchemyAdapter(db_url=db_url)
        await db_adapter.connect()
        columns = await db_adapter.get_all_columns()
        raw_pinds = await db_adapter.discover_pinds(columns, rho_threshold=rho_threshold)
        await db_adapter.disconnect()
        
        # 2. Validación Multi-Agente (Fase B - LLM)
        validated_pinds = await self.orchestrator_adapter.validate_pinds(raw_pinds)
        
        ontologized_pinds = []
        graph = None
        
        # 3. Materialización y Extracción del Grafo (Neo4j)
        if validated_pinds:
            ontologized_pinds = await self.orchestrator_adapter.generate_ontology(validated_pinds)
            
            await self.neo4j_adapter.connect()
            await self.neo4j_adapter.save_pinds(ontologized_pinds)
            graph = await self.neo4j_adapter.get_networkx_graph()
            await self.neo4j_adapter.disconnect()
        
        # 4. Cálculo de Emergencia, Persistencia y Delta Topológico (Pilar 3)
        emergence_index = 0.0
        is_emergence = False
        emergence_details = ""
        
        if graph and graph.number_of_nodes() > 0:
            current_sig = self.emergence_engine.calculate_spectral_signature(graph)
            baseline_sig, history, baseline_nodes, baseline_edges = self.emergence_engine.load_state()
            
            current_nodes = list(graph.nodes())
            # Formatear aristas actuales para comparar
            current_edges = [(u, v) for u, v in graph.edges()]
            
            # Si no hay línea base (primera ejecución), la guardamos
            if not baseline_sig:
                logger.info("Primera ejecución detectada. Guardando línea base y topología.")
                self.emergence_engine.save_state(current_sig, [0.0], current_nodes, current_edges)
            else:
                # Calcular Índice de Emergencia E(P,t)
                emergence_index = self.emergence_engine.calculate_emergence_index(current_sig, baseline_sig)
                history.append(emergence_index)
                
                # Validar Persistencia (Umbral θ=0.15, Ventana=3)
                is_emergence = self.emergence_engine.validate_persistence(history, threshold=0.15, window=3)
                
                # Calcular Delta Topológico si hay una desviación significativa
                if emergence_index > 0.15:
                    new_nodes = set(current_nodes) - set(baseline_nodes)
                    removed_nodes = set(baseline_nodes) - set(current_nodes)
                    
                    # Identificar el "Nexus Node" (Nodo viejo que se conecta con nodos nuevos)
                    nexus_nodes = set()
                    for u, v in graph.edges():
                        if u in new_nodes and v in baseline_nodes: nexus_nodes.add(v)
                        if v in new_nodes and u in baseline_nodes: nexus_nodes.add(u)
                    
                    emergence_details = f"""
                    Evidencia del Cambio de Régimen:
                    - Nodos Nuevos Detectados: {list(new_nodes) if new_nodes else 'Ninguno'}
                    - Nodos Desaparecidos: {list(removed_nodes) if removed_nodes else 'Ninguno'}
                    - Anclaje Topológico (Nexus): El nuevo patrón se conectó a la estructura previa a través de los nodos {list(nexus_nodes) if nexus_nodes else 'sin conexión directa'}.
                    """
                    
                    logger.info(f"Delta Topológico: Nuevos={list(new_nodes)}, Nexus={list(nexus_nodes)}")
                
                # Guardar estado para la próxima ejecución
                # Si no hay emergencia, actualizamos la baseline para que "aprenda" el nuevo régimen normal
                if not is_emergence and emergence_index < 0.05:
                    self.emergence_engine.save_state(current_sig, history, current_nodes, current_edges)
                else:
                    self.emergence_engine.save_state(baseline_sig, history, baseline_nodes, baseline_edges)
                
                logger.info(f"Índice de Emergencia E(P,t): {emergence_index:.4f} | Persistencia: {is_emergence}")
        
        # 5. Explicabilidad (Fase C)
        report = await self.orchestrator_adapter.generate_report(
            pinds=ontologized_pinds,
            emergence_index=emergence_index,
            is_emergence=is_emergence,
            emergence_details=emergence_details # <- Pasamos la evidencia
        )
        
        return {
            "total_raw_pinds": len(raw_pinds),
            "total_validated_pinds": len(validated_pinds),
            "emergence_index": emergence_index,
            "is_emergence": is_emergence,
            "validated_relationships": [f"{p.dependent.table_name}.{p.dependent.column_name} -[{p.semantic_label}]-> {p.referenced.table_name}.{p.referenced.column_name} (ρ={p.rho})" for p in ontologized_pinds],
            "executive_report": report
        }