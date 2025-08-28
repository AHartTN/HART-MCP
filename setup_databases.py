#!/usr/bin/env python3
"""
Comprehensive database setup script for HART-MCP
Resets and configures SQL Server, Milvus, and Neo4j databases
"""

import asyncio
import json
import logging
import traceback
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def setup_sql_server():
    """Reset and configure SQL Server database with proper schema."""
    logger.info("🔄 Setting up SQL Server database...")

    try:
        from db_connectors import get_sql_server_connection
        from config import SQL_SERVER_CONNECTION_STRING

        logger.info(f"Connecting to SQL Server...")

        async with get_sql_server_connection() as conn:
            cursor = await asyncio.to_thread(conn.cursor)

            # Drop existing tables in reverse dependency order
            drop_commands = [
                "DROP TABLE IF EXISTS ChangeLog",
                "DROP TABLE IF EXISTS AgentLogs",
                "DROP TABLE IF EXISTS Chunks",
                "DROP TABLE IF EXISTS Documents",
                "DROP TABLE IF EXISTS Agents",
            ]

            for cmd in drop_commands:
                logger.info(f"Executing: {cmd}")
                await asyncio.to_thread(cursor.execute, cmd)
                await asyncio.to_thread(conn.commit)

            # Create tables with simplified schema (no VECTOR type for compatibility)
            create_commands = [
                """
                CREATE TABLE Agents (
                    AgentID INT IDENTITY PRIMARY KEY,
                    Name NVARCHAR(255) NOT NULL UNIQUE,
                    Role NVARCHAR(100),
                    Status NVARCHAR(50)
                )
                """,
                """
                CREATE TABLE Documents (
                    DocumentID UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
                    Title NVARCHAR(MAX),
                    SourceURL NVARCHAR(MAX),
                    DocumentContent NVARCHAR(MAX), -- Simplified for compatibility
                    CreatedAt DATETIME DEFAULT GETDATE()
                )
                """,
                """
                CREATE TABLE Chunks (
                    ChunkID UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
                    DocumentID UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Documents(DocumentID),
                    Text NVARCHAR(MAX),
                    Embedding NVARCHAR(MAX), -- JSON array as string for compatibility
                    ModelName NVARCHAR(100),
                    ModelVersion NVARCHAR(50),
                    CreatedAt DATETIME DEFAULT GETDATE()
                )
                """,
                """
                CREATE TABLE AgentLogs (
                    LogID INT IDENTITY PRIMARY KEY,
                    AgentID INT FOREIGN KEY REFERENCES Agents(AgentID),
                    QueryContent NVARCHAR(MAX),
                    ResponseContent NVARCHAR(MAX),
                    ThoughtTree NVARCHAR(MAX), -- JSON as string
                    BDIState NVARCHAR(MAX), -- JSON as string  
                    Evaluation NVARCHAR(MAX), -- JSON as string
                    RetrievedChunks NVARCHAR(MAX), -- JSON as string
                    CreatedAt DATETIME DEFAULT GETDATE()
                )
                """,
                """
                CREATE TABLE ChangeLog (
                    ChangeID INT IDENTITY PRIMARY KEY,
                    SourceTable NVARCHAR(50),
                    SourceID NVARCHAR(100),
                    ChangeType NVARCHAR(10),
                    Payload NVARCHAR(MAX), -- JSON as string
                    CreatedAt DATETIME DEFAULT GETDATE()
                )
                """,
            ]

            for cmd in create_commands:
                logger.info(f"Creating table...")
                await asyncio.to_thread(cursor.execute, cmd)
                await asyncio.to_thread(conn.commit)

            # Insert sample data
            sample_data = [
                "INSERT INTO Agents (Name, Role, Status) VALUES ('TestAgent', 'General Agent', 'active')",
                "INSERT INTO Agents (Name, Role, Status) VALUES ('Specialist_1', 'Specialist Agent', 'active')",
                "INSERT INTO Agents (Name, Role, Status) VALUES ('Orchestrator_1', 'Mission Orchestrator', 'active')",
            ]

            for cmd in sample_data:
                logger.info(f"Inserting sample data...")
                await asyncio.to_thread(cursor.execute, cmd)
                await asyncio.to_thread(conn.commit)

            # Test the setup
            await asyncio.to_thread(cursor.execute, "SELECT COUNT(*) FROM Agents")
            result = await asyncio.to_thread(cursor.fetchone)
            logger.info(f"✅ SQL Server setup complete. Agents count: {result[0]}")

            await asyncio.to_thread(cursor.close)

    except Exception as e:
        logger.error(f"❌ SQL Server setup failed: {e}")
        logger.error(traceback.format_exc())
        raise


async def setup_milvus():
    """Reset and configure Milvus collection with correct schema."""
    logger.info("🔄 Setting up Milvus database...")

    try:
        from db_connectors import get_milvus_client
        from config import MILVUS_COLLECTION

        client = await get_milvus_client()
        if not client:
            raise Exception("Failed to connect to Milvus")

        # Drop existing collection if it exists
        if client.has_collection(collection_name=MILVUS_COLLECTION):
            logger.info(f"Dropping existing collection: {MILVUS_COLLECTION}")
            client.drop_collection(collection_name=MILVUS_COLLECTION)

        # Create collection with proper schema
        schema = {
            "collection_name": MILVUS_COLLECTION,
            "dimension": 384,  # Dimension for sentence-transformers/all-MiniLM-L6-v2
        }

        logger.info(f"Creating collection: {MILVUS_COLLECTION}")
        client.create_collection(
            collection_name=MILVUS_COLLECTION,
            dimension=384,  # sentence-transformers/all-MiniLM-L6-v2 dimension
            metric_type="COSINE",
            auto_id=True,
            primary_field_name="id",
            vector_field_name="embedding",
            enable_dynamic_field=True,
        )

        # Insert sample data
        sample_data = [
            {
                "document_id": "doc_1",
                "text": "This is a sample document about AI and machine learning.",
                "embedding": [0.1] * 384,  # Dummy embedding
            },
            {
                "document_id": "doc_2",
                "text": "SQL Server 2025 includes native vector support with DiskANN indexing.",
                "embedding": [0.2] * 384,  # Dummy embedding
            },
        ]

        logger.info("Inserting sample data into Milvus...")
        client.insert(collection_name=MILVUS_COLLECTION, data=sample_data)

        # Skip index creation for now - collection will use default indexing

        # Load collection
        client.load_collection(collection_name=MILVUS_COLLECTION)

        # Test the setup
        result = client.query(
            collection_name=MILVUS_COLLECTION,
            filter="document_id == 'doc_1'",
            output_fields=["document_id", "text"],
        )
        logger.info(f"✅ Milvus setup complete. Sample query result: {result}")

        if hasattr(client, "close"):
            client.close()

    except Exception as e:
        logger.error(f"❌ Milvus setup failed: {e}")
        logger.error(traceback.format_exc())
        raise


async def setup_neo4j():
    """Reset and configure Neo4j database."""
    logger.info("🔄 Setting up Neo4j database...")

    try:
        from db_connectors import get_neo4j_driver

        driver = await get_neo4j_driver()
        if not driver:
            raise Exception("Failed to connect to Neo4j")

        async with driver.session() as session:
            # Clear existing data
            logger.info("Clearing existing Neo4j data...")
            await session.run("MATCH (n) DETACH DELETE n")

            # Create sample nodes and relationships
            logger.info("Creating sample data in Neo4j...")

            # Create sample nodes
            await session.run("""
                CREATE (doc1:Document {id: 'doc_1', title: 'AI and Machine Learning Guide', text: 'This is a sample document about AI and machine learning.'})
                CREATE (doc2:Document {id: 'doc_2', title: 'SQL Server 2025 Features', text: 'SQL Server 2025 includes native vector support with DiskANN indexing.'})
                CREATE (agent1:Agent {id: 'agent_1', name: 'TestAgent', role: 'General Agent'})
                CREATE (agent2:Agent {id: 'agent_2', name: 'Specialist_1', role: 'Specialist Agent'})
            """)

            # Create relationships
            await session.run("""
                MATCH (a:Agent {id: 'agent_1'}), (d:Document {id: 'doc_1'})
                CREATE (a)-[:PROCESSED]->(d)
            """)

            await session.run("""
                MATCH (a:Agent {id: 'agent_2'}), (d:Document {id: 'doc_2'}) 
                CREATE (a)-[:ANALYZED]->(d)
            """)

            # Test the setup
            result = await session.run("MATCH (n) RETURN count(n) as node_count")
            record = await result.single()
            node_count = record["node_count"]
            logger.info(f"✅ Neo4j setup complete. Total nodes: {node_count}")

        if hasattr(driver, "close"):
            await asyncio.to_thread(driver.close)

    except Exception as e:
        logger.error(f"❌ Neo4j setup failed: {e}")
        logger.error(traceback.format_exc())
        raise


async def run_health_checks():
    """Run comprehensive health checks on all databases."""
    logger.info("🔍 Running database health checks...")

    try:
        from utils import check_database_health

        health_status = await check_database_health()

        for db_name, status in health_status.items():
            status_icon = "✅" if status else "❌"
            logger.info(
                f"{status_icon} {db_name.upper()}: {'Healthy' if status else 'Unhealthy'}"
            )

        all_healthy = all(health_status.values())
        if all_healthy:
            logger.info("🎉 All databases are healthy and ready!")
        else:
            logger.warning("⚠️ Some databases are not healthy. Check the logs above.")

        return all_healthy

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main setup function."""
    logger.info("🚀 Starting HART-MCP database setup...")

    setup_functions = [
        ("SQL Server", setup_sql_server),
        ("Milvus", setup_milvus),
        ("Neo4j", setup_neo4j),
    ]

    success_count = 0

    for db_name, setup_func in setup_functions:
        try:
            await setup_func()
            success_count += 1
        except Exception as e:
            logger.error(f"❌ {db_name} setup failed, continuing with others...")

    logger.info(
        f"📊 Setup completed: {success_count}/{len(setup_functions)} databases configured"
    )

    # Run health checks
    all_healthy = await run_health_checks()

    if all_healthy and success_count == len(setup_functions):
        logger.info("🎯 HART-MCP database setup completed successfully!")
        logger.info("✅ All systems are ready for testing!")
        return True
    else:
        logger.warning("⚠️ Setup completed with some issues. Check logs above.")
        return False


if __name__ == "__main__":
    asyncio.run(main())
