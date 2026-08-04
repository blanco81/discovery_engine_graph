# app/adapters/db/sqlalchemy_adapter.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import inspect, text
from typing import List
import logging

from app.core.domain.models import Column, PartialInclusionDependency
from app.core.ports.relational_port import RelationalPort

logger = logging.getLogger(__name__)

class SqlAlchemyAdapter(RelationalPort):
    def __init__(self, db_url: str):
        # Traducir URLs estándar a URLs asíncronas automáticamente
        if db_url.startswith("postgresql://"):
            self.db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("mysql://") or db_url.startswith("mysql+pymysql://"):
            self.db_url = db_url.replace("mysql://", "mysql+aiomysql://", 1).replace("mysql+pymysql://", "mysql+aiomysql://", 1)
        elif db_url.startswith("sqlite:///"):
            self.db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        else:
            self.db_url = db_url
            
        self.engine: AsyncEngine = None

    async def connect(self) -> None:
        logger.info(f"Intentando conexión asíncrona al RDBMS...")
        try:
            self.engine = create_async_engine(self.db_url)
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Conexión exitosa.")
        except Exception as e:
            logger.error(f"Error de conexión: {e}")
            raise ConnectionError(f"No se pudo conectar: {e}")

    async def disconnect(self) -> None:
        if self.engine:
            await self.engine.dispose()
            logger.info("Conexión cerrada.")

    async def get_all_columns(self) -> List[Column]:
        if not self.engine:
            raise ConnectionError("No hay conexión.")
        
        columns = []
        # Usamos run_sync para usar el inspector de SQLAlchemy que aún es síncrono
        async with self.engine.connect() as conn:
            def get_tables(sync_conn):
                insp = inspect(sync_conn)
                return insp.get_table_names()
            
            table_names = await conn.run_sync(get_tables)
            
            for table_name in table_names:
                def get_cols(sync_conn, t_name=table_name):
                    insp = inspect(sync_conn)
                    return insp.get_columns(t_name)
                
                cols_info = await conn.run_sync(get_cols)
                for column_info in cols_info:
                    col = Column(
                        table_name=table_name,
                        column_name=column_info['name'],
                        data_type=str(column_info['type'])
                    )
                    columns.append(col)
                
        logger.info(f"Esquema inferido a ciegas: {len(columns)} columnas encontradas.")
        return columns

    async def discover_pinds(self, columns: List[Column], rho_threshold: float = 0.95) -> List[PartialInclusionDependency]:
        pinds = []
        valid_types = ['VARCHAR', 'TEXT', 'INTEGER', 'BIGINT', 'CHAR', 'UUID', 'SERIAL']
        candidate_cols = [c for c in columns if any(vt in c.data_type.upper() for vt in valid_types)]

        logger.info(f"Iniciando descubrimiento de pINDs sobre {len(candidate_cols)} columnas candidatas...")

        for col_x in candidate_cols:
            for col_y in candidate_cols:
                if col_x.table_name == col_y.table_name and col_x.column_name == col_y.column_name:
                    continue
                
                try:
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

                    async with self.engine.connect() as conn:
                        result_match = await conn.execute(query_match)
                        result_total = await conn.execute(query_total)
                        
                        match_count = result_match.scalar()
                        total_count = result_total.scalar()

                    if total_count and total_count > 0:
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
                            
                except Exception:
                    continue
                    
        logger.info(f"Descubrimiento completado. {len(pinds)} pINDs encontradas.")
        return pinds

    async def get_categorical_distributions(self, columns: List[Column], sample_size: int = 1000) -> Dict[str, Dict[str, float]]:
        """
        Extrae la distribución de probabilidad de las columnas categóricas (TEXT/VARCHAR).
        """
        distributions = {}
        cat_cols = [c for c in columns if 'VARCHAR' in c.data_type.upper() or 'TEXT' in c.data_type.upper()]
        
        for col in cat_cols:
            try:
                query = text(f"""
                    SELECT "{col.column_name}", COUNT(*) as freq
                    FROM "{col.table_name}"
                    WHERE "{col.column_name}" IS NOT NULL
                    GROUP BY "{col.column_name}"
                    LIMIT {sample_size}
                """)
                async with self.engine.connect() as conn:
                    result = await conn.execute(query)
                    rows = result.fetchall()
                
                if rows:
                    total = sum([row[1] for row in rows])
                    if total > 0:
                        # Formato: { "categoria": probabilidad }
                        dist = {str(row[0]): row[1] / total for row in rows}
                        distributions[f"{col.table_name}.{col.column_name}"] = dist
            except Exception:
                continue
                
        logger.info(f"Distribuciones semánticas extraídas para {len(distributions)} columnas categóricas.")
        return distributions