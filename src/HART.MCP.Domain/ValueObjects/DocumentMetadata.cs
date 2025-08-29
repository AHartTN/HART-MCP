using HART.MCP.Domain.Common;

namespace HART.MCP.Domain.ValueObjects;

public class DocumentMetadata : ValueObject
{
    public string Author { get; init; } = string.Empty;
    public string Subject { get; init; } = string.Empty;
    public string Keywords { get; init; } = string.Empty;
    public DateTime? CreationDate { get; init; }
    public DateTime? ModificationDate { get; init; }
    public string Language { get; init; } = "en";
    public int PageCount { get; init; }
    public string Source { get; init; } = string.Empty;
    public Dictionary<string, object> CustomProperties { get; init; } = new();

    protected override IEnumerable<object> GetEqualityComponents()
    {
        yield return Author;
        yield return Subject;
        yield return Keywords;
        yield return CreationDate ?? DateTime.MinValue;
        yield return ModificationDate ?? DateTime.MinValue;
        yield return Language;
        yield return PageCount;
        yield return Source;
        foreach (var kvp in CustomProperties.OrderBy(x => x.Key))
        {
            yield return kvp.Key;
            yield return kvp.Value;
        }
    }
}