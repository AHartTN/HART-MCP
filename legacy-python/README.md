# HART-MCP Legacy Python System 🐍

The original FastAPI-based RAG pipeline and AI services system. Designed for research, prototyping, and legacy integrations.

## 🚀 Quick Start

```bash
cd legacy-python
pip install -r requirements.txt
python server.py
```

## 📁 Directory Structure

```
legacy-python/
├── routes/                 # FastAPI route handlers
│   ├── agent.py           # AI agent operations
│   ├── feedback.py        # Feedback mechanisms
│   ├── health.py          # Health checks
│   ├── ingest.py          # Data ingestion
│   ├── mcp.py             # Multi-agent control plane
│   ├── retrieve.py        # Data retrieval
│   └── status.py          # System status
├── services/              # Core business services
│   ├── embedding_service.py    # Text embeddings
│   ├── database_search.py      # Database queries
│   ├── rag_orchestrator.py     # RAG coordination
│   ├── text_processing.py      # Text utilities
│   └── unified_database_service.py
├── plugins_folder/        # AI agent plugins
│   ├── agent_core.py      # Core agent functionality
│   ├── base_agent.py      # Agent base classes
│   ├── essential_tools.py # Agent tools
│   └── ...
├── utils/                 # Utility modules
│   ├── async_runner.py    # Async utilities
│   ├── database_interfaces.py
│   └── error_handlers.py
├── data/                  # Test data
├── logs/                  # Application logs
├── static/                # Web assets
├── temp/                  # Temporary files
├── uploads/               # File uploads
└── requirements.txt       # Dependencies
```

## 🔧 Configuration

Create a `.env` file in the `legacy-python` directory:

```bash
# SQL Server
SQL_SERVER_HOST=localhost
SQL_SERVER_DATABASE=master
SQL_SERVER_USERNAME=sa
SQL_SERVER_PASSWORD=YourPassword

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=hart_documents

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM Configuration
LLM_SOURCE=gemini  # Options: gemini, claude, llama, ollama
GEMINI_API_KEY=your_api_key
ANTHROPIC_API_KEY=your_api_key
```

## 🐳 Docker Deployment

```bash
# From project root
cd deployment
docker-compose --profile python up -d
```

## 📊 API Endpoints

The system exposes several REST API endpoints:

- **`/health`** - Health checks and database status
- **`/ingest`** - Data ingestion (text, PDF, images, audio)
- **`/retrieve`** - Vector similarity search
- **`/agent`** - AI agent operations (reflexion, tree-of-thought)
- **`/mcp`** - Multi-agent control plane
- **`/feedback`** - User feedback collection
- **`/status`** - Detailed system status

### Example Usage

```bash
# Health check
curl http://localhost:8000/health

# Ingest a document
curl -X POST http://localhost:8000/ingest \
  -F "file=@document.pdf" \
  -F "source_type=pdf"

# Query with RAG
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum computing?", "k": 5}'

# Agent reasoning
curl -X POST http://localhost:8000/agent/tree-of-thought \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain machine learning", "max_depth": 3}'
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_rag_pipeline.py
python -m pytest tests/test_mcp.py
python -m pytest tests/test_performance_security.py

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

## 📈 Performance & Monitoring

### Health Monitoring
```bash
# Check database connections
curl http://localhost:8000/health

# Detailed status with metrics
curl http://localhost:8000/status
```

### Logging
Logs are written to `logs/hart-mcp.log` with structured JSON format:

```python
import logging
logging.info("Processing query", extra={
    "query_id": "uuid", 
    "user_id": "user123",
    "response_time_ms": 250
})
```

## 🔌 Plugin Architecture

The system supports dynamic plugins loaded from `plugins_folder/`:

```python
# Example plugin
class MyPlugin:
    def __init__(self):
        self.name = "my_plugin"
    
    async def execute(self, context: dict) -> dict:
        # Plugin logic here
        return {"result": "processed"}

# Register plugin
plugins.register_plugin("my_plugin", MyPlugin())
```

## 🚀 Key Features

- **Modular RAG Pipeline**: Embedding → Vector Search → Context → LLM
- **Multi-Database**: SQL Server, Milvus, Neo4j integration
- **Multi-LLM Support**: Gemini, Claude, Llama, Ollama
- **Agent Framework**: Tree-of-thought, reflexion, BDI patterns
- **Change Data Capture**: Real-time data synchronization
- **Multimodal Ingestion**: Text, PDF, images, audio support
- **Production Ready**: Health checks, monitoring, error handling

## 📚 Technical Details

### RAG Pipeline Flow
1. **Text Processing** → Chunking, cleaning, metadata extraction
2. **Embedding Generation** → Sentence transformers, OpenAI embeddings  
3. **Vector Storage** → Milvus similarity search
4. **Graph Relationships** → Neo4j knowledge graph
5. **Context Building** → Relevant chunks + relationships
6. **LLM Generation** → Multi-provider inference
7. **Response Enhancement** → Plugin processing, fact-checking

### Database Schema
- **SQL Server**: Structured data, agent logs, system metrics
- **Milvus**: Vector embeddings, similarity search
- **Neo4j**: Knowledge graphs, entity relationships

### Agent Capabilities
- **Reflexion**: Self-correction and improvement cycles
- **Tree-of-Thought**: Multi-step reasoning trees
- **BDI Pattern**: Belief-Desire-Intention agent architecture
- **Plugin System**: Extensible tool integration

## 🔒 Security

- Input validation and sanitization
- SQL injection protection via parameterized queries
- Rate limiting on API endpoints
- Secure file upload handling
- Environment-based secrets management

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database services
   docker ps | grep -E "(milvus|neo4j|postgres)"
   
   # Test connections
   curl http://localhost:8000/health
   ```

2. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Performance Issues**
   ```bash
   # Check system resources
   curl http://localhost:8000/status
   
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   ```

## 📝 Migration to Enterprise C#

When ready to migrate to the enterprise system:

1. **Data Export**: Use migration scripts in `shared-resources/migrations/`
2. **Configuration Mapping**: Convert `.env` to `appsettings.json`
3. **API Compatibility**: Enterprise system provides equivalent REST endpoints
4. **Gradual Migration**: Run both systems during transition period

---

**Next Steps**: Consider migrating to the enterprise C# system for production deployments with enhanced performance, scalability, and maintainability.