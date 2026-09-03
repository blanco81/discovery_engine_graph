# app/adapters/agents/langgraph_adapter.py
from typing import List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import logging
import asyncio
import re

from app.core.domain.models import PartialInclusionDependency
from app.core.ports.orchestrator_port import OrchestratorPort
from app.config.config import settings

logger = logging.getLogger(__name__)

class LangGraphAdapter(OrchestratorPort):
    def __init__(self):
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "huggingface":
            base_url = "https://router.huggingface.co/v1"
            default_headers = {
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Motor de Descubrimiento de Complejidad"
            }
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL_NAME,
                api_key=settings.LLM_API_KEY,
                base_url=base_url,
                temperature=0.0, # Temp 0 para homogeneidad absoluta
                max_tokens=4000,
                default_headers=default_headers
            )
        elif provider == "google":
            self.llm = ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL_NAME,
                google_api_key=settings.LLM_API_KEY,
                temperature=0.0,
                max_output_tokens=4000
            )
        else:
            if provider == "groq":
                base_url = "https://api.groq.com/openai/v1"
                default_headers = None
            elif provider == "openrouter":
                base_url = "https://openrouter.ai/api/v1"
                default_headers = {
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "Motor de Descubrimiento de Complejidad"
                }
            elif provider == "ollama":
                base_url = "http://localhost:11434/v1"
                default_headers = None
            elif provider == "moonshot":
                base_url = "https://api.moonshot.cn/v1"
                default_headers = None
            elif provider == "deepseek":
                base_url = "https://api.deepseek.com/v1"
                default_headers = None
            else:
                base_url = None
                default_headers = None

            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL_NAME,
                api_key=settings.LLM_API_KEY,
                base_url=base_url,
                temperature=0.0, # Temp 0 para homogeneidad absoluta
                max_tokens=4000,
                default_headers=default_headers
            )

    def _extract_message_content(self, msg: Any) -> str:
        """Centraliza la extracción de texto de cualquier formato de LLM."""
        content = msg.content
        if isinstance(content, list):
            content = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in content])
        
        if not content and hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
            content = msg.additional_kwargs.get('reasoning', '') or \
                      msg.additional_kwargs.get('reasoning_content', '') or \
                      msg.additional_kwargs.get('thought', '') or \
                      str(msg.additional_kwargs)
            
        return str(content) if content else ""

    def _find_json(self, content: str) -> Optional[dict]:
        """Busca JSON en el contenido, incluso dentro de etiquetas de razonamiento."""
        if not content:
            return None
            
        # 1. Intentar parsear directamente
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass
            
        # 2. Buscar en bloques de código markdown
        match = re.search(r'```(?:json)?\s*([\{\[].*?[\}\]])\s*```', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
                
        # 3. Buscar el primer { o [ y el último } o ]
        match = re.search(r'[\{\[].*?[\}\]]', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0).strip())
            except json.JSONDecodeError:
                pass
                
        return None

    def _heuristic_filter(self, pinds: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
        filtered = []
        for p in pinds:
            if p.dependent.table_name == p.referenced.table_name:
                continue
            
            dep_name = p.dependent.column_name.lower()
            ref_name = p.referenced.column_name.lower()
            
            ref_table = p.referenced.table_name.lower()
            ref_table_singular = ref_table[:-1] if ref_table.endswith('s') else ref_table
            
            dep_table = p.dependent.table_name.lower()
            dep_table_singular = dep_table[:-1] if dep_table.endswith('s') else dep_table

            col_match = (dep_name in ref_name or ref_name in dep_name) and \
                        (len(dep_name) > 4 or len(ref_name) > 4 or dep_name == ref_name)

            table_match = (ref_table_singular in dep_name) or (ref_table in dep_name)
            table_match_inv = (dep_table_singular in ref_name) or (dep_table in ref_name)

            if col_match or table_match or table_match_inv:
                filtered.append(p)
                    
        return filtered

    async def _evaluate_batch(self, batch: List[PartialInclusionDependency], domain_profile: dict) -> List[PartialInclusionDependency]:
        pinds_text = "\n".join([
            f"{i+1}. ORIGEN: '{p.dependent.column_name}' (Tabla: {p.dependent.table_name}) -> DESTINO: '{p.referenced.column_name}' (Tabla: {p.referenced.table_name})"
            for i, p in enumerate(batch)
        ])

        rules_text = "\n".join([f"- {r}" for r in domain_profile.get("rules", [])])

        prompt = f"""
        Eres un auditor de bases de datos. Se han descubierto las siguientes relaciones matemáticas a ciegas.
        
        {pinds_text}
        
        REGLAS DE AUDITORÍA DEL DOMINIO:
        {rules_text}
        
        - Confía en la coincidencia matemática y léxica.
        - SOLO RECHAZA una relación si viola las reglas del dominio anteriores o si la DIRECCIÓN es absurda.
        
        Devuelve ÚNICAMENTE un json válido con el formato:
        {{"valid_indices": [1, 2, 3, ...]}}
        """

        for attempt in range(3):
            try:
                msg = await self.llm.ainvoke([
                    SystemMessage(content="Eres un experto en bases de datos. Devuelves respuestas estrictas en formato json."),
                    HumanMessage(content=prompt)
                ])
                
                raw_content = self._extract_message_content(msg)
                result = self._find_json(raw_content)
                
                if result is not None and "valid_indices" in result:
                    valid_indices = result["valid_indices"]
                    return [batch[i-1] for i in valid_indices if 0 < i <= len(batch)]
                
                logger.warning(f"Intento {attempt+1}: JSON no encontrado o inválido. Reintentando en 2s...")
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Intento {attempt+1}: Error de API ({str(e)[:50]}). Reintentando en 2s...")
                await asyncio.sleep(2)
                
        logger.error("El LLM falló después de 3 intentos. Aprobando lote por fallback matemático.")
        return batch

    def _remove_bidirectional_redundancy(self, pinds: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
        pair_map = {}
        for p in pinds:
            key = frozenset([p.dependent.table_name, p.referenced.table_name])
            if key not in pair_map:
                pair_map[key] = []
            pair_map[key].append(p)
            
        filtered = []
        for key, group in pair_map.items():
            if len(group) == 1:
                filtered.append(group[0])
            else:
                best_p = max(group, key=lambda x: x.total_count)
                filtered.append(best_p)
                
        logger.info(f"Filtro bidireccional aplicado: {len(pinds)} -> {len(filtered)} aristas finales.")
        return filtered

    async def validate_pinds(self, pinds: List[PartialInclusionDependency], domain_profile: dict) -> List[PartialInclusionDependency]:
        logger.info(f"Iniciando validación de {len(pinds)} pINDs...")
        
        if not pinds:
            return []

        smart_pinds = self._heuristic_filter(pinds)
        logger.info(f"Filtro heurístico aplicado: {len(pinds)} -> {len(smart_pinds)} pINDs candidatas.")

        chunk_size = 20
        chunks = [smart_pinds[i:i + chunk_size] for i in range(0, len(smart_pinds), chunk_size)]
        
        validated_pinds = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Procesando lote {i+1}/{len(chunks)}...")
            batch_result = await self._evaluate_batch(chunk, domain_profile)
            validated_pinds.extend(batch_result)
            
            if i < len(chunks) - 1:
                await asyncio.sleep(1)

        final_pinds = self._remove_bidirectional_redundancy(validated_pinds)
        logger.info(f"Validación completada. {len(final_pinds)} pINDs validadas en total.")
        return final_pinds

    async def generate_report(self, pinds: List[PartialInclusionDependency], emergence_index: float, is_emergence: bool, emergence_details: str = "", language: str = "es") -> str:
        table_names = set([p.dependent.table_name for p in pinds] + [p.referenced.table_name for p in pinds])
        pinds_str = "\n".join([f"- {p.dependent.table_name} se conecta con {p.referenced.table_name} ({p.semantic_label})" for p in pinds[:15]])
        
        lang_map = {"es": "Español", "en": "Inglés", "pt": "Português"}
        lang_name = lang_map.get(language, "Español")
        total_tables = len(table_names)
        
        if is_emergence:
            tone_directive = f"""
            ¡ALERTA CRÍTICA! Se ha detectado un Patrón Emergente Persistente. El sistema ha cambiado de régimen.
            
            DATOS MATEMÁTICOS EXACTOS DETECTADOS (Esta es tu ÚNICA fuente de verdad. NO inventes datos, métricas o tablas que no estén aquí):
            {emergence_details}
            
            Instrucciones de Redacción para Comité de Crisis (Usa este formato exacto y claro):
            0. 🎯 **Contexto del Dominio:** (Identifica el sector: salud, educación, ventas, etc., basándote en los nombres de las tablas. Usa su vocabulario específico).
            1. 🚨 **Nivel de Alerta:** (Confirma brevemente que se ha roto la línea base histórica y hay un nuevo régimen operativo).
            2. 🔍 **Interpretación del Patrón Emergente:** (Explica QUÉ acaba de ocurrir en lenguaje puramente de negocio. Si hay tablas nuevas, explica que "han surgido nuevas áreas o procesos operativos". Si hay deriva semántica, explica que "el comportamiento de los datos existentes ha cambiado radicalmente". Si hay un "Nexus", explica que "el impacto se centra en la relación entre [Tablas]").
            3. ⚠️ **Proyección de Riesgo:** (¿Qué le pasa a la institución en los próximos días si esto no se atiende?).
            4. ⚡ **Directivas Inmediatas:** (2 o 3 acciones concretas y ejecutivas para mitigar el riesgo).
            """
        else:
            tone_directive = f"""
            El sistema se encuentra ESTABLE. 
            Redacta un resumen ejecutivo muy breve, claro y tranquilizador usando el vocabulario del dominio.
            1. ✅ **Estado del Sistema:** (La operación está normal y bajo control).
            2. 🔍 **Monitoreo Activo:** (Se vigilan pasivamente {total_tables} estructuras de datos sin alteraciones).
            """

        prompt = f"""
        Eres el Director de Riesgos Estratégicos de una institución.
        Tu trabajo es traducir la evidencia matemática en un informe ejecutivo claro y directo para un comité de crisis no técnico.
        
        CONTEXTO DE DATOS VIGILADOS:
        Tablas detectadas: {', '.join(table_names)}
        Relaciones descubiertas:
        {pinds_str}
        
        DIRECTRIZ DE REDACCIÓN:
        {tone_directive}
        
        REGLAS ESTRICTAS E INQUEBRANTABLES:
        1. IDIOMA: Escribe TODO el informe estrictamente en {lang_name}.
        2. CLARIDAD Y CERO TECNICISMOS: Eres un traductor de matemáticas a negocio. Prohibido usar las palabras: "D_s", "D_m", "Nodos", "Grafo", "Anclaje Topológico", "Nexus", "Jensen-Shannon", "Laplaciano", "Autovalores", "Concept Drift" o cualquier término matemático. 
        3. CERO ALUCINACIONES: Menciona ÚNICAMENTE las tablas y eventos descritos en los "DATOS MATEMÁTICOS EXACTOS DETECTADOS". Si no hay tablas nuevas, no las menciones.
        """
        
        for attempt in range(3):
            try:
                msg = await self.llm.ainvoke([
                    SystemMessage(content=f"Eres un analista estratégico de élite. IDIOMA OBLIGATORIO: {lang_name}."),
                    HumanMessage(content=prompt)
                ])
                raw_content = self._extract_message_content(msg)
                content = re.sub(r'.*?', '', raw_content, flags=re.DOTALL).strip()
                if not content:
                    content = raw_content.replace('', '').replace('', '').strip()
                if content: return content
                logger.warning(f"Intento {attempt+1} (Reporte): Respuesta vacía. Reintentando en 2s...")
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"Intento {attempt+1} (Reporte): Error. Reintentando en 2s...")
                await asyncio.sleep(2)
        logger.error("El reporte falló después de 3 intentos.")
        return "Error: No se pudo generar el informe ejecutivo tras varios intentos."
    
    async def generate_ontology(self, pinds: List[PartialInclusionDependency], domain_profile: dict) -> List[PartialInclusionDependency]:
        if not pinds: return []
        pinds_text = "\n".join([f"{i+1}. {p.dependent.table_name}.{p.dependent.column_name} -> {p.referenced.table_name}.{p.referenced.column_name}" for i, p in enumerate(pinds)])
        verbs_text = ", ".join(domain_profile.get("verbs", []))
        context_text = domain_profile.get("context", "Sistema de información general.")
        prompt = f"""
        Eres un ontólogo experto. Analiza las siguientes relaciones descubiertas en una base de datos e infiere el VERBO (EN INGLÉS, MAYÚSCULAS y sin espacios, ex: BELONGS_TO).
        Contexto del dominio: {context_text}
        Verbos sugeridos para este dominio: {verbs_text}
        Relaciones a evaluar:
        {pinds_text}
        Devuelve ÚNICAMENTE un JSON válido con el formato:
        {{"ontology": [{{"index": 1, "label": "VERBO_INFERIDO"}}, ...]}}
        """
        for attempt in range(3):
            try:
                msg = await self.llm.ainvoke([SystemMessage(content="Eres un experto en modelado ontológico. Devuelves JSON estricto."), HumanMessage(content=prompt)])
                raw_content = self._extract_message_content(msg)
                result = self._find_json(raw_content)
                if result is not None and "ontology" in result:
                    for item in result["ontology"]:
                        idx = item.get("index"); label = item.get("label", "REFERENCES")
                        if idx and 0 < idx <= len(pinds): pinds[idx-1].semantic_label = label.upper()
                    logger.info(f"Ontología emergente generada para {len(pinds)} relaciones.")
                    return pinds
                logger.warning(f"Intento {attempt+1} (Ontología): JSON no encontrado. Reintentando en 2s...")
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"Intento {attempt+1} (Ontología): Error. Reintentando en 2s...")
                await asyncio.sleep(2)
        logger.error("Ontología falló después de 3 intentos. Usando REFERENCES por defecto.")
        return pinds