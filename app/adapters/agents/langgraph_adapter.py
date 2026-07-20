# app/adapters/agents/langgraph_adapter.py
from typing import TypedDict, List, Annotated
import operator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
import logging

from app.core.domain.models import PartialInclusionDependency
from app.core.ports.orchestrator_port import OrchestratorPort
from app.config.config import settings

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    current_pind: PartialInclusionDependency
    proponent_arg: str
    critic_verdict: str

class LangGraphAdapter(OrchestratorPort):
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            api_key=settings.LLM_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            temperature=0.3
        )
        self.graph = self._build_graph()

    def _proponent_node(self, state: AgentState):
        pind = state["current_pind"]
        
        # Imprimir cabecera del debate
        print("\n" + "="*60)
        print(f"🔍 EVALUANDO RELACIÓN: {pind.dependent.table_name}.{pind.dependent.column_name} -> {pind.referenced.table_name}.{pind.referenced.column_name}")
        print("="*60)
        
        prompt = f"""
        Eres un analista de datos descubriendo relaciones en una base de datos opaca.
        Se ha detectado una coincidencia matemática (pIND) en esta dirección exacta:
        - Origen: '{pind.dependent.column_name}' (Tabla: {pind.dependent.table_name})
        - Destino: '{pind.referenced.column_name}' (Tabla: {pind.referenced.table_name})
        
        Analiza los nombres. ¿Tiene sentido que la columna ORIGEN dependa de la columna DESTINO?
        """
        msg = self.llm.invoke([SystemMessage(content="Eres el Agente Proponente."), HumanMessage(content=prompt)])
        
        # Imprimir respuesta del Proponente
        print("\n🗣️  [AGENTE PROPONENTE]:")
        print("-" * 60)
        print(msg.content.strip())
        
        return {"proponent_arg": msg.content}

    def _critic_node(self, state: AgentState):
        pind = state["current_pind"]
        arg = state["proponent_arg"]
        
        prompt = f"""
        Eres el Agente Crítico, un auditor implacable de bases de datos.
        El Proponente analiza si la columna ORIGEN '{pind.dependent.column_name}' (Tabla: {pind.dependent.table_name}) 
        puede ser una clave foránea que apunta a la columna DESTINO '{pind.referenced.column_name}' (Tabla: {pind.referenced.table_name}).
        
        Argumento del Proponente: {arg}
        
        REGLAS DE AUDITORÍA:
        1. El ORIGEN debe ser un atributo del DESTINO. (Ej: Un 'paciente' tiene una 'ciudad').
        2. Ignora la coincidencia matemática de IDs pequeños. Usa el sentido común semántico.
        3. Evalúa si la relación ORIGEN -> DESTINO es lógica en el mundo real.
        
        Si no tiene sentido direccional, RECHAZA. Responde estrictamente al final con:
        [VERDICTO: ACEPTAR] o [VERDICTO: RECHAZAR]
        """
        msg = self.llm.invoke([SystemMessage(content="Eres el Agente Crítico."), HumanMessage(content=prompt)])
        
        # Imprimir respuesta del Crítico
        print("\n🕵️  [AGENTE CRÍTICO]:")
        print("-" * 60)
        print(msg.content.strip())
        print("-" * 60)
        
        verdict = "ACEPTAR" if "[VERDICTO: ACEPTAR]" in msg.content else "RECHAZAR"
        
        if verdict == "ACEPTAR":
            print(f"✅ RESULTADO: ACEPTADA\n")
        else:
            print(f"❌ RESULTADO: RECHAZADA\n")
            
        return {"critic_verdict": verdict}

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("proponent", self._proponent_node)
        workflow.add_node("critic", self._critic_node)

        workflow.set_entry_point("proponent")
        workflow.add_edge("proponent", "critic")
        workflow.add_edge("critic", END)
        
        return workflow.compile()

    def validate_pinds(self, pinds: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
        logger.info(f"Iniciando validación multi-agente de {len(pinds)} pINDs...")
        validated_pinds = []
        
        for i, pind in enumerate(pinds, 1):
            initial_state = {
                "current_pind": pind,
                "proponent_arg": "",
                "critic_verdict": ""
            }
            final_state = self.graph.invoke(initial_state)
            
            if final_state["critic_verdict"] == "ACEPTAR":
                validated_pinds.append(pind)
                
        logger.info(f"Validación completada. {len(validated_pinds)} pINDs validadas.")
        return validated_pinds
    
    # Añadir este método a la clase LangGraphAdapter
    def generate_report(self, pinds: List[PartialInclusionDependency], emergence_index: float, is_emergence: bool) -> str:
        pinds_str = "\n".join([f"- {p.dependent.table_name}.{p.dependent.column_name} -> {p.referenced.table_name}.{p.referenced.column_name} (Fuerza: {p.rho})" for p in pinds])
        
        prompt = f"""
        Eres el Agente Documentador de un sistema de descubrimiento de complejidad. 
        Tu trabajo es traducir un linaje matemático a un informe ejecutivo en lenguaje natural.
        
        Datos descubiertos a ciegas (Relaciones validadas):
        {pinds_str}
        
        Métricas del sistema:
        - Índice de Emergencia E(P,t): {emergence_index:.4f}
        - ¿Es un Patrón Emergente Persistente?: {'SÍ' if is_emergence else 'NO'}
        
        Genera un informe breve (3-4 párrafos) explicando:
        1. Qué estructuras se han descubierto en el pozo de datos.
        2. Si el sistema está estable o si está emergiendo un nuevo patrón macroscópico.
        3. Qué significado de negocio podría tener esto.
        """
        
        msg = self.llm.invoke([
            SystemMessage(content="Eres un analista de datos senior redactando un informe para la dirección."),
            HumanMessage(content=prompt)
        ])
        
        return msg.content