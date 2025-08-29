namespace HART.MCP.Application.Tools;

public class TestTool : ITool
{
    public string Name => "TestTool";
    public string Description => "Simple test tool that echoes input";

    public Task<string?> ExecuteAsync(Dictionary<string, object> parameters)
    {
        var input = parameters.GetValueOrDefault("input")?.ToString() ?? "No input provided";
        return Task.FromResult<string?>($"TestTool executed with input: {input}");
    }
}