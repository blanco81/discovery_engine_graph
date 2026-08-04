# app/adapters/db/neo4j_adapter.py
from neo4j import AsyncGraphDatabase
from typing import List
import networkx as nx
import logging
import re # <- Añadir import re

from app.core.domain.models import PartialInclusionDependency
from app.core.ports.graph_port import GraphPort
from app.config.config import settings

logger = logging.getLogger(__name__)

class Neo4jAdapter(GraphPort):
    def __init__(self):
        self.driver = None

    async def connect(self) -> None:
        logger.info(f"Conectando asíncronamente a Neo4j: {settings.NEO4J_URI}")
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        await self.driver.verify_connectivity()
        logger.info("Conexión a Neo4j exitosa.")

    async def disconnect(self) -> None:
        if self.driver:
            await self.driver.close()

    async def save_pinds(self, pinds: List[PartialInclusionDependency]) -> None:
        """Inserta las pINDs usando su etiqueta semántica (Ontología Emergente)."""
        if not self.driver:
            raise ConnectionError("No hay conexión a Neo4j.")

        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
            
            for pind in pinds:
                # Sanitizar el label para Cypher (solo letras, números y guion bajo)
                raw_label = pind.semantic_label or "REFERENCES"
                safe_label = re.sub(r'[^A-Z0-9_]', '', raw_label.upper())
                if not safe_label:
                    safe_label = "REFERENCES"
                
                # Concatenación segura para el tipo de arista en Cypher
                cypher_query = f"""
                MERGE (t1:Table {{name: $dep_table}})
                MERGE (t2:Table {{name: $ref_table}})
                MERGE (t1)-[r:`{safe_label}` {{dep_col: $dep_col, ref_col: $ref_col}}]->(t2)
                SET r.rho = $rho, r.violations = $violations, r.total = $total
                """
                await session.run(cypher_query, 
                    dep_table=pind.dependent.table_name,
                    ref_table=pind.referenced.table_name,
                    dep_col=pind.dependent.column_name,
                    ref_col=pind.referenced.column_name,
                    rho=pind.rho,
                    violations=pind.violation_count,
                    total=pind.total_count
                )
        logger.info(f"{len(pinds)} aristas semánticas materializadas en Neo4j.")

    async def get_networkx_graph(self) -> nx.DiGraph:
        G = nx.DiGraph()
        async with self.driver.session() as session:
            nodes = await session.run("MATCH (t:Table) RETURN t.name as name")
            async for node in nodes:
                G.add_node(node["name"])
            
            edges = await session.run("""
                MATCH (t1)-[r]->(t2) 
                RETURN t1.name as source, t2.name as target, r.rho as rho, type(r) as rel_type
            """)
            async for edge in edges:
                G.add_edge(edge["source"], edge["target"], weight=edge["rho"], type=edge["rel_type"])
                
        logger.info(f"Grafo extraído a NetworkX: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas.")
        return G