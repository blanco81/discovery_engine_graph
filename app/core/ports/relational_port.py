# core/ports/relational_port.py
from abc import ABC, abstractmethod
from typing import List
from app.core.domain.models import Column, PartialInclusionDependency

class RelationalPort(ABC):
    """
    Puerto del Pozo Relacional (Fase A).
    Define las operaciones para inspeccionar la base de datos a ciegas.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establece conexión con el RDBMS."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Cierra la conexión."""
        pass

    @abstractmethod
    def get_all_columns(self) -> List[Column]:
        """Inspecciona el esquema a ciegas y devuelve todas las columnas disponibles."""
        pass

    @abstractmethod
    def discover_pinds(self, columns: List[Column], rho_threshold: float = 0.95) -> List[PartialInclusionDependency]:
        """
        Descubre Dependencias de Inclusión Parciales (pINDs).
        """
        pass