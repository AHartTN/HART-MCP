namespace HART.MCP.Application.Tools;

public interface IToolRegistry
{
    void RegisterTool(ITool tool);
    ITool? GetTool(string name);
    IEnumerable<ITool> GetAvailableTools();
}

public interface ITool
{
    string Name { get; }
    string Description { get; }
    Task<string?> ExecuteAsync(Dictionary<string, object> parameters);
}

public class ToolRegistry : IToolRegistry
{
    private readonly Dictionary<string, ITool> _tools = new();

    public void RegisterTool(ITool tool)
    {
        _tools[tool.Name] = tool;
    }

    public ITool? GetTool(string name)
    {
        return _tools.GetValueOrDefault(name);
    }

    public IEnumerable<ITool> GetAvailableTools()
    {
        return _tools.Values;
    }
}