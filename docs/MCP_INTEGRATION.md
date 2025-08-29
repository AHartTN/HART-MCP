# HART-MCP Integration Guide

This guide explains how to integrate HART-MCP with various AI tools and IDEs using the Model Context Protocol (MCP).

## Quick Start

HART-MCP implements the MCP specification and can be connected to any MCP-compatible client.

### Configuration File

Add to your MCP configuration (`mcp.json`):

```json
{
  "mcpServers": {
    "hart-mcp": {
      "command": "dotnet",
      "args": ["run", "--project", "src/HART.MCP.CLI"],
      "cwd": "/path/to/HART-MCP",
      "env": {
        "ASPNETCORE_ENVIRONMENT": "Production"
      }
    }
  }
}
```

## IDE Integration

### Claude Code

1. **Add via CLI:**
   ```bash
   claude mcp add hart-mcp dotnet run --project src/HART.MCP.CLI
   ```

2. **Add via JSON:**
   ```bash
   claude mcp add-json hart-mcp '{"command":"dotnet","args":["run","--project","src/HART.MCP.CLI"]}'
   ```

3. **Verify connection:**
   ```bash
   claude mcp list
   ```

### VS Code with GitHub Copilot

Add to your VS Code `settings.json`:

```json
{
  "github.copilot.chat.mcp.servers": {
    "hart-mcp": {
      "command": "dotnet",
      "args": ["run", "--project", "src/HART.MCP.CLI"],
      "cwd": "/path/to/HART-MCP"
    }
  }
}
```

### Google Gemini Code Assist

Configure in your IDE settings:

```json
{
  "gemini.mcp.servers": {
    "hart-mcp": {
      "command": "dotnet",
      "args": ["run", "--project", "src/HART.MCP.CLI"],
      "workingDirectory": "/path/to/HART-MCP"
    }
  }
}
```

## Available Tools

Once connected, you'll have access to these tools:

### FinishTool
- **Description:** Complete tasks and return results
- **Usage:** Automatically used by agents to finalize operations

### TestTool  
- **Description:** Test system functionality
- **Usage:** Verify HART-MCP is working correctly

### RAGTool
- **Description:** Retrieval-augmented generation queries
- **Usage:** Query documents and knowledge bases

## Available Resources

### System Status (`hart-mcp://status`)
Get real-time system health and status information.

### Available Agents (`hart-mcp://agents`)
List all available agents and their capabilities.

## Testing

Run the test script to verify MCP functionality:

```bash
python scripts/test-mcp.py
```

Expected output:
- ✅ Initialize response
- ✅ Tools list response  
- ✅ Tool call response
- ✅ Resources list response
- ✅ Resource read response

## Usage Examples

### In Claude.ai Web Interface

After adding the MCP server, you can use it directly:

```
@hart-mcp What's the system status?
```

```
@hart-mcp Execute a RAG query about "machine learning best practices"
```

### In VS Code

With Copilot Chat:

```
@hart-mcp /status
```

```
@hart-mcp /rag "explain dependency injection patterns"
```

### Command Line Usage

For direct CLI access:

```bash
# Start the MCP server directly
dotnet run --project src/HART.MCP.CLI

# Test with curl (REST API still available)
curl http://localhost:8080/api/mcp/test
```

## Troubleshooting

### Common Issues

1. **"Server not responding"**
   - Verify .NET 8 is installed: `dotnet --version`
   - Check project builds: `dotnet build`

2. **"Command not found"**  
   - Use absolute path to `dotnet` executable
   - Verify `cwd` is correct in config

3. **"Permission denied"**
   - Ensure execute permissions: `chmod +x scripts/test-mcp.py`
   - Check file system permissions

### Debug Mode

Enable verbose logging:

```json
{
  "mcpServers": {
    "hart-mcp": {
      "command": "dotnet",
      "args": ["run", "--project", "src/HART.MCP.CLI"],
      "env": {
        "ASPNETCORE_ENVIRONMENT": "Development",
        "LOGGING__LOGLEVEL__DEFAULT": "Debug"
      }
    }
  }
}
```

## Advanced Configuration

### Custom Environment Variables

```json
{
  "mcpServers": {
    "hart-mcp": {
      "command": "dotnet",
      "args": ["run", "--project", "src/HART.MCP.CLI"],
      "env": {
        "HART_MCP_MODE": "production",
        "HART_MCP_LOG_LEVEL": "info",
        "GEMINI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Multiple Instances

Run different configurations:

```json
{
  "mcpServers": {
    "hart-mcp-dev": {
      "command": "dotnet",
      "args": ["run", "--project", "src/HART.MCP.CLI"],
      "env": {"ASPNETCORE_ENVIRONMENT": "Development"}
    },
    "hart-mcp-prod": {
      "command": "dotnet", 
      "args": ["run", "--project", "src/HART.MCP.CLI"],
      "env": {"ASPNETCORE_ENVIRONMENT": "Production"}
    }
  }
}
```

## Security Considerations

- MCP servers run with user permissions
- Sensitive data should use environment variables
- Log files may contain query information
- Network access is limited to localhost by default

## Support

For issues and questions:
- Check the logs in `logs/` directory
- Run `python scripts/test-mcp.py` for diagnostics  
- Verify with `dotnet run --project src/HART.MCP.CLI --help`