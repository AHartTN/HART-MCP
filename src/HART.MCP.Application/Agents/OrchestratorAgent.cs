using HART.MCP.Application.Tools;
using HART.MCP.Application.Services;
using Microsoft.Extensions.Logging;

namespace HART.MCP.Application.Agents;

public class OrchestratorAgent : IOrchestratorAgent
{
	private readonly ILlmService _llmService;
	private readonly IToolRegistry _toolRegistry;
	private readonly IProjectStateService _projectState;
	private readonly ILogger<OrchestratorAgent> _logger;
	private readonly Func<Dictionary<string, object>, Task>? _updateCallback;

	public int AgentId { get; }
	public string Name { get; }
	public string Role { get; }

	public OrchestratorAgent(
		int agentId,
		string name,
		string role,
		IToolRegistry toolRegistry,
		ILlmService llmService,
		IProjectStateService projectState,
		ILogger<OrchestratorAgent> logger,
		Func<Dictionary<string, object>, Task>? updateCallback = null)
	{
		AgentId = agentId;
		Name = name;
		Role = role;
		_toolRegistry = toolRegistry;
		_llmService = llmService;
		_projectState = projectState;
		_logger = logger;
		_updateCallback = updateCallback;
	}

	public async Task<string> RunAsync(string query, int? logId = null)
	{
		try
		{
			await SendUpdateAsync(new Dictionary<string, object>
			{
				["status"] = "orchestrating",
				["agent"] = Name,
				["query"] = query
			});

			var systemPrompt = $@"You are {Name}, a {Role}.
Your job is to coordinate and delegate tasks to specialist agents.

Available tools: {string.Join(", ", _toolRegistry.GetAvailableTools().Select(t => t.Name))}

Break down complex tasks and delegate to specialists as needed.
Use DelegateToSpecialistTool to assign work to specialist agents.
Use FinishTool when the overall mission is complete.";

			var messages = new List<Dictionary<string, string>>
			{
				new() { ["role"] = "system", ["content"] = systemPrompt },
				new() { ["role"] = "user", ["content"] = query }
			};

			var maxIterations = 15;
			var iteration = 0;

			while (iteration < maxIterations)
			{
				iteration++;

				var response = await _llmService.GenerateResponseAsync(messages);

				await SendUpdateAsync(new Dictionary<string, object>
				{
					["iteration"] = iteration,
					["orchestrator_thinking"] = response
				});

				var toolCall = ExtractToolCall(response);
				if (toolCall == null)
				{
					messages.Add(new Dictionary<string, string> { ["role"] = "assistant", ["content"] = response });
					continue;
				}

				var tool = _toolRegistry.GetTool(toolCall.ToolName);
				if (tool == null)
				{
					var errorMsg = $"Tool '{toolCall.ToolName}' not found";
					messages.Add(new Dictionary<string, string> { ["role"] = "assistant", ["content"] = errorMsg });
					continue;
				}

				try
				{
					var toolResult = await tool.ExecuteAsync(toolCall.Parameters);

					await SendUpdateAsync(new Dictionary<string, object>
					{
						["orchestrator_tool_used"] = toolCall.ToolName,
						["orchestrator_tool_result"] = toolResult ?? ""
					});

					if (toolCall.ToolName == "FinishTool")
					{
						return toolResult ?? "Mission completed";
					}

					messages.Add(new Dictionary<string, string> { ["role"] = "assistant", ["content"] = response });
					messages.Add(new Dictionary<string, string> { ["role"] = "user", ["content"] = $"Tool result: {toolResult}" });
				}
				catch (Exception ex)
				{
					var errorMsg = $"Tool execution error: {ex.Message}";
					messages.Add(new Dictionary<string, string> { ["role"] = "user", ["content"] = errorMsg });
					_logger.LogError(ex, "Orchestrator tool execution failed: {ToolName}", toolCall.ToolName);
				}
			}

			return "Maximum orchestration iterations reached";
		}
		catch (Exception ex)
		{
			_logger.LogError(ex, "Orchestrator execution failed");
			await SendUpdateAsync(new Dictionary<string, object> { ["error"] = ex.Message });
			throw;
		}
	}

	public async Task SendUpdateAsync(Dictionary<string, object> update)
	{
		if (_updateCallback != null)
		{
			await _updateCallback(update);
		}
	}

	private ToolCall? ExtractToolCall(string response)
	{
		var lines = response.Split('\n');
		foreach (var line in lines)
		{
			if (line.Contains("use ") && line.Contains("Tool"))
			{
				try
				{
					var toolStart = line.IndexOf("use ") + 4;
					var toolEnd = line.IndexOf("Tool") + 4;
					if (toolStart > 3 && toolEnd > toolStart)
					{
						var toolName = line.Substring(toolStart, toolEnd - toolStart).Trim() ?? "";
						var parameters = new Dictionary<string, object>();

						var paramStart = line.IndexOf("with ");
						if (paramStart > 0)
						{
							var paramText = line.Substring(paramStart + 5);
							parameters["input"] = paramText.Trim() ?? "";
						}

						return new ToolCall { ToolName = toolName, Parameters = parameters };
					}
				}
				catch (Exception e)
				{
					_logger.LogError(e, "Failed to extract tool call from response: {Response}", response);
					throw;
				}
			}
		}
		return null;
	}

	private class ToolCall
	{
		public string ToolName { get; set; } = string.Empty;
		public Dictionary<string, object> Parameters { get; set; } = new();
	}
}