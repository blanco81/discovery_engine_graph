# adapters/db/sqlalchemy_adapter.py
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from typing import List
import logging

from app.core.domain.models import Column, PartialInclusionDependency
from app.core.ports.relational_port import RelationalPort
from app.config.config import settings

logger = logging.getLogger(__name__)

class SqlAlchemyAdapter(RelationalPort):
    """
    Adaptador que implementa RelationalPort usando SQLAlchemy.
    Realiza la conexión a ciegas y descubre pINDs mediante consultas de conteo.
    """

    def __init__(self):
        self.engine: Engine = None

    def connect(self) -> None:
        logger.info(f"Conectando a ciegas al RDBMS: {settings.RDBMS_URL}")
        self.engine = create_engine(settings.RDBMS_URL)
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexión exitosa.")

    def disconnect(self) -> None:
        if self.engine:
            self.engine.dispose()
            logger.info("Conexión cerrada.")

    def get_all_columns(self) -> List[Column]:
        """Usa inspect() de SQLAlchemy para leer el esquema sin modelos ORM."""
        if not self.engine:
            raise ConnectionError("No hay conexión a la base de datos.")
        
        inspector = inspect(self.engine)
        columns = []
        
        for table_name in inspector.get_table_names():
            for column_info in inspector.get_columns(table_name):
                col = Column(
                    table_name=table_name,
                    column_name=column_info['name'],
                    data_type=str(column_info['type'])
                )
                columns.append(col)
                
        logger.info(f"Esquema inferido a ciegas: {len(columns)} columnas encontradas.")
        return columns

    def discover_pinds(self, columns: List[Column], rho_threshold: float = 0.95) -> List[PartialInclusionDependency]:
        """
        Implementación de descubrimiento de pINDs.
        Para cada par (X, Y), calcula: rho = count(X IN Y) / count(X)
        Si rho >= umbral, se registra como una arista probabilística.
        """
        pinds = []
        
        # Filtrar tipos de datos válidos para evitar comparar fechas con textos, etc.
        valid_types = ['VARCHAR', 'TEXT', 'INTEGER', 'BIGINT', 'CHAR', 'UUID']
        candidate_cols = [c for c in columns if any(vt in c.data_type.upper() for vt in valid_types)]

        logger.info(f"Iniciando descubrimiento de pINDs sobre {len(candidate_cols)} columnas candidatas...")

        for col_x in candidate_cols:
            for col_y in candidate_cols:
                # Evitar auto-referencias básicas
                if col_x.table_name == col_y.table_name and col_x.column_name == col_y.column_name:
                    continue
                
                try:
                    # Consultas SQL para calcular el solapamiento (duplicate-aware)
                    query_match = text(f"""
                        SELECT COUNT(*) FROM "{col_x.table_name}" t1 
                        WHERE t1."{col_x.column_name}" IS NOT NULL 
                        AND EXISTS (
                            SELECT 1 FROM "{col_y.table_name}" t2 
                            WHERE t2."{col_y.column_name}" = t1."{col_x.column_name}"
                        )
                    """)
                    
                    query_total = text(f"""
                        SELECT COUNT(*) FROM "{col_x.table_name}" 
                        WHERE "{col_x.column_name}" IS NOT NULL
                    """)

                    with self.engine.connect() as conn:
                        match_count = conn.execute(query_match).scalar()
                        total_count = conn.execute(query_total).scalar()

                    if total_count > 0:
                        rho = match_count / total_count
                        violations = total_count - match_count
                        
                        if rho >= rho_threshold:
                            pind = PartialInclusionDependency(
                                dependent=col_x,
                                referenced=col_y,
                                rho=round(rho, 4),
                                violation_count=violations,
                                total_count=total_count
                            )
                            pinds.append(pind)
                            
                except Exception as e:
                    # Silenciar errores de tipo de dato incompatible en SQL y continuar
                    continue
                    
        logger.info(f"Descubrimiento completado. {len(pinds)} pINDs encontradas con ρ >= {rho_threshold}.")
        return pinds