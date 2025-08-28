"""Unified database service implementation."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from utils.database_interfaces import (
    VectorSearchService, 
    GraphSearchService, 
    RelationalSearchService,
    UnifiedSearchService
)
from utils.error_handlers import ErrorCode, DatabaseErrorHandler, safe_execute
from config import MILVUS_COLLECTION

logger = logging.getLogger(__name__)


class MilvusSearchService(VectorSearchService):
    """Concrete implementation of vector search using Milvus."""
    
    def __init__(self):
        super().__init__("Milvus")
        self._client = None
        
    async def connect(self) -> bool:
        """Establish connection to Milvus."""
        try:
            from utils import milvus_connection_context
            # Test connection by trying to get a client
            async with milvus_connection_context() as client:
                self._client = client
                return client is not None
        except Exception as e:
            self._logger.error(f"Failed to connect to Milvus: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close Milvus connection."""
        self._client = None
        
    async def is_healthy(self) -> bool:
        """Check if Milvus connection is healthy."""
        try:
            from utils import milvus_connection_context
            async with milvus_connection_context() as client:
                return client is not None
        except Exception:
            return False
    
    @safe_execute(ErrorCode.DATABASE_QUERY)
    async def search_by_vector(self, 
                              embedding: List[float], 
                              collection: str = None,
                              limit: int = 5,
                              filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors in Milvus."""
        if not collection:
            collection = MILVUS_COLLECTION
            
        try:
            from utils import milvus_connection_context
            async with milvus_connection_context() as milvus_client:
                if not milvus_client:
                    raise ConnectionError("Milvus client not available")
                
                search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
                
                # Apply filters if provided
                if filters:
                    # Milvus filter implementation would go here
                    pass
                
                milvus_results = await asyncio.to_thread(
                    milvus_client.search,
                    collection_name=collection,
                    data=[embedding],
                    anns_field="embedding",
                    search_params=search_params,
                    limit=limit,
                    output_fields=["document_id", "text"]
                )
                
                # Extract and format results
                extracted_results = []
                for hits_list in milvus_results:
                    for hit in hits_list:
                        extracted_results.append({
                            "id": hit.id,
                            "distance": hit.distance,
                            "score": 1 - hit.distance,  # Convert distance to similarity score
                            "document_id": hit.entity.get("document_id"),
                            "text": hit.entity.get("text"),
                            "source": "milvus"
                        })
                
                return extracted_results
                
        except Exception as e:
            error = DatabaseErrorHandler.handle_query_error(e, f"vector search with {len(embedding)} dims", "Milvus")
            raise Exception(error.message) from e
    
    @safe_execute(ErrorCode.DATABASE_QUERY)
    async def insert_vectors(self, collection: str, vectors: List[Dict[str, Any]]) -> bool:
        """Insert vectors into Milvus collection."""
        try:
            from utils import milvus_connection_context
            async with milvus_connection_context() as milvus_client:
                if not milvus_client:
                    return False
                
                # Format data for insertion
                data_to_insert = []
                for vector_data in vectors:
                    data_to_insert.append(vector_data)
                
                result = await asyncio.to_thread(
                    milvus_client.insert,
                    collection_name=collection,
                    data=data_to_insert
                )
                
                return result is not None
                
        except Exception as e:
            self._logger.error(f"Failed to insert vectors into Milvus: {e}")
            return False


class Neo4jSearchService(GraphSearchService):
    """Concrete implementation of graph search using Neo4j."""
    
    def __init__(self):
        super().__init__("Neo4j")
        self._driver = None
        
    async def connect(self) -> bool:
        """Establish connection to Neo4j."""
        try:
            from utils import neo4j_connection_context
            async with neo4j_connection_context() as driver:
                self._driver = driver
                return driver is not None
        except Exception as e:
            self._logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
    
    async def is_healthy(self) -> bool:
        """Check if Neo4j connection is healthy."""
        try:
            from utils import neo4j_connection_context
            async with neo4j_connection_context() as driver:
                return driver is not None
        except Exception:
            return False
    
    @safe_execute(ErrorCode.DATABASE_QUERY)
    async def search_nodes(self, 
                          query: str,
                          limit: int = 10,
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search nodes based on text query."""
        try:
            from utils import neo4j_connection_context
            from query_utils import SEARCH_NODES_CONTAINS_TEXT
            
            async with neo4j_connection_context() as neo4j_driver:
                if not neo4j_driver:
                    raise ConnectionError("Neo4j driver not available")
                
                async with neo4j_driver.session() as session:
                    # Apply filters to the query if provided
                    cypher_query = SEARCH_NODES_CONTAINS_TEXT
                    params = {"query": query}
                    
                    if filters:
                        # Add filter conditions to the query
                        filter_conditions = []
                        for key, value in filters.items():
                            filter_conditions.append(f"n.{key} = ${key}")
                            params[key] = value
                        
                        if filter_conditions:
                            filter_clause = " AND " + " AND ".join(filter_conditions)
                            cypher_query = cypher_query.replace("RETURN", f"{filter_clause} RETURN")
                    
                    # Replace existing LIMIT with desired limit
                    if "LIMIT" in cypher_query:
                        cypher_query = cypher_query.rsplit("LIMIT", 1)[0] + f"LIMIT {limit}"
                    else:
                        cypher_query += f" LIMIT {limit}"
                    
                    result = await session.run(cypher_query, params)
                    records = await result.data()
                    
                    formatted_results = []
                    for i, record in enumerate(records):
                        node_text = record.get("text", "")
                        related_info = record.get("related_info", [])
                        
                        result_entry = {
                            "id": i,
                            "text": node_text,
                            "source": "neo4j",
                            "relationships": []
                        }
                        
                        if related_info:
                            for rel in related_info:
                                result_entry["relationships"].append({
                                    "type": rel.get("relationship", ""),
                                    "related_text": rel.get("related_text", "")
                                })
                        
                        formatted_results.append(result_entry)
                    
                    return formatted_results
                    
        except Exception as e:
            error = DatabaseErrorHandler.handle_query_error(e, query[:50], "Neo4j")
            raise Exception(error.message) from e
    
    @safe_execute(ErrorCode.DATABASE_QUERY)
    async def create_relationship(self, 
                                 from_node: str, 
                                 to_node: str, 
                                 relationship_type: str,
                                 properties: Optional[Dict[str, Any]] = None) -> bool:
        """Create relationship between nodes."""
        try:
            from utils import neo4j_connection_context
            
            async with neo4j_connection_context() as neo4j_driver:
                if not neo4j_driver:
                    return False
                
                async with neo4j_driver.session() as session:
                    # Create relationship query
                    props_str = ""
                    params = {
                        "from_node": from_node,
                        "to_node": to_node
                    }
                    
                    if properties:
                        prop_items = [f"{k}: ${k}" for k in properties.keys()]
                        props_str = f" {{{', '.join(prop_items)}}}"
                        params.update(properties)
                    
                    query = f"""
                    MATCH (a), (b)
                    WHERE a.text = $from_node AND b.text = $to_node
                    CREATE (a)-[r:{relationship_type}{props_str}]->(b)
                    RETURN r
                    """
                    
                    result = await session.run(query, params)
                    return await result.single() is not None
                    
        except Exception as e:
            self._logger.error(f"Failed to create relationship in Neo4j: {e}")
            return False


class SQLServerSearchService(RelationalSearchService):
    """Concrete implementation of relational search using SQL Server."""
    
    def __init__(self):
        super().__init__("SQL Server")
        
    async def connect(self) -> bool:
        """Establish connection to SQL Server."""
        try:
            from db_connectors import get_sql_server_connection
            connection_manager = await get_sql_server_connection()
            return connection_manager is not None
        except Exception as e:
            self._logger.error(f"Failed to connect to SQL Server: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close SQL Server connection."""
        # Connection management handled by context managers
        pass
    
    async def is_healthy(self) -> bool:
        """Check if SQL Server connection is healthy."""
        try:
            return await self.execute_query("SELECT 1 as health_check") is not None
        except Exception:
            return False
    
    @safe_execute(ErrorCode.DATABASE_QUERY)
    async def execute_query(self, 
                           query: str, 
                           parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        try:
            from db_connectors import get_sql_server_connection
            from utils import sql_connection_context
            
            connection_manager = await get_sql_server_connection()
            async with connection_manager as conn:
                async with sql_connection_context() as (sql_conn, cursor):
                    if parameters:
                        # Handle parameterized queries
                        param_values = list(parameters.values())
                        await asyncio.to_thread(cursor.execute, query, param_values)
                    else:
                        await asyncio.to_thread(cursor.execute, query)
                    
                    rows = await asyncio.to_thread(cursor.fetchall)
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    results = []
                    for row in rows:
                        result_dict = dict(zip(columns, row, strict=False))
                        result_dict["source"] = "sql_server"
                        results.append(result_dict)
                    
                    return results
                    
        except Exception as e:
            error = DatabaseErrorHandler.handle_query_error(e, query[:50], "SQL Server")
            raise Exception(error.message) from e
    
    @safe_execute(ErrorCode.DATABASE_QUERY)
    async def execute_command(self, 
                             command: str, 
                             parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Execute SQL command (INSERT/UPDATE/DELETE)."""
        try:
            from db_connectors import get_sql_server_connection
            from utils import sql_connection_context
            
            connection_manager = await get_sql_server_connection()
            async with connection_manager as conn:
                async with sql_connection_context() as (sql_conn, cursor):
                    if parameters:
                        param_values = list(parameters.values())
                        await asyncio.to_thread(cursor.execute, command, param_values)
                    else:
                        await asyncio.to_thread(cursor.execute, command)
                    
                    await asyncio.to_thread(sql_conn.commit)
                    return True
                    
        except Exception as e:
            self._logger.error(f"Failed to execute SQL command: {e}")
            return False
    
    @safe_execute(ErrorCode.DATABASE_QUERY)
    async def search_documents(self, 
                              query: str,
                              limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents by text content in SQL Server."""
        try:
            # Search across Documents and Chunks tables for text content
            search_query = """
            SELECT TOP (?) 
                d.DocumentID,
                d.Title,
                d.SourceURL,
                d.CreatedAt,
                c.Text,
                'document_chunk' as result_type,
                'sql_server' as source
            FROM Documents d 
            LEFT JOIN Chunks c ON d.DocumentID = c.DocumentID
            WHERE d.Title LIKE ? 
               OR d.SourceURL LIKE ?
               OR c.Text LIKE ?
            ORDER BY d.CreatedAt DESC
            """
            
            search_pattern = f"%{query}%"
            parameters = {
                "limit": limit,
                "title_pattern": search_pattern,
                "url_pattern": search_pattern,
                "text_pattern": search_pattern
            }
            
            results = await self.execute_query(search_query, parameters)
            self._logger.info(f"SQL Server document search returned {len(results)} results")
            return results
            
        except Exception as e:
            self._logger.error(f"Document search failed: {e}")
            return []


class EnhancedUnifiedSearchService(UnifiedSearchService):
    """Enhanced unified search service with better error handling and logging."""
    
    def __init__(self):
        # Initialize concrete implementations
        vector_service = MilvusSearchService()
        graph_service = Neo4jSearchService()  
        relational_service = SQLServerSearchService()
        
        super().__init__(vector_service, graph_service, relational_service)
    
    @safe_execute(ErrorCode.DATABASE_QUERY, default_return={
        "vector_results": [], "graph_results": [], "relational_results": [], 
        "errors": ["Service initialization failed"], "search_successful": False
    })
    async def search_all(self, 
                        query: str, 
                        embedding: Optional[List[float]] = None,
                        limit: int = 5,
                        include_vector: bool = True,
                        include_graph: bool = True,
                        include_relational: bool = False) -> Dict[str, Any]:
        """Enhanced search across selected databases with better error handling."""
        results = {
            "vector_results": [],
            "graph_results": [],
            "relational_results": [],
            "errors": [],
            "search_successful": False,
            "query": query,
            "services_attempted": []
        }
        
        successful_searches = 0
        
        # Vector search
        if include_vector and self.vector_service and embedding:
            results["services_attempted"].append("vector")
            try:
                if await self.vector_service.is_healthy():
                    vector_results = await self.vector_service.search_by_vector(
                        embedding, limit=limit
                    )
                    results["vector_results"] = vector_results
                    if vector_results:
                        successful_searches += 1
                        self._logger.info(f"Vector search returned {len(vector_results)} results")
                else:
                    results["errors"].append("Vector service unhealthy")
            except Exception as e:
                error = DatabaseErrorHandler.handle_connection_error(e, "vector")
                results["errors"].append(error.to_dict())
                self._logger.error(f"Vector search failed: {e}")
        
        # Graph search
        if include_graph and self.graph_service:
            results["services_attempted"].append("graph")
            try:
                if await self.graph_service.is_healthy():
                    graph_results = await self.graph_service.search_nodes(
                        query, limit=limit
                    )
                    results["graph_results"] = graph_results
                    if graph_results:
                        successful_searches += 1
                        self._logger.info(f"Graph search returned {len(graph_results)} results")
                else:
                    results["errors"].append("Graph service unhealthy")
            except Exception as e:
                error = DatabaseErrorHandler.handle_connection_error(e, "graph")
                results["errors"].append(error.to_dict())
                self._logger.error(f"Graph search failed: {e}")
        
        # Relational search (only if explicitly requested with specific query)
        if include_relational and self.relational_service:
            results["services_attempted"].append("relational")
            try:
                # Perform text-based search across metadata tables
                search_results = await self.relational_service.search_documents(
                    query=query,
                    limit=limit
                )
                if search_results and isinstance(search_results, list):
                    results["relational_results"].extend(search_results)
                    successful_searches += 1
                    self._logger.info(f"Relational search returned {len(search_results)} results")
                else:
                    results["errors"].append("Relational service returned no results")
            except Exception as e:
                error = DatabaseErrorHandler.handle_connection_error(e, "relational")
                results["errors"].append(error.to_dict())
                self._logger.error(f"Relational search failed: {e}")
            
        results["search_successful"] = successful_searches > 0
        results["services_succeeded"] = successful_searches
        results["total_results"] = len(results["vector_results"]) + len(results["graph_results"]) + len(results["relational_results"])
        
        return results
    
    async def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status of all database services."""
        status = {}
        
        services = [
            ("vector", self.vector_service),
            ("graph", self.graph_service), 
            ("relational", self.relational_service)
        ]
        
        for service_name, service in services:
            if service:
                try:
                    is_healthy = await service.is_healthy()
                    status[service_name] = {
                        "healthy": is_healthy,
                        "name": service.name,
                        "type": service.__class__.__name__
                    }
                except Exception as e:
                    status[service_name] = {
                        "healthy": False,
                        "name": service.name,
                        "error": str(e),
                        "type": service.__class__.__name__
                    }
            else:
                status[service_name] = {
                    "healthy": False,
                    "error": "Service not initialized"
                }
        
        return status


# Global instance for use throughout the application
unified_db_service = EnhancedUnifiedSearchService()