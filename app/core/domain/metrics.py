# core/domain/metrics.py
import networkx as nx
import numpy as np
from scipy.stats import skew, kurtosis

def calculate_netsimile(graph: nx.Graph) -> np.ndarray:
    """
    Calcula el vector de firma estructural NetSimile (Fs) para un grafo dado.
    """
    features = []
    
    for node in graph.nodes():
        # 1. Grado de salida e entrada
        in_deg = graph.in_degree(node) if isinstance(graph, nx.DiGraph) else graph.degree(node)
        out_deg = graph.out_degree(node) if isinstance(graph, nx.DiGraph) else 0
        
        # 2. Coeficiente de clustering local
        clustering = nx.clustering(graph.to_undirected(), node)
        
        # 3. Número de vecinos de segundo orden
        neighbors = set(nx.all_neighbors(graph.to_undirected(), node))
        second_neighbors = set()
        for n in neighbors:
            second_neighbors.update(nx.all_neighbors(graph.to_undirected(), n))
        second_neighbors.discard(node)
        second_neighbors.difference_update(neighbors)
        sn_count = len(second_neighbors)
        
        # Agregar características del nodo
        features.append([in_deg, out_deg, clustering, sn_count])
    
    # Convertir a array numpy para cálculo estadístico
    features_array = np.array(features)
    
    # Agregar estadísticas: media, mediana, std, asimetría (skew), curtosis
    # Esto produce un vector size-independent (NetSimile signature)
    signature = []
    for i in range(features_array.shape[1]):
        col = features_array[:, i]
        signature.extend([
            np.mean(col),
            np.median(col),
            np.std(col),
            skew(col),
            kurtosis(col)
        ])
        
    return np.array(signature)