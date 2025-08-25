from pymilvus import connections

from config import MILVUS_HOST, MILVUS_PASSWORD, MILVUS_PORT, MILVUS_USER

try:
    connections.connect(
        host=MILVUS_HOST, port=MILVUS_PORT, user=MILVUS_USER, password=MILVUS_PASSWORD
    )
    print("Milvus connection successful:", connections.list_connections())
except Exception as e:
    print("Milvus connection failed:", e)
