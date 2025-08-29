namespace HART.MCP.Application.Agents;

public interface ISpecialistAgent
{
    int AgentId { get; }
    string Name { get; }
    string Role { get; }
    Task<string> RunAsync(string query, int? logId = null);
    Task SendUpdateAsync(Dictionary<string, object> update);
}

public interface IOrchestratorAgent
{
    int AgentId { get; }
    string Name { get; }
    string Role { get; }
    Task<string> RunAsync(string query, int? logId = null);
    Task SendUpdateAsync(Dictionary<string, object> update);
}