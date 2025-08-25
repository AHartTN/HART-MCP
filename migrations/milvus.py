from pymilvus import DataType


def setup_milvus(client):
    """Sets up the Milvus vector collection using the provided client."""
    from pymilvus import Collection, CollectionSchema, FieldSchema, utility

    if client is None:
        print("Failed to connect to Milvus.")
        return None
    collection_name = getattr(client, "collection_name", None)
    if not collection_name:
        print("Milvus client does not have a collection_name attribute.")
        return None
    if utility.has_collection(collection_name):
        print(f"Collection '{collection_name}' already exists. Dropping it...")
        Collection(collection_name).drop()
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
    ]
    schema = CollectionSchema(
        fields=fields, description="Vector embeddings for RAG chunks"
    )
    collection = Collection(name=collection_name, schema=schema)
    index_params = {
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 8, "efConstruction": 200},
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    print(f"Collection '{collection_name}' created and indexed successfully.")
    return collection
