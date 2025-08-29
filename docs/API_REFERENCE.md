# HART-MCP API Reference

## Base URL
- Development: `http://localhost:8080`
- Production: `https://your-domain.com`

## Authentication
All API endpoints require authentication via API key:
```http
Authorization: Bearer your-api-key
```

## Endpoints

### Mission Control

#### Execute Mission
Execute a multi-agent mission with streaming progress.

```http
POST /api/mcp
Content-Type: application/json

{
  "query": "Analyze customer feedback and suggest improvements",
  "agentId": 1
}
```

**Response:**
```json
{
  "mission_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Stream Mission Progress
Get real-time updates on mission execution.

```http
GET /api/mcp/stream/{missionId}
Accept: text/event-stream
```

**Server-Sent Events:**
```
data: {"status": "started", "agent": "Orchestrator_1", "query": "..."}

data: {"iteration": 1, "orchestrator_thinking": "I need to break this down..."}

data: {"orchestrator_tool_used": "DelegateToSpecialistTool", "orchestrator_tool_result": "..."}

data: {"status": "completed", "result": "Analysis complete: ..."}
```

### Document Management

#### Ingest Document
Add documents to the RAG system with automatic chunking and embedding.

```http
POST /api/ingest/document
Content-Type: application/json

{
  "content": "Your document content here...",
  "title": "Important Document",
  "contentType": "text/markdown",
  "source": "api_upload",
  "chunkSize": 1000,
  "overlap": 100
}
```

**Response:**
```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "chunks_created": 15,
  "status": "success"
}
```

#### Retrieve Similar Documents
Find documents similar to a query using vector similarity.

```http
GET /api/retrieve/similar?query=climate%20change&limit=10&threshold=0.7
```

**Response:**
```json
{
  "results": [
    {
      "document_id": "123e4567-e89b-12d3-a456-426614174000",
      "score": 0.85,
      "content": "Document chunk content...",
      "metadata": {
        "title": "Climate Report 2023",
        "source": "research_papers"
      }
    }
  ],
  "total": 1
}
```

### Agent Operations

#### Direct Agent Query
Query an agent directly without full mission orchestration.

```http
POST /api/agent/query
Content-Type: application/json

{
  "query": "What is the capital of France?",
  "agentType": "specialist",
  "tools": ["RAGTool", "FinishTool"]
}
```

**Response:**
```json
{
  "response": "The capital of France is Paris.",
  "agent": "Specialist_1",
  "tools_used": ["RAGTool"],
  "execution_time_ms": 1250
}
```

### System Endpoints

#### Health Check
Check system health and component status.

```http
GET /health
```

**Response:**
```json
{
  "status": "Healthy",
  "checks": {
    "database": "Healthy",
    "milvus": "Healthy", 
    "neo4j": "Healthy",
    "llm_service": "Healthy"
  },
  "duration": "00:00:00.045"
}
```

#### System Status
Get detailed system information and statistics.

```http
GET /api/status
```

**Response:**
```json
{
  "version": "1.0.0",
  "uptime": "2 days, 5 hours, 30 minutes",
  "statistics": {
    "total_missions": 1250,
    "active_missions": 3,
    "total_documents": 50000,
    "total_embeddings": 500000
  },
  "components": {
    "sql_server": "Connected",
    "milvus": "Connected (rag_collection: 500K vectors)",
    "neo4j": "Connected (15K nodes, 45K relationships)"
  }
}
```

#### Submit Feedback
Submit feedback on agent responses for system improvement.

```http
POST /api/feedback
Content-Type: application/json

{
  "missionId": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 4,
  "feedback": "Good response but could be more detailed",
  "category": "quality"
}
```

**Response:**
```json
{
  "feedback_id": "fb123456-7890-abcd-ef12-345678901234",
  "status": "received",
  "message": "Thank you for your feedback"
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request body is malformed",
    "details": "JSON parsing error at line 5"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "path": "/api/mcp"
}
```

### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_REQUEST` | Request validation failed |
| `MISSION_NOT_FOUND` | Mission ID not found |
| `AGENT_ERROR` | Agent execution failed |
| `DATABASE_ERROR` | Database operation failed |
| `LLM_ERROR` | LLM service error |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

## Rate Limiting

API requests are limited per user:
- **Free Tier**: 100 requests/hour
- **Pro Tier**: 1000 requests/hour  
- **Enterprise**: Custom limits

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
```

## SDKs and Client Libraries

### C# SDK
```csharp
var client = new HartMcpClient("https://api.hart-mcp.com", "your-api-key");

var mission = await client.ExecuteMissionAsync(new McpRequest 
{
    Query = "Analyze sales data",
    AgentId = 1
});

await foreach (var update in client.StreamMissionAsync(mission.MissionId))
{
    Console.WriteLine($"Status: {update.Status}");
}
```

### Python SDK
```python
import hart_mcp

client = hart_mcp.Client(api_key="your-api-key")

mission = client.execute_mission({
    "query": "Analyze sales data",
    "agentId": 1
})

for update in client.stream_mission(mission["mission_id"]):
    print(f"Status: {update['status']}")
```

### JavaScript SDK
```javascript
import { HartMcpClient } from '@hart-mcp/client';

const client = new HartMcpClient({
  baseUrl: 'https://api.hart-mcp.com',
  apiKey: 'your-api-key'
});

const mission = await client.executeMission({
  query: 'Analyze sales data',
  agentId: 1
});

const stream = client.streamMission(mission.mission_id);
for await (const update of stream) {
  console.log('Status:', update.status);
}
```

## Webhooks

Configure webhooks to receive mission completion notifications:

```http
POST /api/webhooks
Content-Type: application/json

{
  "url": "https://your-app.com/webhook",
  "events": ["mission.completed", "mission.failed"],
  "secret": "webhook-secret"
}
```

**Webhook Payload:**
```json
{
  "event": "mission.completed",
  "mission_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "query": "Original query",
    "result": "Mission result",
    "duration_ms": 15000
  }
}
```

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:
- Development: `http://localhost:8080/api/openapi.json`
- Interactive docs: `http://localhost:8080/api/docs`