# app/adapters/db/state_adapter.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text
import logging
from typing import Tuple, List, Dict
import json

logger = logging.getLogger(__name__)

class InternalStateAdapter:
    """Gestiona el estado del motor en una Metabase interna (SQLite)."""
    
    def __init__(self):
        self.engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///./engine_internal.db")

    async def init_db(self):
        """Crea la tabla de estado si no existe, añadiendo la columna needs_reset."""
        async with self.engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS engine_baselines (
                    source_db_url TEXT PRIMARY KEY,
                    baseline_sig TEXT,
                    history TEXT,
                    baseline_nodes TEXT,
                    baseline_edges TEXT,
                    baseline_semantics TEXT,
                    needs_reset INTEGER DEFAULT 0
                )
            """))
            # Añadir la columna si la base de datos ya existía de versiones anteriores
            try:
                await conn.execute(text("ALTER TABLE engine_baselines ADD COLUMN needs_reset INTEGER DEFAULT 0"))
            except:
                pass # Ya existe la columna

    async def save_state(self, source_db_url: str, baseline_sig: List[float], history: List[float], baseline_nodes: List[str], baseline_edges: List, baseline_semantics: Dict, needs_reset: int = 0):
        async with self.engine.begin() as conn:
            await conn.execute(text("""
                INSERT INTO engine_baselines (source_db_url, baseline_sig, history, baseline_nodes, baseline_edges, baseline_semantics, needs_reset)
                VALUES (:url, :sig, :hist, :nodes, :edges, :sem, :nr)
                ON CONFLICT(source_db_url) DO UPDATE SET 
                    baseline_sig=:sig, history=:hist, baseline_nodes=:nodes, 
                    baseline_edges=:edges, baseline_semantics=:sem, needs_reset=:nr
            """), {
                "url": source_db_url,
                "sig": json.dumps(baseline_sig),
                "hist": json.dumps(history),
                "nodes": json.dumps(baseline_nodes),
                "edges": json.dumps([list(e) for e in baseline_edges]),
                "sem": json.dumps(baseline_semantics),
                "nr": needs_reset
            })

    async def load_state(self, source_db_url: str) -> Tuple[List[float], List[float], List[str], List, Dict, int]:
        """Carga el estado completo. Devuelve también needs_reset."""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT baseline_sig, history, baseline_nodes, baseline_edges, baseline_semantics, needs_reset FROM engine_baselines WHERE source_db_url = :url"), {"url": source_db_url})
            row = result.fetchone()
            if not row:
                return [], [], [], [], {}, 0
            
            edges = [tuple(e) for e in json.loads(row[3])] if row[3] else []
            needs_reset = row[5] if row[5] is not None else 0
            return json.loads(row[0]), json.loads(row[1]), json.loads(row[2]), edges, json.loads(row[4]), needs_reset

    async def request_reset(self, source_db_url: str):
        """Activa la bandera de reset sin borrar el historial."""
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE engine_baselines SET needs_reset = 1 WHERE source_db_url = :url"), {"url": source_db_url})