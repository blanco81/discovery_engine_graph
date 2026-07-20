# app/core/ports/orchestrator_port.py
from abc import ABC, abstractmethod
from typing import List
from app.core.domain.models import PartialInclusionDependency

class OrchestratorPort(ABC):
    """
    Puerto para la orquestación multi-agente (Fase B y C).
    """
    @abstractmethod
    def validate_pinds(self, pinds: List[PartialInclusionDependency]) -> List[PartialInclusionDependency]:
        """Filtra y valida las pINDs mediante debate de agentes."""
        pass

    @abstractmethod
    def generate_report(self, pinds: List[PartialInclusionDependency], emergence_index: float, is_emergence: bool) -> str:
        """Genera un informe en lenguaje natural a partir del linaje matemático."""
        pass