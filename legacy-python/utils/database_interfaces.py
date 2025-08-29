"""Database service interfaces and abstractions."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import logging
from utils.error_handlers import ErrorCode, StandardizedError, DatabaseErrorHandler

logger = logging.getLogger(__name__)


class DatabaseService(ABC):
    """Abstract base class for database services."""
    
    def __init__(self, name: str):
        self.name = name
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the database."""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""
        pass
        
    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if database connection is healthy."""
        pass


class VectorSearchService(DatabaseService):
    """Abstract interface for vector search databases (like Milvus)."""
    
    @abstractmethod
    async def search_by_vector(self, 
                              embedding: List[float], 
                              collection: str,
                              limit: int = 5,
                              filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        pass
        
    @abstractmethod
    async def insert_vectors(self, 
                            collection: str,
                            vectors: List[Dict[str, Any]]) -> bool:
        """Insert vectors into collection."""
        pass


class GraphSearchService(DatabaseService):
    """Abstract interface for graph databases (like Neo4j)."""
    
    @abstractmethod
    async def search_nodes(self, 
                          query: str,
                          limit: int = 10,
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search nodes based on text query."""
        pass
        
    @abstractmethod 
    async def create_relationship(self, 
                                 from_node: str, 
                                 to_node: str, 
                                 relationship_type: str,
                                 properties: Optional[Dict[str, Any]] = None) -> bool:
        """Create relationship between nodes."""
        pass


class RelationalSearchService(DatabaseService):
    """Abstract interface for relational databases (like SQL Server)."""
    
    @abstractmethod
    async def execute_query(self, 
                           query: str, 
                           parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        pass
        
    @abstractmethod
    async def execute_command(self, 
                             command: str, 
                             parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Execute SQL command (INSERT/UPDATE/DELETE)."""
        pass


class UnifiedSearchService:
    """Unified service that coordinates searches across all databases."""
    
    def __init__(self, 
                 vector_service: Optional[VectorSearchService] = None,
                 graph_service: Optional[GraphSearchService] = None, 
                 relational_service: Optional[RelationalSearchService] = None):
        self.vector_service = vector_service
        self.graph_service = graph_service
        self.relational_service = relational_service
        self._logger = logging.getLogger(__name__)
        
    async def search_all(self, 
                        query: str, 
                        embedding: Optional[List[float]] = None,
                        limit: int = 5) -> Dict[str, Any]:
        """Search across all available databases."""
        results = {
            "vector_results": [],
            "graph_results": [],
            "relational_results": [],
            "errors": []
        }
        
        # Vector search
        if self.vector_service and embedding:
            try:
                if await self.vector_service.is_healthy():
                    results["vector_results"] = await self.vector_service.search_by_vector(
                        embedding, "default_collection", limit
                    )
                else:
                    results["errors"].append("Vector service unhealthy")
            except Exception as e:
                error = DatabaseErrorHandler.handle_connection_error(e, "vector")
                results["errors"].append(error.to_dict())
        
        # Graph search  
        if self.graph_service:
            try:
                if await self.graph_service.is_healthy():
                    results["graph_results"] = await self.graph_service.search_nodes(
                        query, limit
                    )
                else:
                    results["errors"].append("Graph service unhealthy")
            except Exception as e:
                error = DatabaseErrorHandler.handle_connection_error(e, "graph")
                results["errors"].append(error.to_dict())
        
        # Relational search would be query-dependent, so skipping for now
        
        return results
        
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all database services."""
        health_status = {}
        
        if self.vector_service:
            try:
                health_status["vector"] = await self.vector_service.is_healthy()
            except Exception:
                health_status["vector"] = False
                
        if self.graph_service:
            try:
                health_status["graph"] = await self.graph_service.is_healthy()
            except Exception:
                health_status["graph"] = False
                
        if self.relational_service:
            try:
                health_status["relational"] = await self.relational_service.is_healthy()
            except Exception:
                health_status["relational"] = False
                
        return health_status