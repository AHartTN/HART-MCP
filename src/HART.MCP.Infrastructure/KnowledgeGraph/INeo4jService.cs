namespace HART.MCP.Infrastructure.KnowledgeGraph;

public interface INeo4jService
{
    Task<bool> CreateDocumentNodeAsync(DocumentNode document);
    Task<bool> CreateEntityNodeAsync(EntityNode entity);
    Task<bool> CreateRelationshipAsync(string fromNodeId, string toNodeId, string relationshipType, Dictionary<string, object>? properties = null);
    Task<IEnumerable<EntityNode>> GetConnectedEntitiesAsync(string nodeId, int maxDepth = 2);
    Task<IEnumerable<DocumentNode>> FindSimilarDocumentsAsync(string documentId, int limit = 10);
    Task<GraphPath> FindShortestPathAsync(string fromNodeId, string toNodeId, string? relationshipType = null);
    Task<IEnumerable<EntityNode>> SearchEntitiesByTypeAsync(string entityType, string? namePattern = null, int limit = 50);
    Task<bool> UpdateNodePropertiesAsync(string nodeId, Dictionary<string, object> properties);
    Task<bool> DeleteNodeAsync(string nodeId);
    Task<bool> DeleteRelationshipAsync(string relationshipId);
    Task<GraphStatistics> GetGraphStatisticsAsync();
    Task<IEnumerable<EntityNode>> ExtractEntitiesFromTextAsync(string text, string documentId);
    Task<bool> IndexExistsAsync(string indexName);
    Task<bool> CreateIndexAsync(string indexName, string label, string[] properties);
}

public class DocumentNode
{
    public string Id { get; set; } = string.Empty;
    public Guid DocumentId { get; set; }
    public string Title { get; set; } = string.Empty;
    public string ContentType { get; set; } = string.Empty;
    public string Hash { get; set; } = string.Empty;
    public long Size { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public Dictionary<string, object> Metadata { get; set; } = new();
    public List<string> Tags { get; set; } = new();
}

public class EntityNode
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string EntityType { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public double Confidence { get; set; } = 1.0;
    public Dictionary<string, object> Properties { get; set; } = new();
    public List<string> Aliases { get; set; } = new();
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public List<RelationshipInfo> Relationships { get; set; } = new();
}

public class RelationshipInfo
{
    public string Id { get; set; } = string.Empty;
    public string Type { get; set; } = string.Empty;
    public string TargetNodeId { get; set; } = string.Empty;
    public string TargetNodeName { get; set; } = string.Empty;
    public Dictionary<string, object> Properties { get; set; } = new();
    public double Strength { get; set; } = 1.0;
}

public class GraphPath
{
    public List<EntityNode> Nodes { get; set; } = new();
    public List<RelationshipInfo> Relationships { get; set; } = new();
    public int Length => Relationships.Count;
    public double TotalWeight { get; set; }
}

public class GraphStatistics
{
    public long TotalNodes { get; set; }
    public long TotalRelationships { get; set; }
    public long DocumentNodes { get; set; }
    public long EntityNodes { get; set; }
    public Dictionary<string, long> NodeTypesCounts { get; set; } = new();
    public Dictionary<string, long> RelationshipTypesCounts { get; set; } = new();
    public DateTime LastUpdated { get; set; } = DateTime.UtcNow;
}