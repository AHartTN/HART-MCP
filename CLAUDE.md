# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HART-MCP is an enterprise-grade Multi-Agent Control Plane with Retrieval-Augmented Generation, built on .NET 8 with Clean Architecture. The system features an Orchestrator Agent that delegates tasks to Specialist Agents, backed by a comprehensive RAG pipeline with vector database (Milvus), knowledge graph (Neo4j), and SQL Server with CLR functions.

## Architecture

The codebase follows Clean Architecture with these main layers:

- **API Layer** (`src/HART.MCP.API/`) - ASP.NET Core controllers, middleware, Program.cs entry point
- **Application Layer** (`src/HART.MCP.Application/`) - Business logic, agents, tools, CQRS commands/queries
- **Domain Layer** (`src/HART.MCP.Domain/`) - Core entities, value objects, domain interfaces
- **Infrastructure Layer** (`src/HART.MCP.Infrastructure/`) - Data access, external services, repositories
- **AI Layer** (`src/HART.MCP.AI/`) - LLM providers, embedding services, RAG orchestration
- **Shared Layer** (`src/HART.MCP.Shared/`) - Common utilities, exceptions, configuration models

### Key Components

**Multi-Agent System:**
- `OrchestratorAgent` - Breaks down tasks and delegates to specialists
- `SpecialistAgent` - Executes specific tasks using available tools
- Tool system with `IToolRegistry` and various implementations

**RAG Pipeline:**
- Vector search via Milvus integration (`IMilvusService`)
- Knowledge graph queries via Neo4j (`INeo4jService`) 
- SQL CLR functions for high-performance vector operations (`HART.MCP.SqlClr`)

**Database Design:**
- Entity Framework Core with migrations in `Infrastructure/Migrations/`
- Repository pattern with `IRepository<T>` and `BaseRepository<T>`
- Unit of Work pattern via `IUnitOfWork`

## Development Commands

### Building and Running

```bash
# Build the solution
dotnet build

# Run the API locally (development)
dotnet run --project src/HART.MCP.API

# Run with Docker
docker-compose -f deployment/docker-compose.csharp.yml up -d
```

### Testing

```bash
# Run all tests
dotnet test

# Run specific test projects
dotnet test tests/HART.MCP.UnitTests/
dotnet test tests/HART.MCP.IntegrationTests/
dotnet test tests/HART.MCP.EndToEndTests/

# Run tests with coverage
dotnet test --collect:"XPlat Code Coverage"
```

### Database Operations

```bash
# Add new migration
dotnet ef migrations add MigrationName --project src/HART.MCP.Infrastructure

# Update database
dotnet ef database update --project src/HART.MCP.Infrastructure

# Generate SQL scripts from migrations
dotnet ef migrations script --project src/HART.MCP.Infrastructure
```

### Code Quality

```bash
# Format code
dotnet format

# Build with detailed output
dotnet build --verbosity normal

# Security scan
dotnet list package --vulnerable
```

## Configuration

The application uses `appsettings.json` in the API project for configuration:

- **Database:** SQL Server connection string in `ConnectionStrings:DefaultConnection`
- **AI Services:** Gemini API configuration under `AI` section
- **Vector Database:** Milvus connection settings under `Milvus`
- **Knowledge Graph:** Neo4j connection under `Neo4j`

Environment variables are supported through `.env` files for Docker deployments.

## Agent and Tool Development

When adding new agents or tools:

1. **Tools** must implement `ITool` interface with `Name`, `Description`, and `ExecuteAsync` methods
2. **Register tools** in DI container via `ToolRegistrationExtensions`
3. **Agents** inherit from base agent classes in `Application/Agents/`
4. **Follow naming conventions:** Tools end with "Tool", Agents end with "Agent"

## Key Entry Points

- **API Controllers:** `src/HART.MCP.API/Controllers/McpController.cs` for main agent execution
- **Agent Registration:** `src/HART.MCP.Application/Extensions/ServiceCollectionExtensions.cs`
- **Tool Registration:** `src/HART.MCP.Infrastructure/Extensions/ToolRegistrationExtensions.cs`
- **Database Context:** `src/HART.MCP.Infrastructure/Persistence/ApplicationDbContext.cs`

## External Dependencies

The system requires these external services to be running:
- SQL Server 2022+ (with CLR enabled for quantum model features)
- Neo4j database for knowledge graph
- Milvus vector database
- Gemini API for LLM services

Use the provided Docker Compose files or connect to standalone instances per the configuration.