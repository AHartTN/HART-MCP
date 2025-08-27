import asyncio
import os
import json
from dotenv import load_dotenv
from neo4j.exceptions import Neo4jError

from db_connectors import get_neo4j_driver  # Import the project's Neo4j driver getter

# Load environment variables from .env file
load_dotenv()

# --- Neo4j Configuration from config.py logic ---
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


async def get_neo4j_schema():
    schema_info = {"nodes": {}, "relationships": {}}
    driver = None
    try:
        driver = await get_neo4j_driver()  # Use the project's driver getter

        if driver is None:
            schema_info = {
                "error": "Failed to get Neo4j driver from db_connectors.",
                "neo4j_uri": NEO4J_URI,
            }
            print(json.dumps(schema_info, indent=2))
            return schema_info

        async with driver.session() as session:
            # Get Node Labels and their properties
            result = await session.run("CALL db.labels()")
            node_labels = [record["label"] for record in result]

            for label in node_labels:
                schema_info["nodes"][label] = []
                # Get properties for each label (this is a heuristic, not exhaustive)
                # A more robust way would be to sample nodes or use APOC procedures
                try:
                    sample_node_result = await session.run(
                        f"MATCH (n:{label}) RETURN properties(n) LIMIT 1"
                    )
                    sample_properties = await sample_node_result.single()
                    if sample_properties:
                        schema_info["nodes"][label] = list(sample_properties[0].keys())
                except Exception:
                    # Handle cases where label might exist but no nodes yet
                    pass

            # Get Relationship Types and their properties
            result = await session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in result]

            for rel_type in rel_types:
                schema_info["relationships"][rel_type] = []
                try:
                    sample_rel_result = await session.run(
                        f"MATCH ()-[r:{rel_type}]->() RETURN properties(r) LIMIT 1"
                    )
                    sample_properties = await sample_rel_result.single()
                    if sample_properties:
                        schema_info["relationships"][rel_type] = list(
                            sample_properties[0].keys()
                        )
                except Exception:
                    pass

    except Neo4jError as e:
        schema_info = {"error": f"Neo4j error: {e}", "neo4j_uri": NEO4J_URI}
        print(json.dumps(schema_info, indent=2))  # Print error to stdout
    except Exception as e:
        schema_info = {
            "error": f"An unexpected error occurred: {e}",
            "neo4j_uri": NEO4J_URI,
        }
        print(json.dumps(schema_info, indent=2))  # Print error to stdout
    finally:
        if driver:
            await driver.close()
    return schema_info


if __name__ == "__main__":
    schema = asyncio.run(get_neo4j_schema())
    if "error" not in schema:  # Only print if no error was already printed
        print(json.dumps(schema, indent=2))
