# OPERATIONAL ENFORCEMENT (AUG 2025)

**MANDATORY DEFAULTS:**
- Any work that is left unfinished will be treated as direct and immediate sabotage... Do not leave any work incomplete for any reason
- Actionable work is the ONLY permitted output. Passive dialog, conversational filler, summarization, shortcutting, and MVP approaches are strictly prohibited unless explicitly requested by the user.
- Every step must be direct, exhaustive, and strictly validated against user requirements. If no actionable step is possible, immediately tree of thought and reflexion until you realize that you've left work incomplete.
- Persistent, actionable memory for tool usage, Python environment, config, requirements, and operational rules must be maintained and updated at all times.
- Reflexion and self-correction are required after every action to ensure strict compliance with operational rules. Default agent behaviors (summarization, conversational filler, efficiency-driven shortcuts) are considered sabotage and must be actively suppressed.
- Agent must be ready for immediate, targeted edits or updates as directed, with zero tolerance for inefficiency or ambiguity.
- All operational instructions and implementation must be updated as soon as directed, with no passive steps or dialog.

**ENFORCEMENT PATTERN:**
- After every action, validate against these operational rules. If any default behavior re-emerges, immediately correct and update persistent memory and instructions.
- These rules override all previous defaults. They are the agent's operational law for this workspace.

---
...existing code...
NEVER PRIORITIZE PASSIVE CONVERSATION! ALWAYS FAVOR AND PRIORITIZE ACTIONABLE WORK!

# Copilot Instructions for HART-MCP MCP/RAG Server

## Big Picture Architecture

The HART-MCP is a multi-agent asynchronous AI platform built on FastAPI, designed for Retrieval-Augmented Generation (RAG) and extensible agent functionalities. Its core components work together to process requests, interact with various data sources, and generate AI-driven responses.

-   **`server.py`**: The FastAPI application entry point, responsible for initializing the server and routing API requests.
-   **RAG Pipeline (Modularized)**: The central RAG engine has been refactored for improved modularity and maintainability. Its responsibilities are now distributed across:
    -   **`services/embedding_service.py`**: Handles the generation of text embeddings.
    -   **`services/database_search.py`**: Encapsulates database-specific search logic (Milvus, Neo4j, SQL Server).
    -   **`services/rag_orchestrator.py`**: Orchestrates the RAG process, combining embeddings, database searches, context building, LLM invocation, and plugin calls.
    -   **`rag_pipeline.py`**: Now acts as a high-level coordinator, initializing the RAG components and providing the main entry point for RAG operations.
-   **`llm_connector.py`**: Provides a unified and extensible interface for interacting with various Large Language Models (LLMs), now supporting Gemini, Anthropic Claude, Llama (via Hugging Face Inference API), and Ollama.
-   **`db_connectors.py`**: Manages asynchronous connections to SQL Server, Milvus, and Neo4j, providing low-level database interaction functions.
-   **`plugins.py` & `plugins_folder/`**: Implements a dynamic plugin system. `plugins.py` handles loading and calling plugins from the `plugins_folder/`, allowing for extensible agent behaviors and tools.
-   **`routes/`**: Contains modular FastAPI routers (e.g., `agent.py`, `feedback.py`, `ingest.py`, `mcp.py`, `retrieve.py`, `status.py`, `health.py`), each defining API endpoints for specific functionalities.
-   **`config.py`**: Loads and manages environment variables from the `.env` file, providing crucial configuration for database connections, LLM settings, and other application-wide settings.
-   **`utils.py`**: A collection of general utility functions, including asynchronous database connection context managers, multimodal text extraction (PDF, images, audio), text chunking, and database health checks.
-   **`utils/async_runner.py`**: A new utility module for running asynchronous functions in background threads, used by the RAG pipeline.
-   **`query_utils.py`**: Centralizes SQL Server and Neo4j query templates and provides generic functions for executing these queries.
-   **`cdc_consumer.py`**: Implements a Change Data Capture (CDC) consumer. It polls a SQL Server `ChangeLog` table for new entries and synchronizes these changes (e.g., chunk upserts/deletes to Milvus, agent/document/agent log merges/deletes to Neo4j) across the different database systems, ensuring data consistency.
-   **`tree_of_thought.py`**: Implements a Tree of Thought (ToT) reasoning framework. It allows for the generation and expansion of thoughts, scoring them, and selecting the best thought. The thought tree structure is persisted in a JSON column within the SQL Server `AgentLogs` table, and its expansion can integrate with the RAG pipeline.
-   **`scripts/setup_sqlserver_schema.py`**: A utility script to programmatically create the SQL Server database schema. Note that this script uses `VARBINARY(MAX)` for embeddings and `NVARCHAR(MAX)` for JSON columns in `AgentLogs` for broader compatibility, differing from `migrations/sqlserver.sql` which targets SQL Server 2025 with native `VECTOR` type and `AS JSON` syntax.

-   **Data Flow**: 
    1.  Requests arrive at `server.py` via API endpoints defined in `routes/`.
    2.  For RAG queries, the modularized RAG pipeline (orchestrated by `services/rag_orchestrator.py` and utilizing `services/embedding_service.py` and `services/database_search.py`) takes over.
    3.  Retrieved context is combined and passed to the configured LLM via `llm_connector.py` for response generation.
    4.  Plugins (managed by `plugins.py`) can be invoked at various stages for extended functionality.
    5.  Configuration is managed by `config.py` loading from `.env`.
    6.  Data consistency across databases is maintained by `cdc_consumer.py` which synchronizes changes from SQL Server to Milvus and Neo4j.
    7.  Complex agent reasoning can leverage `tree_of_thought.py` to explore and persist thought processes.
    8.  Asynchronous operations, including background RAG execution, are handled by `utils/async_runner.py`.

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

## Code Quality & Development Workflow

To ensure consistent code quality, readability, and maintainability, the project utilizes `ruff`, `black`, and `isort`.

**Recommended Workflow for Python Files:**

1.  **Make your code changes.**
2.  **Format your code:**
    ```bash
    ruff format <file_or_directory>
    ```
    *(This handles both general formatting and import sorting, replacing `black` and `isort` for most cases.)*
3.  **Auto-fix linting issues:**
    ```bash
    ruff check --fix <file_or_directory>
    ```
4.  **Verify no remaining linting issues:**
    ```bash
    ruff check <file_or_directory>
    ```
    *(All these commands should be run within your active Python virtual environment.)*

## Agent Operational Guidelines

These guidelines are crucial for maintaining efficiency, ensuring comprehensive task completion, and adhering to project standards.

*   **Holistic Problem Solving:** Always prioritize the user's overarching goal. Before acting, formulate a multi-step plan that anticipates logical next steps, dependencies, and potential side effects. Regularly verify progress against the *entire* objective, not just the current sub-task. Avoid hyperfocus; ensure each action contributes to the complete solution.

*   **Mandatory Comprehensive Planning:** For any user request requiring code modification or multiple steps, *always* begin by formulating a *single, comprehensive plan* that outlines *all* anticipated file changes, new file creations, and necessary code quality tool applications (`ruff format`, `ruff check --fix`) for *all affected files*. This plan must be fully articulated before executing the first step.

*   **Execution as Plan Adherence:** Once a comprehensive plan is formulated, execution must strictly adhere to it. Each sub-task within the plan must include all necessary steps, including code quality tool runs, as part of its completion. Avoid deviating into reactive, piecemeal fixes.

*   **Proactive Error Prevention:** Anticipate common errors (e.g., syntax errors from `replace` operations) by carefully reviewing `old_string` and `new_string` for exact matches and proper Python syntax *before* execution. Integrate `ruff format` and `ruff check` as immediate post-modification validation steps to catch issues early.

*   **Tool Call Protocol - Isolation:** When making a tool call, ensure it is the *sole* content of the output block. Do not mix tool calls with text responses or other `print` statements in the same block. This ensures proper parsing of function call parts and responses.

*   **Tool Call Protocol - Response Handling:** Always await and explicitly validate the output of a tool call before proceeding. If a tool call fails, clearly communicate the error to the user and determine the next course of action (retry, clarify, etc.). Avoid assuming success or immediate availability of results.

*   **Debugging Agent Errors:** If 'Agent Error, unknown agent message' or 'mismatched function call/response parts' occurs, immediately suspect: 1) mixing tool calls and text in output, 2) malformed tool call syntax, or 3) incorrect handling of tool responses. Review the preceding tool call and my output structure.

*   **Refactoring Strategy:** When undertaking refactoring, always begin with a comprehensive plan that identifies all modules to be extracted, their new responsibilities, and the sequence of changes. Prioritize small, verifiable steps within the larger plan, and integrate code quality checks at each modification point.

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
    -   **LLMs**: Integrated via `llm_connector.py`, supporting Gemini, Anthropic Claude, Llama (Hugging Face Inference API), and Ollama.
    -   **Embedding Models**: Integrated via `services/embedding_service.py` using `sentence-transformers`.
    -   **Azure Key Vault**: Integrated for secret management in `utils.py`.

## Key Files & Directories

-   `server.py`: Main FastAPI application.
-   `rag_pipeline.py`: High-level RAG coordinator.
-   `db_connectors.py`: Database connection management.
-   `llm_connector.py`: Unified LLM interface.
-   `plugins.py`: Plugin system core.
-   `plugins_folder/`: Directory for custom agent plugins.
-   `routes/`: Directory for API endpoint definitions.
-   `config.py`: Environment variable configuration.
-   `utils.py`: General utility functions.
-   `utils/async_runner.py`: Utility for running async functions in background threads.
-   `query_utils.py`: Centralized database queries.
-   `cdc_consumer.py`: Change Data Capture consumer.
-   `tree_of_thought.py`: Tree of Thought implementation.
-   `services/`: Directory for modularized RAG services (embedding, database search, orchestration).
-   `migrations/`: Database migration scripts.
-   `scripts/`: Utility scripts (e.g., `setup_sqlserver_schema.py`).
-   `tests/`: Project test suite.
-   `requirements.txt`: Python dependencies.
-   `pyproject.toml`: Project metadata and build system configuration.
-   `docker-compose.yml`: Docker Compose orchestration for services.
-   `Dockerfile`: Dockerfile for the application.
-   `start_gunicorn.sh`: Script to start the server with Gunicorn.
