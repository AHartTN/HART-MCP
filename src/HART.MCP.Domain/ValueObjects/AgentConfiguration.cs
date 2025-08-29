using HART.MCP.Domain.Common;

namespace HART.MCP.Domain.ValueObjects;

public class AgentConfiguration : ValueObject
{
    public string ModelName { get; init; } = "gpt-3.5-turbo";
    public double Temperature { get; init; } = 0.7;
    public int MaxTokens { get; init; } = 2048;
    public int TimeoutSeconds { get; init; } = 60;
    public bool EnableMemory { get; init; } = true;
    public bool EnableToolUse { get; init; } = true;
    public Dictionary<string, object> CustomSettings { get; init; } = new();

    protected override IEnumerable<object> GetEqualityComponents()
    {
        yield return ModelName;
        yield return Temperature;
        yield return MaxTokens;
        yield return TimeoutSeconds;
        yield return EnableMemory;
        yield return EnableToolUse;
        foreach (var kvp in CustomSettings.OrderBy(x => x.Key))
        {
            yield return kvp.Key;
            yield return kvp.Value;
        }
    }
}