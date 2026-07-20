# core/domain/models.py
from dataclasses import dataclass
from typing import List

@dataclass
class Column:
    """Representación de una columna inferida a ciegas."""
    table_name: str
    column_name: str
    data_type: str

    def __repr__(self):
        return f"{self.table_name}.{self.column_name}"

@dataclass
class PartialInclusionDependency:
    """
    Representa una pIND: r1[X] ⊆_ρ r2[Y]
    Define una arista dirigida probabilística en nuestro futuro grafo.
    """
    dependent: Column          # X (La columna que apunta)
    referenced: Column         # Y (La columna referenciada)
    rho: float                 # Umbral de solapamiento (0, 1]
    violation_count: int       # Número de tuplas que violan la inclusión
    total_count: int           # Total de tuplas evaluadas

    def __repr__(self):
        return f"{self.dependent} ⊆_{self.rho:.2f} {self.referenced}"

@dataclass
class DynamicProfile:
    """
    Perfil Dinámico P(t) = {A(t), R(t), E(t), L(t)}
    En esta etapa inicial, modelamos Atributos y Relaciones.
    """
    attributes: List[Column]
    relationships: List[PartialInclusionDependency]