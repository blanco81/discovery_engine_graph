# app/core/domain/emergence.py
import networkx as nx
import numpy as np
from typing import List, Tuple
import json
import os
import logging

logger = logging.getLogger(__name__)

STATE_FILE = "system_state.json"

class EmergenceEngine:
    """
    Motor matemático para detectar Patrones Emergentes Persistentes (Pilar 3).
    Basado en teoría espectral, persistencia temporal y Control Estadístico de Procesos (SPC).
    """

    def calculate_spectral_signature(self, graph: nx.Graph, k: int = 8) -> List[float]:
        """
        Calcula la firma espectral del grafo usando los primeros k autovalores 
        del Laplaciano, INCLUYENDO los ceros. 
        Los autovalores en 0 representan componentes desconectados (islas).
        """
        undirected_g = graph.to_undirected()
        
        # Calcular autovalores del Laplaciano
        eigenvalues = nx.laplacian_spectrum(undirected_g, weight='weight')
        
        # Ordenar TODOS los autovalores, INCLUYENDO los ceros
        sorted_eigenvalues = np.sort(eigenvalues)
        
        # Tomar los primeros k autovalores (ahora incluimos los ceros)
        signature = np.zeros(k)
        length = min(len(sorted_eigenvalues), k)
        signature[:length] = sorted_eigenvalues[:length]
        
        # Devolver como lista nativa de Python
        return signature.tolist()

    def calculate_emergence_index(self, current_sig: List[float], historical_sig: List[float]) -> float:
        """
        Calcula el Índice de Emergencia E(P,t).
        Usamos la distancia L2 (Euclidiana) entre el espectro actual y el histórico.
        """
        current_np = np.array(current_sig)
        historical_np = np.array(historical_sig)
        
        ds = np.linalg.norm(current_np - historical_np)
        normalized_ds = ds / (np.linalg.norm(historical_np) + 1e-10)
        
        return float(normalized_ds)

    def calculate_adaptive_threshold(self, history: List[float], window: int = 3, warmup: int = 5) -> float:
        """
        Calcula el Umbral Adaptativo (theta_adaptive) basado en Control Estadístico de Procesos.
        Fórmula: mu + k * sigma (Regla de los 3 sigmas).
        Excluye la ventana actual para no sesgar el ruido de fondo con la anomalía presente.
        """
        # Excluimos las últimas 'window' iteraciones para calcular el ruido de fondo
        baseline_history = history[:-window] if len(history) > window else history
        
        if len(baseline_history) < warmup:
            # Si no hay suficiente historial (fase de calentamiento), usamos un umbral fijo base
            return 0.15
        
        history_np = np.array(baseline_history)
        mu = np.mean(history_np)
        sigma = np.std(history_np)
        
        # k = 3.0 (Regla de 3 sigmas). Si sigma es 0, usamos un piso mínimo de 0.001
        adaptive_theta = mu + 3.0 * sigma if sigma > 0 else 0.001
        return float(adaptive_theta)

    def validate_persistence(self, emergence_history: List[float], threshold: float, window: int = 3) -> bool:
        """
        Valida si una emergencia es persistente en el tiempo.
        Requerimiento de Pilar 3: No es una anomalía puntual, es un cambio de régimen.
        """
        if len(emergence_history) < window:
            return False
            
        recent_history = emergence_history[-window:]
        
        # Condición 1: Todos los pasos recientes deben superar el umbral (que ahora es adaptativo)
        all_above_threshold = all(e > threshold for e in recent_history)
        
        # Condición 2: Coherencia modal (Baja varianza reciente)
        variance = np.var(recent_history)
        is_stable = variance < (threshold * 0.5)
        
        # Forzamos la conversión a bool nativo de Python para que FastAPI pueda serializarlo
        return bool(all_above_threshold and is_stable)

    # --- Métodos de persistencia en JSON (Legacy/Fallback) ---
    def save_state(self, baseline_sig: List[float], history: List[float], baseline_nodes: List[str] = None, baseline_edges: List[Tuple[str, str]] = None, baseline_semantics: dict = None):
        """Guarda la línea base, el historial, la topología y la semántica en un JSON."""
        with open(STATE_FILE, 'w') as f:
            json.dump({
                "baseline_sig": baseline_sig, 
                "history": history,
                "baseline_nodes": baseline_nodes or [],
                "baseline_edges": baseline_edges or [],
                "baseline_semantics": baseline_semantics or {}
            }, f)
        logger.info("Estado del sistema (estructural y semántico) guardado.")

    def load_state(self) -> Tuple[List[float], List[float], List[str], List[Tuple[str, str]], dict]:
        """Carga el estado completo. Si no existe, devuelve listas/vacios."""
        if not os.path.exists(STATE_FILE):
            return [], [], [], [], {}
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            return (
                data.get("baseline_sig", []), 
                data.get("history", []), 
                data.get("baseline_nodes", []), 
                data.get("baseline_edges", []),
                data.get("baseline_semantics", {})
            )