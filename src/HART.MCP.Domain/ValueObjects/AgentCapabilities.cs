using HART.MCP.Domain.Common;

namespace HART.MCP.Domain.ValueObjects;

public class AgentCapabilities : ValueObject
{
    public bool CanProcessDocuments { get; init; } = true;
    public bool CanPerformRAG { get; init; } = true;
    public bool CanUseTreeOfThought { get; init; } = false;
    public bool CanDelegateToOthers { get; init; } = false;
    public bool CanAccessExternalAPIs { get; init; } = false;
    public List<string> SupportedFileTypes { get; init; } = new();
    public List<string> SupportedLanguages { get; init; } = new() { "en" };
    public List<string> AvailableTools { get; init; } = new();
    public Dictionary<string, object> CustomCapabilities { get; init; } = new();

    protected override IEnumerable<object> GetEqualityComponents()
    {
        yield return CanProcessDocuments;
        yield return CanPerformRAG;
        yield return CanUseTreeOfThought;
        yield return CanDelegateToOthers;
        yield return CanAccessExternalAPIs;
        foreach (var fileType in SupportedFileTypes.OrderBy(x => x))
            yield return fileType;
        foreach (var language in SupportedLanguages.OrderBy(x => x))
            yield return language;
        foreach (var tool in AvailableTools.OrderBy(x => x))
            yield return tool;
        foreach (var kvp in CustomCapabilities.OrderBy(x => x.Key))
        {
            yield return kvp.Key;
            yield return kvp.Value;
        }
    }
}