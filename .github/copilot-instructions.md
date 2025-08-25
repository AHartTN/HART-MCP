NEVER PRIORITIZE PASSIVE CONVERSATION! ALWAYS FAVOR AND PRIORITIZE ACTIONABLE WORK!

# Copilot Instructions for HART-MCP MCP/RAG Server

## Big Picture Architecture

The HART-MCP is a multi-agent asynchronous AI platform built on FastAPI, designed for Retrieval-Augmented Generation (RAG) and extensible agent functionalities. Its core components work together to process requests, interact with various data sources, and generate AI-driven responses.

-   **`server.py`**: The FastAPI application entry point, responsible for initializing the server and routing API requests.
-   **`rag_pipeline.py`**: The central RAG engine. It handles query embedding, orchestrates searches across Milvus (vector DB), Neo4j (graph DB), and SQL Server (relational DB), combines retrieved context, and generates responses using an LLM. It also incorporates a plugin execution hook.
-   **`db_connectors.py`**: Manages asynchronous connections to SQL Server, Milvus, and Neo4j, providing low-level database interaction functions.
-   **`plugins.py` & `plugins_folder/`**: Implements a dynamic plugin system. `plugins.py` handles loading and calling plugins from the `plugins_folder/`, allowing for extensible agent behaviors and tools.
-   **`routes/`**: Contains modular FastAPI routers (e.g., `agent.py`, `feedback.py`, `ingest.py`, `mcp.py`, `retrieve.py`, `status.py`, `health.py`), each defining API endpoints for specific functionalities.
-   **`config.py`**: Loads and manages environment variables from the `.env` file, providing crucial configuration for database connections and other settings.
-   **`utils.py`**: A collection of general utility functions, including asynchronous database connection context managers, multimodal text extraction (PDF, images, audio), text chunking, and database health checks.
-   **`query_utils.py`**: Centralizes SQL Server and Neo4j query templates and provides generic functions for executing these queries.
-   **`cdc_consumer.py`**: Implements a Change Data Capture (CDC) consumer. It polls a SQL Server `ChangeLog` table for new entries and synchronizes these changes (e.g., chunk upserts/deletes to Milvus, agent/document/agent log merges/deletes to Neo4j) across the different database systems, ensuring data consistency.
-   **`tree_of_thought.py`**: Implements a Tree of Thought (ToT) reasoning framework. It allows for the generation and expansion of thoughts, scoring them, and selecting the best thought. The thought tree structure is persisted in a JSON column within the SQL Server `AgentLogs` table, and its expansion can integrate with the RAG pipeline.
-   **`scripts/setup_sqlserver_schema.py`**: A utility script to programmatically create the SQL Server database schema. Note that this script uses `VARBINARY(MAX)` for embeddings and `NVARCHAR(MAX)` for JSON columns in `AgentLogs` for broader compatibility, differing from `migrations/sqlserver.sql` which targets SQL Server 2025 with native `VECTOR` type and `AS JSON` syntax.

-   **Data Flow**: 
    1.  Requests arrive at `server.py` via API endpoints defined in `routes/`.
    2.  For RAG queries, `rag_pipeline.py` generates embeddings and queries Milvus, Neo4j, and SQL Server (via `db_connectors.py` and `query_utils.py`).
    3.  Retrieved context is combined and passed to an LLM for response generation.
    4.  Plugins (managed by `plugins.py`) can be invoked at various stages for extended functionality.
    5.  Configuration is managed by `config.py` loading from `.env`.
    6.  Data consistency across databases is maintained by `cdc_consumer.py` which synchronizes changes from SQL Server to Milvus and Neo4j.
    7.  Complex agent reasoning can leverage `tree_of_thought.py` to explore and persist thought processes.

-   **Why**: Designed for extensibility (plugins), multimodal support, robust RAG capabilities, and integration with various database technologies for diverse data handling, with built-in data synchronization and advanced reasoning capabilities.

## Developer Workflows

-   **Setup**: 
    -   Python 3.9+ required.
    -   Ensure a `.env` file is present in the project root with necessary environment variables (see `README.md` for details).
    -   Install dependencies: `pip install -r requirements.txt`
    -   Start server: `uvicorn server:app --host 0.0.0.0 --port 8000` or `./start_gunicorn.sh` (for production-like).

-   **Testing**: 
    -   Tests are located in the `tests/` directory and are `pytest` compatible.
    -   Run all tests: `pytest`
    -   Test files generally match modules (e.g., `test_db_connectors.py` for `db_connectors.py`).

-   **Database Migrations**: 
    -   Milvus: `python migrations/milvus.py`
    -   Neo4j: `python migrations/neo4j_migrate.py`
    -   SQL Server: Use provided `.sql` scripts (e.g., `migrations/sqlserver.sql`) for SQL Server 2025 with native vector support, or run `python scripts/setup_sqlserver_schema.py` for broader compatibility.

## Project-Specific Patterns

-   **Authentication**: Currently, authentication is handled externally or not required for local development. The system is designed to integrate with external authentication mechanisms if needed.

-   **Plugins**: New agent logic or tools can be added by creating Python files in `plugins_folder/`. Each new plugin module should have a `register` function that takes the plugin registry as an argument and registers its functions. Example plugins are in `plugins.py`.

-   **API Conventions**: 
    -   API endpoints are modularized within the `routes/` directory.
    -   JSON is used for requests/responses. The `/ingest` endpoint supports form-data for file uploads.
    -   Detailed API documentation is available via Swagger UI (`/docs`) and ReDoc (`/redoc`) when the server is running.

-   **Multimodal Support**: The `/ingest` endpoint supports text, PDF, image (PNG, JPG, JPEG), and audio (MP3, WAV) file ingestion, with text extraction handled by `utils.py`.

## Integration Points

-   **External Services**: 
    -   **Milvus**: Vector database for semantic search. Connection details in `config.py` and `db_connectors.py`.
    -   **Neo4j**: Graph database for relational data and knowledge graphs. Connection details in `config.py` and `db_connectors.py`.
    -   **SQL Server**: Relational database for structured data. Connection details in `config.py` and `db_connectors.py`.
    -   **LLMs**: Integrated via the `transformers` library in `rag_pipeline.py` (e.g., `distilgpt2`).
    -   **Embedding Models**: Integrated via `sentence-transformers` in `rag_pipeline.py`.
    -   **Azure Key Vault**: Integrated for secret management in `utils.py`.

## Key Files & Directories

-   `server.py`: Main FastAPI application.
-   `rag_pipeline.py`: Core RAG logic.
-   `db_connectors.py`: Database connection management.
-   `plugins.py`: Plugin system core.
-   `plugins_folder/`: Directory for custom agent plugins.
-   `routes/`: Directory for API endpoint definitions.
-   `config.py`: Environment variable configuration.
-   `utils.py`: General utility functions.
-   `query_utils.py`: Centralized database queries.
-   `cdc_consumer.py`: Change Data Capture consumer.
-   `tree_of_thought.py`: Tree of Thought implementation.
-   `migrations/`: Database migration scripts.
-   `scripts/`: Utility scripts (e.g., `setup_sqlserver_schema.py`).
-   `tests/`: Project test suite.
-   `requirements.txt`: Python dependencies.
-   `pyproject.toml`: Project metadata and build system configuration.
-   `docker-compose.yml`: Docker Compose orchestration for services.
-   `Dockerfile`: Dockerfile for the application.
-   `start_gunicorn.sh`: Script to start the server with Gunicorn.
