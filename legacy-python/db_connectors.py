import asyncio
import json
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from functools import wraps
import time

import pyodbc
from neo4j import AsyncGraphDatabase, Driver, basic_auth
from neo4j.exceptions import Neo4jError, ServiceUnavailable, TransientError
from pymilvus import MilvusClient, MilvusException, connections

from config import (
    MILVUS_HOST,
    MILVUS_PASSWORD,
    MILVUS_PORT,
    MILVUS_USER,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    SQL_SERVER_CONNECTION_STRING,
)
from query_utils import (
    AGENTLOGS_SELECT_EVALUATION,
    AGENTLOGS_UPDATE_EVALUATION,
    execute_sql_query,
)

logger = logging.getLogger(__name__)

# Connection pools and state management
_sql_connection_pool = None
_neo4j_driver_pool = None
_milvus_client_pool = None

# Circuit breaker state
_circuit_breaker_state = {
    "sql_server": {"failures": 0, "last_failure": 0, "state": "CLOSED"},
    "neo4j": {"failures": 0, "last_failure": 0, "state": "CLOSED"},
    "milvus": {"failures": 0, "last_failure": 0, "state": "CLOSED"},
}

CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 60  # seconds


def circuit_breaker(service_name: str):
    """Circuit breaker decorator for database operations."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            state = _circuit_breaker_state[service_name]

            # Check if circuit is open
            if state["state"] == "OPEN":
                if time.time() - state["last_failure"] > CIRCUIT_BREAKER_TIMEOUT:
                    state["state"] = "HALF_OPEN"
                    logger.info(
                        f"Circuit breaker for {service_name} moved to HALF_OPEN"
                    )
                else:
                    raise ConnectionError(f"Circuit breaker OPEN for {service_name}")

            try:
                # Check if function is async
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # For sync functions, run them directly
                    result = func(*args, **kwargs)

                # Reset on success
                if state["state"] in ["HALF_OPEN", "CLOSED"]:
                    state["failures"] = 0
                    state["state"] = "CLOSED"
                return result

            except Exception as e:
                state["failures"] += 1
                state["last_failure"] = time.time()

                if state["failures"] >= CIRCUIT_BREAKER_THRESHOLD:
                    state["state"] = "OPEN"
                    logger.error(
                        f"Circuit breaker OPEN for {service_name} after {state['failures']} failures"
                    )

                raise e

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync usage, we can't use circuit breaker async features
            # Just call the function directly
            return func(*args, **kwargs)

        # Return async wrapper for now, as most usage seems to expect async
        return async_wrapper

    return decorator


class SQLServerConnectionManager:
    def __init__(self, connection_string, pool_size: int = 10):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.conn = None
        self._pool = asyncio.Queue(maxsize=pool_size)
        self._pool_initialized = False

    async def _initialize_pool(self):
        """Initialize connection pool lazily."""
        if not self._pool_initialized:
            for _ in range(self.pool_size):
                try:
                    conn = await asyncio.to_thread(
                        pyodbc.connect, self.connection_string
                    )
                    await self._pool.put(conn)
                except Exception as e:
                    logger.error(f"Failed to create SQL Server connection: {e}")
                    break
            self._pool_initialized = True
            logger.info(
                f"SQL Server connection pool initialized with {self._pool.qsize()} connections"
            )

    async def __aenter__(self):
        await self._initialize_pool()
        try:
            self.conn = await asyncio.wait_for(self._pool.get(), timeout=30)
            return self.conn
        except asyncio.TimeoutError:
            raise ConnectionError("Timeout getting connection from SQL Server pool")
        except Exception as e:
            logger.error(f"Error getting SQL Server connection: {e}")
            # Fallback to direct connection
            self.conn = await asyncio.to_thread(pyodbc.connect, self.connection_string)
            return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        if self.conn:
            try:
                if exc_type:
                    await asyncio.to_thread(self.conn.rollback)
                else:
                    await asyncio.to_thread(self.conn.commit)

                # Return to pool if healthy
                if not exc_type and self._pool.qsize() < self.pool_size:
                    await self._pool.put(self.conn)
                else:
                    await asyncio.to_thread(self.conn.close)
            except Exception as e:
                logger.error(f"Error returning connection to pool: {e}")
                await asyncio.to_thread(self.conn.close)


@circuit_breaker("sql_server")
async def get_sql_server_connection():
    """
    Return an async context manager for SQL Server connection.
    Usage:
        connection_manager = await get_sql_server_connection()
        async with connection_manager as conn:
            ...
    """
    # Initialize and return the connection manager
    manager = SQLServerConnectionManager(SQL_SERVER_CONNECTION_STRING)
    await manager._initialize_pool()
    return manager


async def get_milvus_client() -> Optional[MilvusClient]:
    """
    Connect to Milvus database using credentials from env vars.
    """
    try:
        uri = f"http://{MILVUS_USER}:{MILVUS_PASSWORD}@{MILVUS_HOST}:{MILVUS_PORT}"
        logger.info("Connecting to Milvus at %s...", uri)
        client = await asyncio.to_thread(
            MilvusClient, uri=uri
        )  # Run blocking call in a thread
        logger.info("Successfully connected to Milvus.")
        return client
    except MilvusException as exc:
        logger.error("Milvus connection error: %s\n%s", exc, traceback.format_exc())
        return None


async def get_neo4j_driver() -> Optional[Driver]:
    """
    Connect to Neo4j database using credentials from env vars ONLY.
    """
    try:
        logger.info("Connecting to Neo4j at %s...", NEO4J_URI)
        driver = AsyncGraphDatabase.driver(
            str(NEO4J_URI),
            auth=basic_auth(str(NEO4J_USER), str(NEO4J_PASSWORD)),
        )
        await driver.verify_connectivity()
        logger.info("Successfully connected to Neo4j.")
        return driver
    except Neo4jError as exc:
        logger.error("Neo4j connection error: %s\n%s", exc, traceback.format_exc())
        return None


async def update_agent_log_evaluation(cursor, log_id: int, new_entry: dict) -> bool:
    """
    Retrieves existing Evaluation JSON from AgentLogs, appends a new entry,
    and updates the column. Assumes an active cursor is provided.
    """
    try:
        # Execute fetchone in a thread
        result = await asyncio.to_thread(
            cursor.execute,
            AGENTLOGS_SELECT_EVALUATION,
            (log_id,),
        )
        result = await asyncio.to_thread(cursor.fetchone)

        if not result:
            logger.warning("LogID %s not found for evaluation update.", log_id)
            return False

        existing_evaluation = []
        if result[0]:
            try:
                existing_evaluation = json.loads(result[0])
            except json.JSONDecodeError:
                logger.warning(
                    (
                        "Existing evaluation for LogID %s is not valid JSON. "
                        "Initializing as empty list."
                    ),
                    log_id,
                )
            if not isinstance(existing_evaluation, list):
                existing_evaluation = []

        existing_evaluation.append(new_entry)

        # Execute update in a thread
        await asyncio.to_thread(
            execute_sql_query,
            cursor,
            AGENTLOGS_UPDATE_EVALUATION,
            (json.dumps(existing_evaluation), log_id),
        )
        return True
    except (RuntimeError, ValueError, TypeError) as exc:
        logger.error(
            "Failed to update AgentLogs Evaluation for LogID %s: %s",
            log_id,
            exc,
        )
        return False
