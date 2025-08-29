using HART.MCP.Domain.Common;
using HART.MCP.Domain.ValueObjects;

namespace HART.MCP.Domain.Entities;

public class Document : BaseEntity
{
    public string Title { get; private set; } = string.Empty;
    public string Content { get; private set; } = string.Empty;
    public string OriginalFileName { get; private set; } = string.Empty;
    public DocumentType Type { get; private set; }
    public long SizeBytes { get; private set; }
    public string MimeType { get; private set; } = string.Empty;
    public string Hash { get; private set; } = string.Empty;
    public DocumentMetadata Metadata { get; private set; } = new();
    public DocumentStatus Status { get; private set; } = DocumentStatus.Pending;
    public string? ProcessingError { get; private set; }
    public DateTime? ProcessedAt { get; private set; }

    private readonly List<DocumentChunk> _chunks = new();
    public IReadOnlyCollection<DocumentChunk> Chunks => _chunks.AsReadOnly();

    private Document() { }

    public Document(
        string title,
        string content,
        string originalFileName,
        DocumentType type,
        long sizeBytes,
        string mimeType,
        string hash)
    {
        Title = Guard.Against.NullOrWhiteSpace(title, nameof(title));
        Content = Guard.Against.NullOrWhiteSpace(content, nameof(content));
        OriginalFileName = Guard.Against.NullOrWhiteSpace(originalFileName, nameof(originalFileName));
        Type = type;
        SizeBytes = Guard.Against.Negative(sizeBytes, nameof(sizeBytes));
        MimeType = Guard.Against.NullOrWhiteSpace(mimeType, nameof(mimeType));
        Hash = Guard.Against.NullOrWhiteSpace(hash, nameof(hash));
    }

    public void AddChunk(DocumentChunk chunk)
    {
        Guard.Against.Null(chunk, nameof(chunk));
        _chunks.Add(chunk);
        MarkAsUpdated();
    }

    public void MarkAsProcessed()
    {
        Status = DocumentStatus.Processed;
        ProcessedAt = DateTime.UtcNow;
        ProcessingError = null;
        MarkAsUpdated();
    }

    public void MarkAsProcessingFailed(string error)
    {
        Status = DocumentStatus.Failed;
        ProcessingError = Guard.Against.NullOrWhiteSpace(error, nameof(error));
        MarkAsUpdated();
    }

    public void UpdateMetadata(DocumentMetadata metadata)
    {
        Metadata = Guard.Against.Null(metadata, nameof(metadata));
        MarkAsUpdated();
    }
}

public enum DocumentType
{
    Text = 1,
    Pdf = 2,
    Image = 3,
    Audio = 4,
    Video = 5,
    Other = 99
}

public enum DocumentStatus
{
    Pending = 1,
    Processing = 2,
    Processed = 3,
    Failed = 4
}