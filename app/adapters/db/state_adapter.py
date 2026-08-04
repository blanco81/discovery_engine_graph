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
        # Usamos un SQLite interno asíncrono para no depender de servidores extra
        self.engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///./engine_internal.db")

    async def init_db(self):
        """Crea la tabla de estado si no existe."""
        async with self.engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS engine_baselines (
                    source_db_url TEXT PRIMARY KEY,
                    baseline_sig TEXT,
                    history TEXT,
                    baseline_nodes TEXT,
                    baseline_edges TEXT,
                    baseline_semantics TEXT
                )
            """))

    async def save_state(self, source_db_url: str, baseline_sig: List[float], history: List[float], baseline_nodes: List[str], baseline_edges: List, baseline_semantics: Dict):
        async with self.engine.begin() as conn:
            # Upsert: Si existe la URL, actualiza; si no, inserta.
            await conn.execute(text("""
                INSERT INTO engine_baselines (source_db_url, baseline_sig, history, baseline_nodes, baseline_edges, baseline_semantics)
                VALUES (:url, :sig, :hist, :nodes, :edges, :sem)
                ON CONFLICT(source_db_url) DO UPDATE SET 
                    baseline_sig=:sig, history=:hist, baseline_nodes=:nodes, 
                    baseline_edges=:edges, baseline_semantics=:sem
            """), {
                "url": source_db_url,
                "sig": json.dumps(baseline_sig),
                "hist": json.dumps(history),
                "nodes": json.dumps(baseline_nodes),
                "edges": json.dumps([list(e) for e in baseline_edges]),
                "sem": json.dumps(baseline_semantics)
            })

    async def load_state(self, source_db_url: str) -> Tuple[List[float], List[float], List[str], List, Dict]:
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM engine_baselines WHERE source_db_url = :url"), {"url": source_db_url})
            row = result.fetchone()
            if not row:
                return [], [], [], [], {}
            
            # Reconstruir tuplas para las aristas
            edges = [tuple(e) for e in json.loads(row[4])]
            return json.loads(row[1]), json.loads(row[2]), json.loads(row[3]), edges, json.loads(row[5])

    async def reset_state(self, source_db_url: str):
        async with self.engine.begin() as conn:
            await conn.execute(text("DELETE FROM engine_baselines WHERE source_db_url = :url"), {"url": source_db_url})