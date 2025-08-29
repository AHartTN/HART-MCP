using HART.MCP.Domain.Common;
using HART.MCP.Domain.ValueObjects;

namespace HART.MCP.Domain.Entities;

public class Agent : BaseEntity
{
    public string Name { get; private set; } = string.Empty;
    public string Description { get; private set; } = string.Empty;
    public AgentType Type { get; private set; }
    public AgentStatus Status { get; private set; } = AgentStatus.Inactive;
    public AgentConfiguration Configuration { get; private set; } = new();
    public AgentCapabilities Capabilities { get; private set; } = new();
    public string? SystemPrompt { get; private set; }
    public DateTime? LastActiveAt { get; private set; }
    public int ExecutionCount { get; private set; }
    public TimeSpan TotalExecutionTime { get; private set; }

    private readonly List<AgentExecution> _executions = new();
    public IReadOnlyCollection<AgentExecution> Executions => _executions.AsReadOnly();

    private Agent() { }

    public Agent(
        string name,
        string description,
        AgentType type,
        AgentConfiguration? configuration = null)
    {
        Name = Guard.Against.NullOrWhiteSpace(name, nameof(name));
        Description = Guard.Against.NullOrWhiteSpace(description, nameof(description));
        Type = type;
        Configuration = configuration ?? new AgentConfiguration();
    }

    public void Activate()
    {
        Status = AgentStatus.Active;
        LastActiveAt = DateTime.UtcNow;
        MarkAsUpdated();
    }

    public void Deactivate()
    {
        Status = AgentStatus.Inactive;
        MarkAsUpdated();
    }

    public void UpdateConfiguration(AgentConfiguration configuration)
    {
        Configuration = Guard.Against.Null(configuration, nameof(configuration));
        MarkAsUpdated();
    }

    public void UpdateCapabilities(AgentCapabilities capabilities)
    {
        Capabilities = Guard.Against.Null(capabilities, nameof(capabilities));
        MarkAsUpdated();
    }

    public void SetSystemPrompt(string? systemPrompt)
    {
        SystemPrompt = systemPrompt;
        MarkAsUpdated();
    }

    public AgentExecution StartExecution(string query, string? context = null)
    {
        var execution = new AgentExecution(Id, query, context);
        _executions.Add(execution);
        Status = AgentStatus.Executing;
        LastActiveAt = DateTime.UtcNow;
        MarkAsUpdated();
        return execution;
    }

    public void CompleteExecution(AgentExecution execution, TimeSpan executionTime)
    {
        ExecutionCount++;
        TotalExecutionTime += executionTime;
        Status = AgentStatus.Active;
        LastActiveAt = DateTime.UtcNow;
        MarkAsUpdated();
    }
}

public enum AgentType
{
    Orchestrator = 1,
    Specialist = 2,
    RAG = 3,
    TreeOfThought = 4,
    MetaAgent = 5
}

public enum AgentStatus
{
    Inactive = 1,
    Active = 2,
    Executing = 3,
    Error = 4,
    Maintenance = 5
}