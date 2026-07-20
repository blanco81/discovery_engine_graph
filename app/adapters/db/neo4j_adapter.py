# adapters/db/neo4j_adapter.py
from neo4j import GraphDatabase
from typing import List
import networkx as nx
import logging

from app.core.domain.models import PartialInclusionDependency
from app.core.ports.graph_port import GraphPort
from app.config.config import settings

logger = logging.getLogger(__name__)

class Neo4jAdapter(GraphPort):
    """Adaptador para materializar el grafo dinámico en Neo4j."""

    def __init__(self):
        self.driver = None

    def connect(self) -> None:
        logger.info(f"Conectando a Neo4j: {settings.NEO4J_URI}")
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        self.driver.verify_connectivity()
        logger.info("Conexión a Neo4j exitosa.")

    def disconnect(self) -> None:
        if self.driver:
            self.driver.close()

    def save_pinds(self, pinds: List[PartialInclusionDependency]) -> None:
        """Inserta o actualiza las pINDs como aristas dirigidas en Neo4j."""
        if not self.driver:
            raise ConnectionError("No hay conexión a Neo4j.")

        with self.driver.session() as session:
            # Limpiar el grafo anterior para esta prueba (En producción sería incremental)
            session.run("MATCH (n) DETACH DELETE n")
            
            for pind in pinds:
                cypher_query = """
                MERGE (t1:Table {name: $dep_table})
                MERGE (t2:Table {name: $ref_table})
                MERGE (t1)-[r:REFERENCES {dep_col: $dep_col, ref_col: $ref_col}]->(t2)
                SET r.rho = $rho, r.violations = $violations, r.total = $total
                """
                session.run(cypher_query, 
                    dep_table=pind.dependent.table_name,
                    ref_table=pind.referenced.table_name,
                    dep_col=pind.dependent.column_name,
                    ref_col=pind.referenced.column_name,
                    rho=pind.rho,
                    violations=pind.violation_count,
                    total=pind.total_count
                )
        logger.info(f"{len(pinds)} pINDs materializadas como aristas en Neo4j.")

    def get_networkx_graph(self) -> nx.DiGraph:
        """Extrae el grafo de Neo4j a NetworkX para cálculos de NetSimile."""
        G = nx.DiGraph()
        with self.driver.session() as session:
            # Obtener nodos
            nodes = session.run("MATCH (t:Table) RETURN t.name as name")
            for node in nodes:
                G.add_node(node["name"])
            
            # Obtener aristas
            edges = session.run("""
                MATCH (t1)-[r:REFERENCES]->(t2) 
                RETURN t1.name as source, t2.name as target, r.rho as rho
            """)
            for edge in edges:
                G.add_edge(edge["source"], edge["target"], weight=edge["rho"])
                
        logger.info(f"Grafo extraído a NetworkX: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas.")
        return G