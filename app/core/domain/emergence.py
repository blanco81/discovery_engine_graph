# app/core/domain/emergence.py
import networkx as nx
import numpy as np
from typing import List, Tuple

class EmergenceEngine:
    """
    Motor matemático para detectar Patrones Emergentes Persistentes (Pilar 3).
    Basado en teoría espectral y persistencia temporal (Wolfram/Bar-Yam).
    """

    def calculate_spectral_signature(self, graph: nx.Graph, k: int = 5) -> np.ndarray:
        """
        Calcula la firma espectral del grafo usando los primeros k autovalores 
        del Laplaciano. Esto captura la estructura de comunidades y conectividad global.
        """
        # Asegurar que el grafo sea no dirigido para el cálculo del Laplaciano
        undirected_g = graph.to_undirected()
        
        # Calcular autovalores del Laplaciano
        eigenvalues = nx.laplacian_spectrum(undirected_g, weight='weight')
        
        # Tomar los k autovalores más pequeños (excluyendo el 0 que es trivial)
        # Esto representa la estructura macroscópica del grafo
        non_zero_eigenvalues = np.sort(eigenvalues[eigenvalues > 1e-10])
        
        # Rellenar con ceros si el grafo es muy pequeño y no hay suficientes autovalores
        signature = np.zeros(k)
        length = min(len(non_zero_eigenvalues), k)
        signature[:length] = non_zero_eigenvalues[:length]
        
        return signature

    def calculate_emergence_index(self, current_sig: np.ndarray, historical_sig: np.ndarray) -> float:
        """
        Calcula el Índice de Emergencia E(P,t).
        Usamos la distancia L2 (Euclidiana) entre el espectro actual y el histórico.
        """
        # En una implementación completa, aquí se sumarían D_s, D_m, D_t, D_g
        # Por ahora, nos enfocamos en la desviación estructural espectral (D_s)
        ds = np.linalg.norm(current_sig - historical_sig)
        
        # Normalizamos el índice para que esté entre 0 y 1 aprox
        # (Añadiendo un pequeño épsilon para evitar división por cero)
        normalized_ds = ds / (np.linalg.norm(historical_sig) + 1e-10)
        
        return normalized_ds

    def validate_persistence(self, emergence_history: List[float], threshold: float = 0.15, window: int = 3) -> bool:
        """
        Valida si una emergencia es persistente en el tiempo.
        Requerimiento de Pilar 3: No es una anomalía puntual, es un cambio de régimen.
        
        - emergence_history: Lista de índices E(P,t) en pasos de tiempo anteriores.
        - threshold: Umbral θ para considerar que hay una desviación significativa.
        - window: Número de pasos de tiempo consecutivos que debe mantenerse.
        """
        if len(emergence_history) < window:
            return False
            
        # Tomamos los últimos 'window' pasos
        recent_history = emergence_history[-window:]
        
        # Condición 1: Todos los pasos recientes deben superar el umbral
        all_above_threshold = all(e > threshold for e in recent_history)
        
        # Condición 2: Coherencia modal (la desviación no debe oscilar locamente)
        # Calculamos la varianza de los últimos pasos; si es muy alta, es ruido, no emergencia.
        variance = np.var(recent_history)
        is_stable = variance < (threshold * 0.5) # La varianza debe ser menor que la mitad del umbral
        
        return all_above_threshold and is_stable