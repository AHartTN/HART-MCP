using HART.MCP.Application.Services;
using HART.MCP.Application.Agents;

namespace HART.MCP.Application.Tools;

public class RagTool : ITool
{
    private readonly IRagOrchestrator _ragOrchestrator;

    public string Name => "RAGTool";
    public string Description => "Retrieve and generate responses using RAG pipeline";

    public RagTool(IRagOrchestrator ragOrchestrator)
    {
        _ragOrchestrator = ragOrchestrator;
    }

    public async Task<string?> ExecuteAsync(Dictionary<string, object> parameters)
    {
        var query = parameters.GetValueOrDefault("input")?.ToString() ?? 
                   parameters.GetValueOrDefault("query")?.ToString() ?? 
                   string.Empty;

        if (string.IsNullOrEmpty(query))
            return "Error: No query provided for RAG tool";

        try
        {
            var response = await _ragOrchestrator.GenerateResponseAsync(query);
            return response;
        }
        catch (Exception ex)
        {
            return $"RAG tool error: {ex.Message}";
        }
    }
}

public class FinishTool : ITool
{
    public string Name => "FinishTool";
    public string Description => "Complete the current task with final result";

    public Task<string?> ExecuteAsync(Dictionary<string, object> parameters)
    {
        var result = parameters.GetValueOrDefault("input")?.ToString() ?? 
                    parameters.GetValueOrDefault("result")?.ToString() ?? 
                    "Task completed";
        return Task.FromResult<string?>(result);
    }
}

public class WriteToSharedStateTool : ITool
{
    private readonly IProjectStateService _projectState;

    public string Name => "WriteToSharedStateTool";
    public string Description => "Write data to shared project state";

    public WriteToSharedStateTool(IProjectStateService projectState)
    {
        _projectState = projectState;
    }

    public async Task<string?> ExecuteAsync(Dictionary<string, object> parameters)
    {
        var key = parameters.GetValueOrDefault("key")?.ToString();
        var value = parameters.GetValueOrDefault("value");

        if (string.IsNullOrEmpty(key))
            return "Error: No key provided";

        await _projectState.SetAsync(key, value);
        return $"Stored value for key: {key}";
    }
}

public class ReadFromSharedStateTool : ITool
{
    private readonly IProjectStateService _projectState;

    public string Name => "ReadFromSharedStateTool";
    public string Description => "Read data from shared project state";

    public ReadFromSharedStateTool(IProjectStateService projectState)
    {
        _projectState = projectState;
    }

    public async Task<string?> ExecuteAsync(Dictionary<string, object> parameters)
    {
        var key = parameters.GetValueOrDefault("key")?.ToString();

        if (string.IsNullOrEmpty(key))
            return "Error: No key provided";

        var value = await _projectState.GetAsync<object>(key);
        return value?.ToString() ?? "No value found for key";
    }
}

public class DelegateToSpecialistTool : ITool
{
    private readonly ISpecialistAgent _specialist;

    public string Name => "DelegateToSpecialistTool";
    public string Description => "Delegate task to specialist agent";

    public DelegateToSpecialistTool(ISpecialistAgent specialist)
    {
        _specialist = specialist;
    }

    public async Task<string?> ExecuteAsync(Dictionary<string, object> parameters)
    {
        var task = parameters.GetValueOrDefault("input")?.ToString() ?? 
                  parameters.GetValueOrDefault("task")?.ToString();

        if (string.IsNullOrEmpty(task))
            return "Error: No task provided for delegation";

        try
        {
            var result = await _specialist.RunAsync(task);
            return $"Specialist completed task: {result}";
        }
        catch (Exception ex)
        {
            return $"Specialist delegation error: {ex.Message}";
        }
    }
}