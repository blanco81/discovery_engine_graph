# app/core/services/inference_service.py
import logging
from app.adapters.db.sqlalchemy_adapter import SqlAlchemyAdapter
from app.adapters.agents.langgraph_adapter import LangGraphAdapter
from app.adapters.db.neo4j_adapter import Neo4jAdapter
from app.core.domain.emergence import EmergenceEngine
from app.core.domain.metrics import calculate_js_distance

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

        # ¡AQUÍ DECLARAMOS LA VARIABLE!
        semantic_distributions = await db_adapter.get_categorical_distributions(columns)

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
        
        # 4. Cálculo de Emergencia, Persistencia y Delta Topológico
        emergence_index = 0.0
        is_emergence = False
        emergence_details = ""
        
        # ¡NUEVO! Extraer distribuciones categóricas ANTES de desconectar la BD
        # (Asegúrate de que db_adapter siga conectado o vuelve a conectar)
        # Por simplicidad, asumimos que lo extraemos durante la Fase A:
        # (Si ya cerraste la conexión, abre una nueva o mueve este código antes del disconnect)
        
        # Supongamos que 'semantic_distributions' viene de la Fase A:
        # semantic_distributions = await db_adapter.get_categorical_distributions(columns)
        
        if graph and graph.number_of_nodes() > 0:
            current_sig = self.emergence_engine.calculate_spectral_signature(graph)
            # ¡MODIFICADO! Cargamos el estado semántico también
            baseline_sig, history, baseline_nodes, baseline_edges, baseline_semantics = self.emergence_engine.load_state()
            
            current_nodes = list(graph.nodes())
            current_edges = [(u, v) for u, v in graph.edges()]
            
            if not baseline_sig:
                logger.info("Primera ejecución. Guardando línea base estructural y semántica.")
                self.emergence_engine.save_state(current_sig, [0.0], current_nodes, current_edges, semantic_distributions)
            else:
                # 4.1 Desviación Estructural (D_s)
                ds = self.emergence_engine.calculate_emergence_index(current_sig, baseline_sig)
                
                # 4.2 Desviación Semántica (D_m) -> ¡NUEVO!
                dm = 0.0
                for col_name, current_dist in semantic_distributions.items():
                    if col_name in baseline_semantics:
                        baseline_dist = baseline_semantics[col_name]
                        js_dist = calculate_js_distance(baseline_dist, current_dist)
                        # Nos quedamos con la mayor desviación semántica encontrada
                        if js_dist > dm:
                            dm = js_dist
                            drifted_column = col_name
                
                # El Índice de Emergencia Total es la suma de ambas desviaciones
                emergence_index = ds + dm
                history.append(emergence_index)
                
                is_emergence = self.emergence_engine.validate_persistence(history, threshold=0.15, window=3)
                
                if emergence_index > 0.15:
                    new_nodes = set(current_nodes) - set(baseline_nodes)
                    removed_nodes = set(baseline_nodes) - set(current_nodes)
                    nexus_nodes = set()
                    for u, v in graph.edges():
                        if u in new_nodes and v in baseline_nodes: nexus_nodes.add(v)
                        if v in new_nodes and u in baseline_nodes: nexus_nodes.add(u)
                    
                    # Detallamos si fue estructural o semántico
                    emergence_details = f"""
                    Evidencia del Cambio de Régimen:
                    - Desviación Estructural (D_s): {ds:.4f}
                    - Desviación Semántica (D_m): {dm:.4f}
                    - Nodos Nuevos: {list(new_nodes) if new_nodes else 'Ninguno'}
                    - Nodos Desaparecidos: {list(removed_nodes) if removed_nodes else 'Ninguno'}
                    - Anclaje Topológico (Nexus): {list(nexus_nodes) if nexus_nodes else 'Ninguno'}
                    """
                    if dm > 0.15:
                        emergence_details += f"\n- ALERTA SEMÁNTICA: Se ha detectado Concept Drift en la columna '{drifted_column}'. La distribución de sus datos ha cambiado radicalmente."
                
                if not is_emergence and emergence_index < 0.05:
                    self.emergence_engine.save_state(current_sig, history, current_nodes, current_edges, semantic_distributions)
                else:
                    self.emergence_engine.save_state(baseline_sig, history, baseline_nodes, baseline_edges, baseline_semantics)
        
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