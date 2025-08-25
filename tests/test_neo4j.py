import os

from neo4j import GraphDatabase

try:
    host = os.getenv("NEO4J_HOST")
    port = os.getenv("NEO4J_PORT")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    uri = f"bolt://{host}:{port}"
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        result = session.run("RETURN 1")
        single_result = result.single()
        if single_result:
            print("Neo4j connection successful:", single_result[0])
        else:
            print("Neo4j connection failed: No result returned")
except Exception as e:
    print("Neo4j connection failed:", e)
