# core/ports/graph_port.py
from abc import ABC, abstractmethod
from typing import List
from app.core.domain.models import PartialInclusionDependency
import networkx as nx

class GraphPort(ABC):
    """
    Puerto para la persistencia y consulta del Grafo Dinámico (Fase B).
    """

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def save_pinds(self, pinds: List[PartialInclusionDependency]) -> None:
        """Guarda las pINDs como nodos y aristas en el grafo."""
        pass

    @abstractmethod
    def get_networkx_graph(self) -> nx.DiGraph:
        """Extrae el grafo actual a un objeto NetworkX para cálculos matemáticos."""
        pass