# MCP Server Setup Guide

This guide explains how to configure MCP (Model Context Protocol) servers for use with Claude Code in the HART-MCP project.

## Configuration File

The MCP configuration is located at `.config/mcp/mcp.json`. This file defines which MCP servers Claude Code can connect to.

## Adding Your MCP Servers

To add your Docker Hub MCP servers, edit the `.config/mcp/mcp.json` file and replace the example configurations with your actual server details.

### Example Configuration Structure

```json
{
  "mcpServers": {
    "server-name": {
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

### Common MCP Server Types

1. **Memory Server** - For persistent memory across conversations
2. **Sequential Thinking Server** - For step-by-step reasoning
3. **Azure MCP Server** - For Azure resource management  
4. **Filesystem Server** - For file operations
5. **Database Server** - For database operations

### Adding Your Docker Hub Servers

Replace the placeholder configurations in `mcp.json` with your actual server commands. For example:

```json
{
  "mcpServers": {
    "your-memory-server": {
      "command": "path/to/your/memory-server",
      "args": ["--config", "/path/to/config"],
      "env": {
        "STORAGE_PATH": "/data/memory"
      }
    },
    "your-azure-server": {
      "command": "path/to/your/azure-server", 
      "env": {
        "AZURE_CLIENT_ID": "your-client-id",
        "AZURE_CLIENT_SECRET": "your-client-secret",
        "AZURE_TENANT_ID": "your-tenant-id"
      }
    }
  }
}
```

### Environment Variables

For sensitive configuration like API keys, use environment variables:

1. Create a `.env` file in the project root
2. Add your environment variables:
   ```
   AZURE_CLIENT_ID=your-actual-client-id
   AZURE_CLIENT_SECRET=your-actual-client-secret
   AZURE_TENANT_ID=your-actual-tenant-id
   ```
3. Reference them in `mcp.json` using `${VAR_NAME}` syntax

### Testing Your Configuration

After adding your MCP servers:

1. Restart Claude Code
2. Check that your servers are recognized
3. Test functionality by using the tools provided by your MCP servers

### Troubleshooting

- Ensure all paths are correct and executable
- Check that required environment variables are set
- Verify network connectivity if servers run remotely
- Review server logs for connection issues

## Next Steps

Once configured, your MCP servers will be available as tools within the HART-MCP system, extending the capabilities of both the Orchestrator and Specialist agents.