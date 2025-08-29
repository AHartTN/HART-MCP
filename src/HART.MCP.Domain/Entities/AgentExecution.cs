using HART.MCP.Domain.Common;

namespace HART.MCP.Domain.Entities;

public class AgentExecution : BaseEntity
{
    public Guid AgentId { get; private set; }
    public string Query { get; private set; } = string.Empty;
    public string? Context { get; private set; }
    public string? Response { get; private set; }
    public ExecutionStatus Status { get; private set; } = ExecutionStatus.Running;
    public DateTime StartTime { get; private set; } = DateTime.UtcNow;
    public DateTime? EndTime { get; private set; }
    public TimeSpan? Duration => EndTime?.Subtract(StartTime);
    public string? ErrorMessage { get; private set; }
    public int TokensUsed { get; private set; }
    public decimal Cost { get; private set; }
    public string? TreeOfThoughtData { get; private set; }

    public Agent Agent { get; private set; } = null!;

    private AgentExecution() { }

    public AgentExecution(Guid agentId, string query, string? context = null)
    {
        AgentId = Guard.Against.Default(agentId, nameof(agentId));
        Query = Guard.Against.NullOrWhiteSpace(query, nameof(query));
        Context = context;
    }

    public void Complete(string response, int tokensUsed = 0, decimal cost = 0)
    {
        Response = Guard.Against.NullOrWhiteSpace(response, nameof(response));
        Status = ExecutionStatus.Completed;
        EndTime = DateTime.UtcNow;
        TokensUsed = tokensUsed;
        Cost = cost;
        MarkAsUpdated();
    }

    public void Fail(string errorMessage)
    {
        ErrorMessage = Guard.Against.NullOrWhiteSpace(errorMessage, nameof(errorMessage));
        Status = ExecutionStatus.Failed;
        EndTime = DateTime.UtcNow;
        MarkAsUpdated();
    }

    public void Cancel()
    {
        Status = ExecutionStatus.Cancelled;
        EndTime = DateTime.UtcNow;
        MarkAsUpdated();
    }

    public void SetTreeOfThoughtData(string treeData)
    {
        TreeOfThoughtData = treeData;
        MarkAsUpdated();
    }
}

public enum ExecutionStatus
{
    Running = 1,
    Completed = 2,
    Failed = 3,
    Cancelled = 4
}