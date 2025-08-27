# HART-MCP: Multi-Agent Asynchronous AI Platform

## Project Overview
HART-MCP (Multi-Agent Control Plane) is an innovative and extensible platform designed to serve as a multi-agent asynchronous server. It forms the core of a new AI agent platform, leveraging advanced technologies like LangGraph (implied by design for complex agent workflows) to facilitate complex interactions and coordinated behaviors among various AI agents. This platform provides a robust and scalable foundation for developing and deploying sophisticated Retrieval-Augmented Generation (RAG) solutions and managing diverse AI agent functionalities.

## Architecture
The HART-MCP server is built with a modular and asynchronous architecture, primarily using FastAPI. Key components include:

*   **`server.py`**: The main entry point for the FastAPI application, responsible for initializing the server and routing incoming requests to specific API endpoints.
*   **`rag_pipeline.py`**: The core of the RAG system. It orchestrates the process of generating embeddings, performing vector searches across multiple data sources (Milvus, Neo4j, SQL Server 2025 with native vector search), combining retrieved context, and generating a final response using the standardized Gemini Pro Language Model (LLM) via `llm_connector.py`. It also integrates with the plugin system.
*   **`db_connectors.py`**: Centralizes the logic for establishing and managing connections to the various databases (SQL Server, Milvus, Neo4j). It provides asynchronous functions for connecting and performing basic database operations.
*   **`plugins.py`**: Implements a dynamic plugin system that allows for extending the server's capabilities. Plugins are loaded from the `plugins_folder/` and can be called by name to execute custom agent logic or tools.
*   **`routes/`**: A directory containing modular FastAPI routers (e.g., `agent.py`, `feedback.py`, `ingest.py`, `mcp.py`, `retrieve.py`). Each file defines API endpoints for specific functionalities, promoting a clean and organized API structure.
*   **`config.py`**: Manages the loading and parsing of environment variables from a `.env` file, providing critical configuration parameters for database connections and other settings.
*   **`utils.py`**: A collection of general utility functions, including asynchronous context managers for database connections, file processing (text extraction from various formats), text chunking, and database health checks.
*   **`query_utils.py`**: Centralizes SQL Server and Neo4j query templates as constants and provides generic functions for executing these queries, including support for SQL Server 2025's native vector and JSON types, ensuring consistency and reusability.
*   **`cdc_consumer.py`**: Implements a Change Data Capture (CDC) consumer that polls a SQL Server `ChangeLog` table for new entries. It processes these changes to synchronize data (e.g., chunks, agent logs, agents, documents) across Milvus and Neo4j, ensuring data consistency across the different database systems.
*   **`tree_of_thought.py`**: Implements a Tree of Thought (ToT) reasoning framework. It allows for the generation and expansion of thoughts, scoring them, and selecting the best thought. The thought tree structure is persisted in a JSON column within the SQL Server `AgentLogs` table, and its expansion can integrate with the RAG pipeline.

## Data Flow
Requests enter the system via the API endpoints defined in `routes/`. These requests are then processed by the `server.py` which directs them to the appropriate handler. For RAG-related queries, the `rag_pipeline.py` takes over, generating embeddings, querying Milvus (vector search), Neo4j (graph data), and SQL Server (structured data) via `db_connectors.py` and `query_utils.py`. The retrieved context is then combined and fed to an LLM to generate a comprehensive response. The system also supports dynamic extension through `plugins.py`. Data consistency across databases is maintained by `cdc_consumer.py` which synchronizes changes from SQL Server to Milvus and Neo4j.

## Installation

### Prerequisites
*   Python 3.9+
*   Docker (recommended for containerized deployment of dependencies like Milvus, Neo4j, SQL Server)

### Local Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-org/HART-MCP.git
    cd HART-MCP
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv .venv
    # On Windows
    .venv\Scripts\activate
    # On macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration
The project relies on environment variables loaded from a `.env` file at the root of the project using `python-dotenv`. This file is crucial for database connections and other settings.

**Required Environment Variables (to be placed in your `.env` file):**

#### SQL Server
*   `SQL_SERVER_DRIVER`: ODBC Driver for SQL Server (e.g., `{ODBC Driver 17 for SQL Server}`).
*   `SQL_SERVER_SERVER`: SQL Server instance address (e.g., `localhost,1433`).
*   `SQL_SERVER_DATABASE`: Database name (e.g., `master`).
*   `SQL_SERVER_UID` or `SQL_SERVER_USERNAME`: Username for SQL Server authentication.
*   `SQL_SERVER_PWD` or `SQL_SERVER_PASSWORD`: Password for SQL Server authentication.

#### Milvus
*   `MILVUS_HOST`: Milvus server host (e.g., `localhost`).
*   `MILVUS_PORT`: Milvus server port (e.g., `19530`).
*   `MILVUS_USER` or `MILVUS_UID`: Username for Milvus authentication (if applicable).
*   `MILVUS_PASSWORD` or `MILVUS_PWD`: Password for Milvus authentication (if applicable).
*   `MILVUS_COLLECTION`: Default Milvus collection name.

#### Neo4j
*   `NEO4J_URI`: Neo4j server URI (e.g., `bolt://localhost:7687`).
*   `NEO4J_USER`: Username for Neo4j authentication.
*   `NEO4J_PASSWORD`: Password for Neo4j authentication.

## Running the Server
The server can be run using Gunicorn, and Docker Compose is used for orchestrating the application and its dependencies.

### Using Docker Compose (Recommended)
```bash
docker-compose up --build
```

### Local Development Server (without Docker Compose for application)
Ensure all necessary database services (Milvus, Neo4j, SQL Server) are running and accessible.
```bash
./start_gunicorn.sh
```
Alternatively, for direct FastAPI development:
```bash
python server.py
```

## API Endpoints
The HART-MCP server exposes several API endpoints, organized by functionality:
*   `/agent`: For AI agent-related operations (e.g., reflexion, Tree of Thought, BDI).
*   `/feedback`: For handling feedback mechanisms.
*   `/health`: For health checks and status monitoring of integrated databases.
*   `/ingest`: For data ingestion processes (supports multimodal input: text, PDF, images, audio).
*   `/mcp`: Core Multi-Agent Control Plane operations, including agent creation and logging.
*   `/retrieve`: For data retrieval and querying, specifically from Milvus.
*   `/status`: For detailed status information of integrated databases.

Detailed API documentation can be accessed at `/docs` or `/redoc` once the server is running.

## Testing
The project includes a comprehensive test suite using `pytest`.

To run tests:
```bash
pytest
```

## Dependencies
Key dependencies include:
*   `fastapi`: Web framework for the server.
*   `uvicorn`: ASGI server for running FastAPI applications locally.
*   `python-dotenv`: For loading environment variables.
*   `pyodbc`: SQL Server database connector.
*   `pymilvus`: Milvus vector database client.
*   `neo4j`: Neo4j graph database driver.
*   `sentence-transformers`: For generating text embeddings.
*   `transformers`: For LLM integration (e.g., `distilgpt2`).
*   `PyPDF2`, `pytesseract`, `Pillow`: For PDF and image text extraction.
*   `speech_recognition`: For audio transcription.
*   `ruff`, `black`, `isort`: For code formatting and linting.
*   `pytest-asyncio`: For asynchronous testing.
*   `gunicorn`: WSGI HTTP Server.
*   `marshmallow`, `pydantic`: For JSON schema validation and data parsing.
*   `azure-identity`, `azure-keyvault-secrets`: For Azure Key Vault integration (partially implemented).

## Contributing
Contributions are welcome! Please refer to the `CONTRIBUTING.md` (to be created) for guidelines.

## Codebase Cleanup and Refinement

This section documents the ongoing efforts to maintain and improve the codebase's quality, readability, and maintainability.

### Effort Done

As part of a recent cleanup initiative, the following actions have been completed:

*   **Automated Formatting:** Applied `isort` for import sorting and `black` for code formatting across the entire codebase, ensuring consistent style and adherence to PEP 8.
*   **Linting and Static Analysis:** Utilized `ruff` to identify and fix various linting issues, including:
    *   Resolution of undefined name errors by adding missing imports (e.g., `traceback` module).
    *   Correction of redundant code definitions (e.g., duplicate `__init__` method in `plugins_folder/agent_core.py`).
    *   Restructuring of imports to ensure they are at the module level and at the top of files (e.g., in `tests/test_agent.py`).
    *   Removal of duplicate test function definitions in `tests/test_agent.py` to eliminate redefinition errors.

These steps have significantly improved the code's consistency and addressed many common Python style and linting concerns.

### Effort Needed

Based on a recent "Tree of Thought and Reflexion" exercise, the following areas have been identified for further cleanup and refinement. These tasks aim to enhance code quality, maintainability, and overall robustness:

1.  **Configuration Review:**
    *   **Task:** Examine `config.py` and other files for any remaining hardcoded values (e.g., connection strings, API keys, magic numbers).
    *   **Goal:** Ensure all configurable parameters are properly externalized and loaded from environment variables or a dedicated configuration system.

2.  **Unused Code/Dependencies:**
    *   **Task:** Conduct a deeper analysis (potentially using tools like `deptry` or `pip-autoremove`) to identify and remove truly unused dependencies listed in `requirements.txt`.
    *   **Task:** Perform a manual or automated scan for dead code (functions, classes, or entire files) that are no longer called or needed.
    *   **Goal:** Reduce project size, improve build times, and eliminate potential security vulnerabilities from unused libraries.

3.  **Error Handling Enhancement:**
    *   **Task:** Standardize error handling mechanisms across the application, especially for interactions with databases (SQL Server, Milvus, Neo4j) and external services.
    *   **Task:** Ensure error messages are informative for debugging and user-facing errors are handled gracefully.
    *   **Goal:** Improve application stability and provide clearer feedback on failures.

4.  **Documentation (Docstrings & Comments):**
    *   **Task:** Add or improve comprehensive docstrings for all functions, classes, and modules, explaining their purpose, arguments, and return values.
    *   **Task:** Review existing comments to ensure they explain *why* a particular piece of code is written, rather than just *what* it does.
    *   **Task:** Update the `README.md` with any new features, installation steps, or operational details.
    *   **Goal:** Enhance code readability, maintainability, and onboarding for new developers.

5.  **Code Readability & Simplicity:**
    *   **Task:** Refactor overly complex functions or methods into smaller, more focused units.
    *   **Task:** Break down large functions into smaller, more manageable ones to improve clarity and testability.
    *   **Task:** Review variable and function naming conventions for clarity and consistency.
    *   **Goal:** Improve code comprehension and reduce the likelihood of introducing bugs.

6.  **Test Coverage & Clarity:**
    *   **Task:** Review the existing test suite for clarity, robustness, and completeness.
    *   **Task:** Identify areas lacking sufficient test coverage and write new unit, integration, or end-to-end tests as appropriate.
    *   **Goal:** Ensure the application's functionality is thoroughly validated and changes do not introduce regressions.

7.  **Logging Consistency:**
    *   **Task:** Establish and enforce consistent logging practices across the entire application (e.g., standard log levels, message formats, inclusion of relevant context).
    *   **Task:** Add more informative log messages at critical points for better debugging and monitoring in production environments.
    *   **Goal:** Provide better visibility into application behavior and simplify troubleshooting.

8.  **Plugin Architecture Review:**
    *   **Task:** Examine the `plugins_folder` and `plugins.py` to ensure the plugin loading and execution mechanism is robust, secure, and easily extensible.
    *   **Task:** Consider defining clear interfaces or abstract base classes for plugins to guide future development and ensure compatibility.
    *   **Goal:** Facilitate easier development and integration of new functionalities through plugins.

9.  **SQL Query Management:**
    *   **Task:** Review `query_utils.py` to ensure all SQL queries are well-organized, consistently parameterized, and secure against SQL injection vulnerabilities.
    *   **Task:** Evaluate the feasibility and benefits of introducing an Object-Relational Mapper (ORM) for SQL Server interactions, especially if the project's scale and complexity are expected to grow.
    *   **Goal:** Improve data access layer maintainability, security, and developer productivity.
