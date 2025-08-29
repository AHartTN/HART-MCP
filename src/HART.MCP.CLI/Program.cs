using System.Text.Json;
using System.Text.Json.Serialization;
using HART.MCP.Application.Tools;
using HART.MCP.Application.Services;
using HART.MCP.AI.Services;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace HART.MCP.CLI;

public class Program
{
    public static async Task Main(string[] args)
    {
        var services = new ServiceCollection();
        ConfigureServices(services);
        var serviceProvider = services.BuildServiceProvider();

        var mcpServer = new McpServer(serviceProvider);
        await mcpServer.RunAsync();
    }

    private static void ConfigureServices(IServiceCollection services)
    {
        services.AddLogging(builder => builder.AddConsole().SetMinimumLevel(LogLevel.Error));
        services.AddSingleton<IProjectStateService, ProjectStateService>();
        services.AddSingleton<ILlmService, HART.MCP.Application.Services.LlmService>();
        services.AddSingleton<HART.MCP.AI.Abstractions.IEmbeddingService, HART.MCP.AI.Services.EmbeddingService>();
        
        // Infrastructure services (optional - only if databases are available)
        // Infrastructure project disabled due to API compatibility issues
        // services.AddSingleton<HART.MCP.Infrastructure.VectorDatabase.IMilvusService, HART.MCP.Infrastructure.VectorDatabase.MilvusService>();
        // services.AddSingleton<HART.MCP.Infrastructure.KnowledgeGraph.INeo4jService, HART.MCP.Infrastructure.KnowledgeGraph.Neo4jService>();
        // services.AddSingleton<HART.MCP.Infrastructure.Caching.ICacheService, HART.MCP.Infrastructure.Caching.MemoryCacheService>();
        
        services.AddSingleton<HART.MCP.AI.Abstractions.IRAGService, HART.MCP.AI.Services.RAGService>();
        
        services.AddSingleton<IToolRegistry>(provider =>
        {
            var registry = new ToolRegistry();
            registry.RegisterTool(new FinishTool());
            registry.RegisterTool(new TestTool());
            // Note: RAG tool requires IRagOrchestrator which needs database setup
            return registry;
        });
    }
}

public class McpServer
{
    private readonly IServiceProvider _serviceProvider;
    private readonly JsonSerializerOptions _jsonOptions;

    public McpServer(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
        };
    }

    public async Task RunAsync()
    {
        using var stdin = Console.OpenStandardInput();
        using var stdout = Console.OpenStandardOutput();
        using var reader = new StreamReader(stdin);
        using var writer = new StreamWriter(stdout);

        writer.AutoFlush = true;

        string? line;
        while ((line = await reader.ReadLineAsync()) != null)
        {
            try
            {
                var request = JsonSerializer.Deserialize<JsonRpcRequest>(line, _jsonOptions);
                if (request != null)
                {
                    var response = await HandleRequestAsync(request);
                    var responseJson = JsonSerializer.Serialize(response, _jsonOptions);
                    await writer.WriteLineAsync(responseJson);
                }
            }
            catch (Exception ex)
            {
                var errorResponse = new JsonRpcResponse
                {
                    Id = null,
                    Error = new JsonRpcError
                    {
                        Code = -32603,
                        Message = "Internal error",
                        Data = ex.Message
                    }
                };
                var errorJson = JsonSerializer.Serialize(errorResponse, _jsonOptions);
                await writer.WriteLineAsync(errorJson);
            }
        }
    }

    private async Task<JsonRpcResponse> HandleRequestAsync(JsonRpcRequest request)
    {
        return request.Method switch
        {
            "initialize" => await HandleInitializeAsync(request),
            "tools/list" => HandleToolsList(request),
            "tools/call" => await HandleToolCallAsync(request),
            "resources/list" => HandleResourcesList(request),
            "resources/read" => await HandleResourceReadAsync(request),
            _ => new JsonRpcResponse
            {
                Id = request.Id,
                Error = new JsonRpcError { Code = -32601, Message = "Method not found" }
            }
        };
    }

    private Task<JsonRpcResponse> HandleInitializeAsync(JsonRpcRequest request)
    {
        return Task.FromResult(new JsonRpcResponse
        {
            Id = request.Id,
            Result = new
            {
                protocolVersion = "2024-11-05",
                capabilities = new
                {
                    tools = new { },
                    resources = new { }
                },
                serverInfo = new
                {
                    name = "HART-MCP",
                    version = "1.0.0"
                }
            }
        });
    }

    private JsonRpcResponse HandleToolsList(JsonRpcRequest request)
    {
        var toolRegistry = _serviceProvider.GetRequiredService<IToolRegistry>();
        var tools = toolRegistry.GetAvailableTools().Select(tool => new
        {
            name = tool.Name,
            description = tool.Description,
            inputSchema = new
            {
                type = "object",
                properties = new
                {
                    input = new { type = "string", description = "Input for the tool" }
                },
                required = new[] { "input" }
            }
        }).ToArray();

        return new JsonRpcResponse
        {
            Id = request.Id,
            Result = new { tools }
        };
    }

    private async Task<JsonRpcResponse> HandleToolCallAsync(JsonRpcRequest request)
    {
        try
        {
            var toolCallParams = JsonSerializer.Deserialize<ToolCallParams>(
                request.Params?.GetRawText() ?? "{}", _jsonOptions);
            
            if (toolCallParams == null)
            {
                return new JsonRpcResponse
                {
                    Id = request.Id,
                    Error = new JsonRpcError { Code = -32602, Message = "Invalid params" }
                };
            }

            var toolRegistry = _serviceProvider.GetRequiredService<IToolRegistry>();
            var tool = toolRegistry.GetTool(toolCallParams.Name);
            
            if (tool == null)
            {
                return new JsonRpcResponse
                {
                    Id = request.Id,
                    Error = new JsonRpcError { Code = -32602, Message = $"Tool '{toolCallParams.Name}' not found" }
                };
            }

            var parameters = new Dictionary<string, object>();
            if (toolCallParams.Arguments.HasValue)
            {
                foreach (var prop in toolCallParams.Arguments.Value.EnumerateObject())
                {
                    parameters[prop.Name] = prop.Value.GetString() ?? "";
                }
            }

            var result = await tool.ExecuteAsync(parameters);

            return new JsonRpcResponse
            {
                Id = request.Id,
                Result = new
                {
                    content = new[]
                    {
                        new
                        {
                            type = "text",
                            text = result ?? "Tool executed successfully"
                        }
                    }
                }
            };
        }
        catch (Exception ex)
        {
            return new JsonRpcResponse
            {
                Id = request.Id,
                Error = new JsonRpcError
                {
                    Code = -32603,
                    Message = "Tool execution failed",
                    Data = ex.Message
                }
            };
        }
    }

    private JsonRpcResponse HandleResourcesList(JsonRpcRequest request)
    {
        var resources = new[]
        {
            new
            {
                uri = "hart-mcp://status",
                name = "System Status",
                description = "Current system status and health",
                mimeType = "application/json"
            },
            new
            {
                uri = "hart-mcp://agents",
                name = "Available Agents",
                description = "List of available agents and their capabilities",
                mimeType = "application/json"
            }
        };

        return new JsonRpcResponse
        {
            Id = request.Id,
            Result = new { resources }
        };
    }

    private Task<JsonRpcResponse> HandleResourceReadAsync(JsonRpcRequest request)
    {
        var resourceParams = JsonSerializer.Deserialize<ResourceReadParams>(
            request.Params?.GetRawText() ?? "{}", _jsonOptions);

        if (resourceParams?.Uri == null)
        {
            return Task.FromResult(new JsonRpcResponse
            {
                Id = request.Id,
                Error = new JsonRpcError { Code = -32602, Message = "Invalid params" }
            });
        }

        var content = resourceParams.Uri switch
        {
            "hart-mcp://status" => JsonSerializer.Serialize(new
            {
                status = "healthy",
                timestamp = DateTime.UtcNow,
                version = "1.0.0",
                capabilities = new[] { "rag", "agents", "tools" }
            }, _jsonOptions),
            "hart-mcp://agents" => JsonSerializer.Serialize(new
            {
                agents = new[]
                {
                    new { name = "Orchestrator", type = "orchestrator", description = "Manages complex tasks" },
                    new { name = "Specialist", type = "specialist", description = "Executes specific tasks" }
                }
            }, _jsonOptions),
            _ => "Resource not found"
        };

        return Task.FromResult(new JsonRpcResponse
        {
            Id = request.Id,
            Result = new
            {
                contents = new[]
                {
                    new
                    {
                        uri = resourceParams.Uri,
                        mimeType = "application/json",
                        text = content
                    }
                }
            }
        });
    }
}

// JSON-RPC Models
public class JsonRpcRequest
{
    [JsonPropertyName("jsonrpc")]
    public string JsonRpc { get; set; } = "2.0";
    
    [JsonPropertyName("id")]
    public object? Id { get; set; }
    
    [JsonPropertyName("method")]
    public string Method { get; set; } = "";
    
    [JsonPropertyName("params")]
    public JsonElement? Params { get; set; }
}

public class JsonRpcResponse
{
    [JsonPropertyName("jsonrpc")]
    public string JsonRpc { get; set; } = "2.0";
    
    [JsonPropertyName("id")]
    public object? Id { get; set; }
    
    [JsonPropertyName("result")]
    public object? Result { get; set; }
    
    [JsonPropertyName("error")]
    public JsonRpcError? Error { get; set; }
}

public class JsonRpcError
{
    [JsonPropertyName("code")]
    public int Code { get; set; }
    
    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
    
    [JsonPropertyName("data")]
    public object? Data { get; set; }
}

public class ToolCallParams
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    
    [JsonPropertyName("arguments")]
    public JsonElement? Arguments { get; set; }
}

public class ResourceReadParams
{
    [JsonPropertyName("uri")]
    public string? Uri { get; set; }
}