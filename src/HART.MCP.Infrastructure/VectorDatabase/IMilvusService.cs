namespace HART.MCP.Infrastructure.VectorDatabase;

public interface IMilvusService
{
    Task<bool> CreateCollectionAsync(string collectionName, int dimension, string metricType = "COSINE");
    Task<bool> CollectionExistsAsync(string collectionName);
    Task<string> InsertVectorsAsync(string collectionName, IEnumerable<VectorDocument> documents);
    Task<IEnumerable<VectorSearchResult>> SearchSimilarAsync(string collectionName, float[] queryVector, int topK = 10, float threshold = 0.7f);
    Task<bool> DeleteVectorAsync(string collectionName, string documentId);
    Task<VectorDocument?> GetVectorAsync(string collectionName, string documentId);
    Task<bool> UpdateVectorAsync(string collectionName, VectorDocument document);
    Task<long> GetCollectionCountAsync(string collectionName);
    Task<bool> CreateIndexAsync(string collectionName, string fieldName, string indexType = "IVF_FLAT");
    Task<bool> LoadCollectionAsync(string collectionName);
    Task<bool> ReleaseCollectionAsync(string collectionName);
}

public class VectorDocument
{
    public string Id { get; set; } = string.Empty;
    public Guid DocumentId { get; set; }
    public float[] Vector { get; set; } = Array.Empty<float>();
    public string Content { get; set; } = string.Empty;
    public int ChunkIndex { get; set; }
    public string ContentType { get; set; } = string.Empty;
    public Dictionary<string, object> Metadata { get; set; } = new();
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public class VectorSearchResult
{
    public string Id { get; set; } = string.Empty;
    public Guid DocumentId { get; set; }
    public float Score { get; set; }
    public float[] Vector { get; set; } = Array.Empty<float>();
    public string Content { get; set; } = string.Empty;
    public int ChunkIndex { get; set; }
    public Dictionary<string, object> Metadata { get; set; } = new();
    public float Distance { get; set; }
}