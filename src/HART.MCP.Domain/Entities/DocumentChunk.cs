using HART.MCP.Domain.Common;

namespace HART.MCP.Domain.Entities;

public class DocumentChunk : BaseEntity
{
    public Guid DocumentId { get; private set; }
    public string Content { get; private set; } = string.Empty;
    public int ChunkIndex { get; private set; }
    public int StartPosition { get; private set; }
    public int EndPosition { get; private set; }
    public float[] Embedding { get; private set; } = Array.Empty<float>();
    public string EmbeddingModel { get; private set; } = string.Empty;
    public DateTime? EmbeddedAt { get; private set; }

    public Document Document { get; private set; } = null!;

    private DocumentChunk() { }

    public DocumentChunk(
        Guid documentId,
        string content,
        int chunkIndex,
        int startPosition,
        int endPosition)
    {
        DocumentId = Guard.Against.Default(documentId, nameof(documentId));
        Content = Guard.Against.NullOrWhiteSpace(content, nameof(content));
        ChunkIndex = Guard.Against.Negative(chunkIndex, nameof(chunkIndex));
        StartPosition = Guard.Against.Negative(startPosition, nameof(startPosition));
        EndPosition = Guard.Against.NegativeOrZero(endPosition, nameof(endPosition));
        
        if (endPosition <= startPosition)
            throw new ArgumentException("EndPosition must be greater than StartPosition");
    }

    public void SetEmbedding(float[] embedding, string model)
    {
        Embedding = Guard.Against.NullOrEmpty(embedding, nameof(embedding));
        EmbeddingModel = Guard.Against.NullOrWhiteSpace(model, nameof(model));
        EmbeddedAt = DateTime.UtcNow;
        MarkAsUpdated();
    }
}