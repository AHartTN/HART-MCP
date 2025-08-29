using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using HART.MCP.Application.Agents;
using HART.MCP.Application.Services;
using HART.MCP.Application.Tools;
using System.Collections.Concurrent;
using System.Text.Json;

namespace HART.MCP.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class McpController : ControllerBase
{
    private readonly IServiceProvider _serviceProvider;
    private readonly ILogger<McpController> _logger;
    private static readonly ConcurrentDictionary<string, TaskCompletionSource<string>> _missionTasks = new();
    private static readonly ConcurrentDictionary<string, ConcurrentQueue<object>> _missionQueues = new();

    public McpController(IServiceProvider serviceProvider, ILogger<McpController> logger)
    {
        _serviceProvider = serviceProvider;
        _logger = logger;
    }

    [HttpPost]
    public Task<IActionResult> ExecuteMission([FromBody] McpRequest request)
    {
        var missionId = Guid.NewGuid().ToString();
        var queue = new ConcurrentQueue<object>();
        _missionQueues[missionId] = queue;

        _ = Task.Run(async () =>
        {
            try
            {
                await RunAgentMission(request.Query, request.AgentId, missionId, queue);
            }
            catch (Exception ex)
            {
                queue.Enqueue(new { error = $"MCP error: {ex.Message}" });
                _logger.LogError(ex, "Mission {MissionId} failed", missionId);
            }
            finally
            {
                queue.Enqueue(new { status = "completed" }); // End marker
            }
        });

        return Task.FromResult<IActionResult>(Ok(new { mission_id = missionId }));
    }

    [HttpGet("test")]
    public async Task<IActionResult> TestAgent()
    {
        var result = await AgentTester.TestAgentExecution();
        return Ok(new { result });
    }

    [HttpGet("database-status")]
    public async Task<IActionResult> GetDatabaseStatus()
    {
        // Infrastructure disabled due to API compatibility issues
        var result = new
        {
            status = "Infrastructure disabled",
            agentCount = 0,
            documentCount = 0,
            chunkCount = 0,
            executionCount = 0,
            message = "Database operations are currently unavailable"
        };
        
        return await Task.FromResult(Ok(result));
    }

    [HttpGet("stream/{missionId}")]
    public async Task Stream(string missionId)
    {
        Response.ContentType = "text/event-stream";
        Response.Headers["Cache-Control"] = "no-cache";
        Response.Headers["Connection"] = "keep-alive";

        if (!_missionQueues.TryGetValue(missionId, out var queue))
        {
            await Response.WriteAsync("data: {\"error\":\"Mission not found\"}\n\n");
            return;
        }

        try
        {
            while (true)
            {
                if (queue.TryDequeue(out var message))
                {
                    if (message == null) break; // End marker

                    var json = JsonSerializer.Serialize(message);
                    await Response.WriteAsync($"data: {json}\n\n");
                    await Response.Body.FlushAsync();
                }
                else
                {
                    await Task.Delay(100); // Poll every 100ms
                }
            }
        }
        finally
        {
            _missionQueues.TryRemove(missionId, out _);
        }
    }

    private async Task RunAgentMission(string query, int agentId, string missionId, ConcurrentQueue<object> queue)
    {
        var updateCallback = new Func<Dictionary<string, object>, Task>(async (update) =>
        {
            queue.Enqueue(update);
            await Task.CompletedTask;
        });

        using var scope = _serviceProvider.CreateScope();
        var services = scope.ServiceProvider;

        var toolRegistry = services.GetRequiredService<IToolRegistry>();
        var llmService = services.GetRequiredService<ILlmService>();
        var projectState = services.GetRequiredService<IProjectStateService>();
        var loggerFactory = services.GetRequiredService<ILoggerFactory>();

        // Create specialist agent
        var specialistAgent = new SpecialistAgent(
            agentId,
            $"Specialist_{agentId}",
            "Specialist Task Executor",
            toolRegistry,
            llmService,
            projectState,
            loggerFactory.CreateLogger<SpecialistAgent>(),
            updateCallback);

        // Create orchestrator agent
        var orchestratorAgent = new OrchestratorAgent(
            agentId + 1000,
            $"Orchestrator_{agentId}",
            "Mission Orchestrator",
            toolRegistry,
            llmService,
            projectState,
            loggerFactory.CreateLogger<OrchestratorAgent>(),
            updateCallback);

        try
        {
            var result = await orchestratorAgent.RunAsync(query);
            queue.Enqueue(new { status = "completed", result });
        }
        catch (Exception ex)
        {
            queue.Enqueue(new { error = $"Agent execution failed: {ex.Message}" });
            throw;
        }
    }

    public class McpRequest
    {
        public string Query { get; set; } = string.Empty;
        public int AgentId { get; set; } = 1;
    }
}