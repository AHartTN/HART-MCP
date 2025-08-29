import asyncio
import os
import json
from dotenv import load_dotenv
from pymilvus import MilvusClient, MilvusException

# Load environment variables from .env file
load_dotenv()

# --- Milvus Configuration from config.py logic ---
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_USER = os.getenv("MILVUS_UID") or os.getenv("MILVUS_USER")
MILVUS_PASSWORD = os.getenv("MILVUS_PWD") or os.getenv("MILVUS_PASSWORD")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION")


async def get_milvus_schema():
    schema_info = {}
    client = None
    try:
        uri = f"http://{MILVUS_USER}:{MILVUS_PASSWORD}@{MILVUS_HOST}:{MILVUS_PORT}"
        client = MilvusClient(uri=uri)

        # Check if the collection exists
        if not client.has_collection(collection_name=MILVUS_COLLECTION):
            schema_info["error"] = (
                f"Milvus collection '{MILVUS_COLLECTION}' does not exist."
            )
            return schema_info

        # Describe the collection
        collection_info = client.describe_collection(collection_name=MILVUS_COLLECTION)
        schema_info["collection_name"] = collection_info.get("collection_name")
        schema_info["fields"] = []
        for field in collection_info.get("fields", []):
            schema_info["fields"].append(
                {
                    "name": field.get("name"),
                    "description": field.get("description"),
                    "type": field.get("type"),
                    "is_primary_key": field.get("is_primary_key"),
                    "auto_id": field.get("auto_id"),
                    "params": field.get("params"),
                }
            )
        schema_info["indexes"] = collection_info.get("indexes", [])

    except MilvusException as e:
        schema_info = {
            "error": str(e),
            "milvus_uri": uri if "uri" in locals() else "N/A",
        }
    except Exception as e:
        schema_info = {"error": str(e)}
    finally:
        if client:
            client.close()
    return schema_info


if __name__ == "__main__":
    schema = asyncio.run(get_milvus_schema())
    print(json.dumps(schema, indent=2))
