# app/core/services/inference_service.py
import logging
from app.adapters.db.sqlalchemy_adapter import SqlAlchemyAdapter
from app.adapters.agents.langgraph_adapter import LangGraphAdapter
from app.adapters.db.neo4j_adapter import Neo4jAdapter
from app.adapters.db.state_adapter import InternalStateAdapter
from app.core.domain.emergence import EmergenceEngine
from app.core.domain.metrics import calculate_js_distance

logger = logging.getLogger(__name__)

class InferenceService:
    """
    Orquesta el flujo completo: Inferencia -> Validación -> Materialización -> Emergencia -> Explicabilidad
    """
    def __init__(self):
        self.orchestrator_adapter = LangGraphAdapter()
        self.neo4j_adapter = Neo4jAdapter()
        self.emergence_engine = EmergenceEngine()
        self.state_adapter = InternalStateAdapter()

    async def run_discovery_pipeline(self, db_url: str, rho_threshold: float = 0.90) -> dict:
        logger.info("Iniciando pipeline asíncrono completo (Etapas 1 a 4)...")
        
        # Asegurar que la tabla de estado interno existe
        await self.state_adapter.init_db()
        
        # 1. Conexión y descubrimiento a ciegas (Fase A)
        db_adapter = SqlAlchemyAdapter(db_url=db_url)
        await db_adapter.connect()
        columns = await db_adapter.get_all_columns()
        raw_pinds = await db_adapter.discover_pinds(columns, rho_threshold=rho_threshold)
        
        # Extraer distribuciones categóricas para la Firma Semántica (F_m)
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
        
        # 4. Cálculo de Emergencia, Persistencia y Delta Topológico (Pilar 3)
        emergence_index = 0.0
        is_emergence = False
        emergence_details = ""
        
        if graph and graph.number_of_nodes() > 0:
            current_sig = self.emergence_engine.calculate_spectral_signature(graph)
            
            # Cargar estado (6 valores)
            baseline_sig, history, baseline_nodes, baseline_edges, baseline_semantics, needs_reset = await self.state_adapter.load_state(db_url)
            
            current_nodes = list(graph.nodes())
            current_edges = [(u, v) for u, v in graph.edges()]
            
            # LÓGICA DE RESET (Caja Negra)
            if needs_reset == 1:
                logger.info(f"Reset solicitado para {db_url}. Asimilando nueva normalidad y manteniendo historial.")
                history.append(0.0)
                await self.state_adapter.save_state(db_url, current_sig, history, current_nodes, current_edges, semantic_distributions, needs_reset=0)
                emergence_index = 0.0
                
            # PRIMERA EJECUCIÓN (Sin línea base previa)
            elif not baseline_sig:
                logger.info(f"Primera ejecución para {db_url}. Guardando línea base estructural y semántica.")
                history.append(0.0)
                await self.state_adapter.save_state(db_url, current_sig, history, current_nodes, current_edges, semantic_distributions, needs_reset=0)
                emergence_index = 0.0
                
            # EJECUCIÓN NORMAL (Vigilancia)
            else:
                # 4.1 Desviación Estructural (D_s)
                ds = self.emergence_engine.calculate_emergence_index(current_sig, baseline_sig)
                
                # 4.2 Desviación Semántica (D_m)
                dm = 0.0
                drifted_column = ""
                for col_name, current_dist in semantic_distributions.items():
                    if col_name in baseline_semantics:
                        baseline_dist = baseline_semantics[col_name]
                        js_dist = calculate_js_distance(baseline_dist, current_dist)
                        if js_dist > dm:
                            dm = js_dist
                            drifted_column = col_name
                
                # El Índice de Emergencia Total es la suma de ambas desviaciones
                emergence_index = ds + dm
                history.append(emergence_index)
                
                # Validar Persistencia (Umbral θ=0.15, Ventana=3)
                is_emergence = self.emergence_engine.validate_persistence(history, threshold=0.15, window=3)
                
                # Calcular Delta Topológico si hay una desviación significativa
                if emergence_index > 0.15:
                    new_nodes = set(current_nodes) - set(baseline_nodes)
                    removed_nodes = set(baseline_nodes) - set(current_nodes)
                    
                    nexus_nodes = set()
                    for u, v in graph.edges():
                        if u in new_nodes and v in baseline_nodes: nexus_nodes.add(v)
                        if v in new_nodes and u in baseline_nodes: nexus_nodes.add(u)
                    
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
                    
                    logger.info(f"Delta Topológico: Nuevos={list(new_nodes)}, Nexus={list(nexus_nodes)}")
                
                if not is_emergence and emergence_index < 0.05:
                    await self.state_adapter.save_state(db_url, current_sig, history, current_nodes, current_edges, semantic_distributions, needs_reset=0)
                else:
                    await self.state_adapter.save_state(db_url, baseline_sig, history, baseline_nodes, baseline_edges, baseline_semantics, needs_reset=0)
                
                logger.info(f"Índice de Emergencia E(P,t): {emergence_index:.4f} | Persistencia: {is_emergence}")
        
        # Obtener el historial final actualizado (6 valores)
        _, current_history, _, _, _, _ = await self.state_adapter.load_state(db_url)
        
        # 5. Explicabilidad (Fase C - Informe Ejecutivo)
        report = await self.orchestrator_adapter.generate_report(
            pinds=ontologized_pinds,
            emergence_index=emergence_index,
            is_emergence=is_emergence,
            emergence_details=emergence_details
        )
        
        return {
            "total_raw_pinds": len(raw_pinds),
            "total_validated_pinds": len(validated_pinds),
            "emergence_index": emergence_index,
            "is_emergence": is_emergence,
            "validated_relationships": [f"{p.dependent.table_name}.{p.dependent.column_name} -[{p.semantic_label}]-> {p.referenced.table_name}.{p.referenced.column_name} (ρ={p.rho})" for p in ontologized_pinds],
            "executive_report": report,
            "emergence_history": current_history
        }