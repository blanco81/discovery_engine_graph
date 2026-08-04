# app/adapters/agents/langgraph_adapter.py
from typing import List
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
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
        
        # Si es Hugging Face, usamos ChatHuggingFace
        if provider == "huggingface":
            llm_endpoint = HuggingFaceEndpoint(
                repo_id=settings.LLM_MODEL_NAME,
                huggingfacehub_api_token=settings.LLM_API_KEY,
                temperature=0.1,
                max_new_tokens=2000,
                task="text-generation"
            )
            self.llm = ChatHuggingFace(llm=llm_endpoint)
        
        # Para Groq, OpenRouter, Ollama o Moonshot nativo, usamos ChatOpenAI
        else:
            if provider == "groq":
                base_url = "https://api.groq.com/openai/v1"
            elif provider == "openrouter":
                base_url = "https://openrouter.ai/api/v1"
            elif provider == "ollama":
                base_url = "http://localhost:11434/v1"
            elif provider == "moonshot":
                base_url = "https://api.moonshot.cn/v1"
            else:
                base_url = None

            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL_NAME,
                api_key=settings.LLM_API_KEY,
                base_url=base_url,
                temperature=0.1
            )

    def _heuristic_filter(self, pinds: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
        """
        Filtro previo heurístico y léxico avanzado.
        Combina similitud entre columnas y similitud columna-tabla.
        """
        filtered = []
        for p in pinds:
            # Regla 1: Ignorar relaciones de una tabla consigo misma
            if p.dependent.table_name == p.referenced.table_name:
                continue
            
            dep_name = p.dependent.column_name.lower()
            ref_name = p.referenced.column_name.lower()
            
            # Obtenemos el nombre de la tabla destino y lo "singularizamos" básicamente
            ref_table = p.referenced.table_name.lower()
            ref_table_singular = ref_table[:-1] if ref_table.endswith('s') else ref_table
            
            dep_table = p.dependent.table_name.lower()
            dep_table_singular = dep_table[:-1] if dep_table.endswith('s') else dep_table

            # Regla 2: Similitud Léxica Directa (Columna vs Columna)
            # Ej: 'card_id' está dentro de 'active_card_id'
            col_match = (dep_name in ref_name or ref_name in dep_name) and \
                        (len(dep_name) > 4 or len(ref_name) > 4 or dep_name == ref_name)

            # Regla 3: Similitud Estructural (Columna Origen vs Tabla Destino)
            # Ej: dep_name='patient_id', ref_table_singular='patient'
            # Ej: dep_name='bldg_id', ref_table='buildings' -> ref_table_singular='building' (fallaría, pero bldg no es building)
            table_match = (ref_table_singular in dep_name) or (ref_table in dep_name)
            
            # Regla 4: Similitud Estructural Inversa (Columna Destino vs Tabla Origen)
            # Ej: ref_name='student_id', dep_table='students'
            table_match_inv = (dep_table_singular in ref_name) or (dep_table in ref_name)

            # Si pasa alguna de las reglas léxicas/estructurales, se envía al LLM
            if col_match or table_match or table_match_inv:
                filtered.append(p)
                    
        return filtered

    async def _evaluate_batch(self, batch: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
        """Evalúa un lote pequeño de pINDs usando el LLM."""
        pinds_text = "\n".join([
            f"{i+1}. ORIGEN: '{p.dependent.column_name}' (Tabla: {p.dependent.table_name}) -> DESTINO: '{p.referenced.column_name}' (Tabla: {p.referenced.table_name})"
            for i, p in enumerate(batch)
        ])

        prompt = f"""
        Eres un auditor de bases de datos. Se han descubierto las siguientes relaciones matemáticas a ciegas que ya pasaron un filtro léxico estricto (los nombres de las columnas coinciden).
        
        {pinds_text}
        
        REGLA DE AUDITORÍA:
        - Confía en la coincidencia matemática y léxica.
        - SOLO RECHAZA una relación si la DIRECCIÓN es claramente absurda (Ej: 'buildings.bldg_id' -> 'rooms.room_id' está invertido, debería ser al revés).
        - No rechaces relaciones solo por falta de contexto.
        
        Devuelve ÚNICAMENTE un json válido con el formato:
        {{"valid_indices": [1, 2, 3, ...]}}
        Donde los números correspondan a los índices de TODAS las relaciones que no están invertidas.
        """

        try:
            # Aplicamos el modo JSON solo a esta llamada específica usando .bind()
            json_llm = self.llm.bind(response_format={"type": "json_object"})
            
            msg = await json_llm.ainvoke([
                SystemMessage(content="Eres un experto en bases de datos. Devuelves respuestas estrictas en formato json."),
                HumanMessage(content=prompt)
            ])
            
            # Doble seguridad: Limpiar markdown y usar Regex para extraer el JSON
            content = msg.content.strip().replace("```json", "").replace("```", "")
            
            # Buscar el primer '{' y el último '}' para aislar el JSON por si acaso
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if not match:
                logger.error(f"No se encontró JSON en la respuesta del LLM: {content[:100]}")
                return []
                
            json_str = match.group(0)
            result = json.loads(json_str)
            valid_indices = result.get("valid_indices", [])
            
            # Mapear índices a los objetos pIND originales
            return [batch[i-1] for i in valid_indices if 0 < i <= len(batch)]
            
        except json.JSONDecodeError:
            logger.error("El LLM no devolvió un JSON válido en el lote. Descartando lote.")
            return []
        except Exception as e:
            logger.error(f"Error evaluando lote: {e}")
            return []
    def _remove_bidirectional_redundancy(self, pinds: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
        """
        Filtra relaciones bidireccionales conservando solo la direccionalidad lógica.
        Regla: La tabla con más filas (transaccional) apunta a la tabla con menos filas (maestra).
        """
        # Agrupar las relaciones por par de tablas (ignorando la dirección por un momento)
        pair_map = {}
        for p in pinds:
            key = frozenset([p.dependent.table_name, p.referenced.table_name])
            if key not in pair_map:
                pair_map[key] = []
            pair_map[key].append(p)
            
        filtered = []
        for key, group in pair_map.items():
            if len(group) == 1:
                # Solo hay una dirección, la conservamos
                filtered.append(group[0])
            else:
                # Hay bidireccionalidad. Nos quedamos con la que tenga mayor total_count en el origen
                # (ej. access_logs.total_count=200 > rooms.total_count=20)
                best_p = max(group, key=lambda x: x.total_count)
                filtered.append(best_p)
                
        logger.info(f"Filtro bidireccional aplicado: {len(pinds)} -> {len(filtered)} aristas finales.")
        return filtered

    async def validate_pinds(self, pinds: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
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
            batch_result = await self._evaluate_batch(chunk)
            validated_pinds.extend(batch_result)
            
            if i < len(chunks) - 1:
                await asyncio.sleep(1)

        # NUEVO FILTRO: Eliminar bidireccionalidad redundante
        final_pinds = self._remove_bidirectional_redundancy(validated_pinds)
        
        logger.info(f"Validación completada. {len(final_pinds)} pINDs validadas en total.")
        return final_pinds

    async def generate_report(self, pinds: List[PartialInclusionDependency], emergence_index: float, is_emergence: bool, emergence_details: str = "") -> str:
        # En lugar de mostrar la matemática cruda, la traducimos a conceptos de riesgo
        if is_emergence:
            tone_directive = f"""
            ¡ALERTA CRÍTICA DE NEGOCIO! Se ha detectado un Patrón Emergente Persistente.
            El sistema ha cambiado de régimen. El tono debe ser de alerta temprana para directivos.
            
            Evidencia Interna (TRADÚCELA a lenguaje de negocio, NO uses términos matemáticos):
            {emergence_details}
            
            Instrucciones de Redacción OBLIGATORIAS (Usa este formato exacto):
            1. 🚨 **Estado del Sistema:** (1 frase indicando alerta de cambio operativo).
            2. 🔍 **Hallazgo Principal:** (Explica en español simple qué surgió. Si hay 'Nodos Nuevos', diles que apareció una nueva área de negocio/proceso. Si hay 'Alerta Semántica', diles que el comportamiento de los datos existentes mutó drásticamente, como un brote o una falla masiva).
            3. 🏢 **Impacto en la Operación:** (Basado en los nombres de las tablas, explica cómo afecta esto a la vida real: estudiantes, pacientes, recursos, etc.).
            4. 📋 **Recomendación Inmediata:** (1 o 2 acciones concretas que el gerente debería hacer hoy).
            """
        else:
            tone_directive = """
            El sistema se encuentra ESTABLE. 
            Redacta un resumen ejecutivo corto y tranquilizador.
            1. ✅ **Estado del Sistema:** (Indica que la operación está normal).
            2. 🔍 **Monitoreo Activo:** (Menciona brevemente cuántas estructuras de datos se están vigilando).
            """

        # Simplificamos la lista de relaciones para que el LLM no se enrede
        pinds_str = "\n".join([f"- {p.dependent.table_name} se conecta con {p.referenced.table_name}" for p in pinds[:10]])
        
        prompt = f"""
        Eres el Analista Principal de Inteligencia de Datos para un Directorio Ejecutivo.
        Tu trabajo es traducir descubrimientos técnicos en informes pragmáticos de 1 página.
        
        Contexto de Datos Vigilados:
        {pinds_str}
        
        Directriz de Redacción:
        {tone_directive}
        
        NO menciones índices matemáticos, ni Jensen-Shannon, ni autovalores, ni pINDs. Habla de "procesos", "comportamiento de datos" y "áreas de negocio".
        """
        
        msg = await self.llm.ainvoke([
            SystemMessage(content="Eres un Chief Data Officer redactando un informe ejecutivo pragmático."),
            HumanMessage(content=prompt)
        ])
        return msg.content
    
    async def generate_ontology(self, pinds: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
        """Pide al LLM que asigne un verbo semántico a cada relación validada."""
        if not pinds:
            return []

        pinds_text = "\n".join([
            f"{i+1}. {p.dependent.table_name}.{p.dependent.column_name} -> {p.referenced.table_name}.{p.referenced.column_name}"
            for i, p in enumerate(pinds)
        ])

        prompt = f"""
        Eres un ontólogo experto. Analiza las siguientes relaciones descubiertas en una base de datos e infiere el VERBO que mejor represente la relación semántica de negocio (en INGLÉS, EN MAYÚSCULAS y sin espacios, ej: BELONGS_TO).
        
        Ejemplos de inferencia:
        - patients.doctor_id -> doctors.id : TREATED_BY
        - rooms.bldg_id -> buildings.bldg_id : LOCATED_IN
        - students.active_card_id -> rfid_cards.card_id : OWNS
        - sensor_readings.sensor_id -> sensors.sensor_id : GENERATED_BY
        - transactions.account_id -> accounts.id : BELONGS_TO
        
        Relaciones a evaluar:
        {pinds_text}
        
        Devuelve ÚNICAMENTE un JSON válido con el formato:
        {{"ontology": [{{"index": 1, "label": "VERBO_INFERIDO"}}, ...]}}
        """

        try:
            json_llm = self.llm.bind(response_format={"type": "json_object"})
            msg = await json_llm.ainvoke([
                SystemMessage(content="Eres un experto en modelado ontológico. Devuelves JSON estricto."),
                HumanMessage(content=prompt)
            ])
            
            content = msg.content.strip().replace("```json", "").replace("```", "")
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if not match:
                logger.error("No se encontró JSON en la respuesta ontológica.")
                return pinds # Devolvemos las originales con "REFERENCES"
                
            result = json.loads(match.group(0))
            ontology_mappings = result.get("ontology", [])
            
            # Actualizar el campo semantic_label en los objetos pIND
            for item in ontology_mappings:
                idx = item.get("index")
                label = item.get("label", "REFERENCES")
                if idx and 0 < idx <= len(pinds):
                    pinds[idx-1].semantic_label = label.upper()
            
            logger.info(f"Ontología emergente generada para {len(pinds)} relaciones.")
            return pinds
            
        except Exception as e:
            logger.error(f"Error generando ontología: {e}")
            return pinds # Si falla, usamos REFERENCES