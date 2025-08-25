from db_connectors import get_neo4j_driver


def run_neo4j_migration():
    cypher_setup = """
    CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE;
    CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
    CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
    CREATE CONSTRAINT IF NOT EXISTS FOR (l:AgentLog) REQUIRE l.id IS UNIQUE;
    """
    driver = get_neo4j_driver()
    if not driver:
        print("Failed to connect to Neo4j.")
        return
    with driver.session() as session:
        for stmt in cypher_setup.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                session.run(stmt)
                print(f"Executed: {stmt}")
    print("Neo4j schema migration complete.")


if __name__ == "__main__":
    run_neo4j_migration()
