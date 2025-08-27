from neo4j import GraphDatabase
import os

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "test")


def run_neo4j_migration():
    cypher_setup = """
    CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE;
    CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
    CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
    CREATE CONSTRAINT IF NOT EXISTS FOR (l:AgentLog) REQUIRE l.id IS UNIQUE;
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        for stmt in cypher_setup.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                session.run(stmt)
                print(f"Executed: {stmt}")
    print("Neo4j schema migration complete.")


if __name__ == "__main__":
    run_neo4j_migration()
