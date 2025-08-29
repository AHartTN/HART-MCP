using Neo4j.Driver;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace HART.MCP.Infrastructure.KnowledgeGraph;

public class Neo4jService : INeo4jService, IDisposable
{
    private readonly IDriver _driver;
    private readonly ILogger<Neo4jService> _logger;
    private bool _disposed;

    public Neo4jService(IConfiguration configuration, ILogger<Neo4jService> logger)
    {
        _logger = logger;
        
        var uri = configuration.GetConnectionString("Neo4j") ?? "bolt://localhost:7687";
        var username = configuration["Neo4j:Username"] ?? "neo4j";
        var password = configuration["Neo4j:Password"] ?? "password";

        _driver = GraphDatabase.Driver(uri, AuthTokens.Basic(username, password));
        _logger.LogInformation("Connected to Neo4j at {Uri}", uri);
    }

    public async Task<bool> CreateDocumentNodeAsync(DocumentNode document)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = @"
                CREATE (d:Document {
                    id: $id,
                    documentId: $documentId,
                    title: $title,
                    contentType: $contentType,
                    hash: $hash,
                    size: $size,
                    createdAt: $createdAt,
                    metadata: $metadata,
                    tags: $tags
                })
                RETURN d.id as id";

            var parameters = new Dictionary<string, object>
            {
                ["id"] = document.Id,
                ["documentId"] = document.DocumentId.ToString(),
                ["title"] = document.Title,
                ["contentType"] = document.ContentType,
                ["hash"] = document.Hash,
                ["size"] = document.Size,
                ["createdAt"] = document.CreatedAt.ToString("yyyy-MM-ddTHH:mm:ss.fffZ"),
                ["metadata"] = JsonSerializer.Serialize(document.Metadata),
                ["tags"] = document.Tags.ToArray()
            };

            var result = await session.RunAsync(query, parameters);
            var record = await result.SingleAsync();
            
            _logger.LogDebug("Created document node {DocumentId}", document.DocumentId);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create document node {DocumentId}", document.DocumentId);
            return false;
        }
    }

    public async Task<bool> CreateEntityNodeAsync(EntityNode entity)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = $@"
                CREATE (e:Entity:{entity.EntityType} {{
                    id: $id,
                    name: $name,
                    entityType: $entityType,
                    description: $description,
                    confidence: $confidence,
                    properties: $properties,
                    aliases: $aliases,
                    createdAt: $createdAt
                }})
                RETURN e.id as id";

            var parameters = new Dictionary<string, object>
            {
                ["id"] = entity.Id,
                ["name"] = entity.Name,
                ["entityType"] = entity.EntityType,
                ["description"] = entity.Description,
                ["confidence"] = entity.Confidence,
                ["properties"] = JsonSerializer.Serialize(entity.Properties),
                ["aliases"] = entity.Aliases.ToArray(),
                ["createdAt"] = entity.CreatedAt.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            };

            var result = await session.RunAsync(query, parameters);
            var record = await result.SingleAsync();
            
            _logger.LogDebug("Created entity node {EntityId} of type {EntityType}", entity.Id, entity.EntityType);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create entity node {EntityId}", entity.Id);
            return false;
        }
    }

    public async Task<bool> CreateRelationshipAsync(string fromNodeId, string toNodeId, string relationshipType, Dictionary<string, object>? properties = null)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = $@"
                MATCH (from), (to)
                WHERE from.id = $fromNodeId AND to.id = $toNodeId
                CREATE (from)-[r:{relationshipType}]->(to)
                SET r += $properties
                RETURN r";

            var parameters = new Dictionary<string, object>
            {
                ["fromNodeId"] = fromNodeId,
                ["toNodeId"] = toNodeId,
                ["properties"] = properties ?? new Dictionary<string, object>()
            };

            var result = await session.RunAsync(query, parameters);
            var hasRecord = await result.FetchAsync();
            
            if (hasRecord)
            {
                _logger.LogDebug("Created relationship {RelationshipType} from {FromNodeId} to {ToNodeId}", relationshipType, fromNodeId, toNodeId);
                return true;
            }
            
            _logger.LogWarning("Could not create relationship - nodes not found: {FromNodeId}, {ToNodeId}", fromNodeId, toNodeId);
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create relationship {RelationshipType} from {FromNodeId} to {ToNodeId}", relationshipType, fromNodeId, toNodeId);
            return false;
        }
    }

    public async Task<IEnumerable<EntityNode>> GetConnectedEntitiesAsync(string nodeId, int maxDepth = 2)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = @"
                MATCH (start {id: $nodeId})-[*1.." + maxDepth + @"]-(connected:Entity)
                RETURN DISTINCT connected.id as id, connected.name as name, 
                       connected.entityType as entityType, connected.description as description,
                       connected.confidence as confidence, connected.properties as properties,
                       connected.aliases as aliases, connected.createdAt as createdAt";

            var parameters = new Dictionary<string, object>
            {
                ["nodeId"] = nodeId
            };

            var result = await session.RunAsync(query, parameters);
            var entities = new List<EntityNode>();

            await result.ForEachAsync(record =>
            {
                var entity = new EntityNode
                {
                    Id = record["id"].As<string>(),
                    Name = record["name"].As<string>(),
                    EntityType = record["entityType"].As<string>(),
                    Description = record["description"].As<string>(),
                    Confidence = record["confidence"].As<double>(),
                    Aliases = record["aliases"].As<string[]>().ToList()
                };

                try
                {
                    var propertiesJson = record["properties"].As<string>();
                    entity.Properties = JsonSerializer.Deserialize<Dictionary<string, object>>(propertiesJson) ?? new();
                }
                catch
                {
                    entity.Properties = new Dictionary<string, object>();
                }

                if (DateTime.TryParse(record["createdAt"].As<string>(), out var createdAt))
                {
                    entity.CreatedAt = createdAt;
                }

                entities.Add(entity);
            });

            _logger.LogDebug("Found {Count} connected entities for node {NodeId}", entities.Count, nodeId);
            return entities;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get connected entities for node {NodeId}", nodeId);
            return new List<EntityNode>();
        }
    }

    public async Task<IEnumerable<DocumentNode>> FindSimilarDocumentsAsync(string documentId, int limit = 10)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = @"
                MATCH (d1:Document {documentId: $documentId})-[:MENTIONS]-(e:Entity)-[:MENTIONED_IN]-(d2:Document)
                WHERE d1 <> d2
                WITH d2, count(e) as sharedEntities
                ORDER BY sharedEntities DESC
                LIMIT $limit
                RETURN d2.id as id, d2.documentId as documentId, d2.title as title,
                       d2.contentType as contentType, d2.hash as hash, d2.size as size,
                       d2.createdAt as createdAt, d2.metadata as metadata, d2.tags as tags";

            var parameters = new Dictionary<string, object>
            {
                ["documentId"] = documentId,
                ["limit"] = limit
            };

            var result = await session.RunAsync(query, parameters);
            var documents = new List<DocumentNode>();

            await result.ForEachAsync(record =>
            {
                var document = new DocumentNode
                {
                    Id = record["id"].As<string>(),
                    Title = record["title"].As<string>(),
                    ContentType = record["contentType"].As<string>(),
                    Hash = record["hash"].As<string>(),
                    Size = record["size"].As<long>(),
                    Tags = record["tags"].As<string[]>().ToList()
                };

                if (Guid.TryParse(record["documentId"].As<string>(), out var docId))
                {
                    document.DocumentId = docId;
                }

                try
                {
                    var metadataJson = record["metadata"].As<string>();
                    document.Metadata = JsonSerializer.Deserialize<Dictionary<string, object>>(metadataJson) ?? new();
                }
                catch
                {
                    document.Metadata = new Dictionary<string, object>();
                }

                if (DateTime.TryParse(record["createdAt"].As<string>(), out var createdAt))
                {
                    document.CreatedAt = createdAt;
                }

                documents.Add(document);
            });

            _logger.LogDebug("Found {Count} similar documents for {DocumentId}", documents.Count, documentId);
            return documents;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to find similar documents for {DocumentId}", documentId);
            return new List<DocumentNode>();
        }
    }

    public async Task<GraphPath> FindShortestPathAsync(string fromNodeId, string toNodeId, string? relationshipType = null)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var relationshipFilter = string.IsNullOrEmpty(relationshipType) ? "" : $":{relationshipType}";
            
            var query = $@"
                MATCH (start {{id: $fromNodeId}}), (end {{id: $toNodeId}})
                MATCH path = shortestPath((start)-[{relationshipFilter}*]-(end))
                RETURN path";

            var parameters = new Dictionary<string, object>
            {
                ["fromNodeId"] = fromNodeId,
                ["toNodeId"] = toNodeId
            };

            var result = await session.RunAsync(query, parameters);
            var path = new GraphPath();

            if (await result.FetchAsync())
            {
                var pathValue = result.Current["path"].As<IPath>();
                
                // Extract nodes
                foreach (var node in pathValue.Nodes)
                {
                    var entityNode = new EntityNode
                    {
                        Id = node["id"].As<string>(),
                        Name = node.Properties.ContainsKey("name") ? node.Properties["name"].As<string>() : "",
                        EntityType = node.Properties.ContainsKey("entityType") ? node.Properties["entityType"].As<string>() : "Unknown"
                    };
                    path.Nodes.Add(entityNode);
                }

                // Extract relationships
                foreach (var relationship in pathValue.Relationships)
                {
                    var relationshipInfo = new RelationshipInfo
                    {
                        Id = relationship.ElementId,
                        Type = relationship.Type,
                        Properties = relationship.Properties.ToDictionary(p => p.Key, p => p.Value)
                    };
                    path.Relationships.Add(relationshipInfo);
                }

                path.TotalWeight = pathValue.Relationships.Count();
            }

            _logger.LogDebug("Found path of length {Length} from {FromNodeId} to {ToNodeId}", path.Length, fromNodeId, toNodeId);
            return path;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to find shortest path from {FromNodeId} to {ToNodeId}", fromNodeId, toNodeId);
            return new GraphPath();
        }
    }

    public async Task<IEnumerable<EntityNode>> SearchEntitiesByTypeAsync(string entityType, string? namePattern = null, int limit = 50)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var whereClause = string.IsNullOrEmpty(namePattern) 
                ? "" 
                : "AND e.name CONTAINS $namePattern";
            
            var query = $@"
                MATCH (e:Entity:{entityType})
                WHERE true {whereClause}
                RETURN e.id as id, e.name as name, e.entityType as entityType,
                       e.description as description, e.confidence as confidence,
                       e.properties as properties, e.aliases as aliases, e.createdAt as createdAt
                LIMIT $limit";

            var parameters = new Dictionary<string, object>
            {
                ["limit"] = limit
            };

            if (!string.IsNullOrEmpty(namePattern))
            {
                parameters["namePattern"] = namePattern;
            }

            var result = await session.RunAsync(query, parameters);
            var entities = new List<EntityNode>();

            await result.ForEachAsync(record =>
            {
                var entity = new EntityNode
                {
                    Id = record["id"].As<string>(),
                    Name = record["name"].As<string>(),
                    EntityType = record["entityType"].As<string>(),
                    Description = record["description"].As<string>(),
                    Confidence = record["confidence"].As<double>(),
                    Aliases = record["aliases"].As<string[]>().ToList()
                };

                try
                {
                    var propertiesJson = record["properties"].As<string>();
                    entity.Properties = JsonSerializer.Deserialize<Dictionary<string, object>>(propertiesJson) ?? new();
                }
                catch
                {
                    entity.Properties = new Dictionary<string, object>();
                }

                if (DateTime.TryParse(record["createdAt"].As<string>(), out var createdAt))
                {
                    entity.CreatedAt = createdAt;
                }

                entities.Add(entity);
            });

            _logger.LogDebug("Found {Count} entities of type {EntityType}", entities.Count, entityType);
            return entities;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to search entities of type {EntityType}", entityType);
            return new List<EntityNode>();
        }
    }

    public async Task<bool> UpdateNodePropertiesAsync(string nodeId, Dictionary<string, object> properties)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = @"
                MATCH (n {id: $nodeId})
                SET n += $properties
                RETURN n.id as id";

            var parameters = new Dictionary<string, object>
            {
                ["nodeId"] = nodeId,
                ["properties"] = properties
            };

            var result = await session.RunAsync(query, parameters);
            var hasRecord = await result.FetchAsync();
            
            if (hasRecord)
            {
                _logger.LogDebug("Updated properties for node {NodeId}", nodeId);
                return true;
            }
            
            _logger.LogWarning("Node not found for update: {NodeId}", nodeId);
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to update node properties {NodeId}", nodeId);
            return false;
        }
    }

    public async Task<bool> DeleteNodeAsync(string nodeId)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = @"
                MATCH (n {id: $nodeId})
                DETACH DELETE n";

            var parameters = new Dictionary<string, object>
            {
                ["nodeId"] = nodeId
            };

            var result = await session.RunAsync(query, parameters);
            var summary = await result.ConsumeAsync();
            
            var deleted = summary.Counters.NodesDeleted > 0;
            if (deleted)
            {
                _logger.LogDebug("Deleted node {NodeId}", nodeId);
            }
            
            return deleted;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to delete node {NodeId}", nodeId);
            return false;
        }
    }

    public async Task<bool> DeleteRelationshipAsync(string relationshipId)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = @"
                MATCH ()-[r]-()
                WHERE elementId(r) = $relationshipId
                DELETE r";

            var parameters = new Dictionary<string, object>
            {
                ["relationshipId"] = relationshipId
            };

            var result = await session.RunAsync(query, parameters);
            var summary = await result.ConsumeAsync();
            
            var deleted = summary.Counters.RelationshipsDeleted > 0;
            if (deleted)
            {
                _logger.LogDebug("Deleted relationship {RelationshipId}", relationshipId);
            }
            
            return deleted;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to delete relationship {RelationshipId}", relationshipId);
            return false;
        }
    }

    public async Task<GraphStatistics> GetGraphStatisticsAsync()
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = @"
                MATCH (n) 
                OPTIONAL MATCH ()-[r]->()
                RETURN 
                    count(DISTINCT n) as totalNodes,
                    count(DISTINCT r) as totalRelationships,
                    count(DISTINCT CASE WHEN n:Document THEN n END) as documentNodes,
                    count(DISTINCT CASE WHEN n:Entity THEN n END) as entityNodes";

            var result = await session.RunAsync(query);
            var record = await result.SingleAsync();

            var stats = new GraphStatistics
            {
                TotalNodes = record["totalNodes"].As<long>(),
                TotalRelationships = record["totalRelationships"].As<long>(),
                DocumentNodes = record["documentNodes"].As<long>(),
                EntityNodes = record["entityNodes"].As<long>()
            };

            // Get node type counts
            var nodeTypeQuery = @"
                MATCH (n)
                RETURN labels(n) as labels, count(n) as count";

            var nodeTypeResult = await session.RunAsync(nodeTypeQuery);
            await nodeTypeResult.ForEachAsync(record =>
            {
                var labels = record["labels"].As<string[]>();
                var count = record["count"].As<long>();
                foreach (var label in labels)
                {
                    stats.NodeTypesCounts[label] = stats.NodeTypesCounts.GetValueOrDefault(label, 0) + count;
                }
            });

            // Get relationship type counts
            var relTypeQuery = @"
                MATCH ()-[r]->()
                RETURN type(r) as relType, count(r) as count";

            var relTypeResult = await session.RunAsync(relTypeQuery);
            await relTypeResult.ForEachAsync(record =>
            {
                var relType = record["relType"].As<string>();
                var count = record["count"].As<long>();
                stats.RelationshipTypesCounts[relType] = count;
            });

            _logger.LogDebug("Retrieved graph statistics: {TotalNodes} nodes, {TotalRelationships} relationships", 
                stats.TotalNodes, stats.TotalRelationships);
            
            return stats;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get graph statistics");
            return new GraphStatistics();
        }
    }

    public Task<IEnumerable<EntityNode>> ExtractEntitiesFromTextAsync(string text, string documentId)
    {
        // This is a simplified entity extraction - in practice you'd use NLP libraries
        // or call external services like spaCy, NLTK, or cloud NER services
        
        var entities = new List<EntityNode>();
        var words = text.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        
        // Simple capitalized word extraction (very basic NER)
        var capitalizedWords = words
            .Where(w => char.IsUpper(w[0]) && w.Length > 2 && w.All(c => char.IsLetter(c)))
            .Distinct()
            .ToList();

        foreach (var word in capitalizedWords.Take(10)) // Limit to 10 entities
        {
            var entity = new EntityNode
            {
                Id = Guid.NewGuid().ToString(),
                Name = word,
                EntityType = "UNKNOWN", // Would be determined by NER
                Description = $"Entity extracted from document {documentId}",
                Confidence = 0.5, // Low confidence for this simple extraction
                Properties = new Dictionary<string, object>
                {
                    ["source"] = "simple_extraction",
                    ["documentId"] = documentId
                }
            };
            
            entities.Add(entity);
        }

        _logger.LogDebug("Extracted {Count} entities from text for document {DocumentId}", entities.Count, documentId);
        return Task.FromResult<IEnumerable<EntityNode>>(entities);
    }

    public async Task<bool> IndexExistsAsync(string indexName)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var query = @"SHOW INDEXES YIELD name WHERE name = $indexName RETURN count(*) as count";
            
            var parameters = new Dictionary<string, object>
            {
                ["indexName"] = indexName
            };

            var result = await session.RunAsync(query, parameters);
            var record = await result.SingleAsync();
            
            return record["count"].As<long>() > 0;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to check if index {IndexName} exists", indexName);
            return false;
        }
    }

    public async Task<bool> CreateIndexAsync(string indexName, string label, string[] properties)
    {
        try
        {
            using var session = _driver.AsyncSession();
            
            var propertyList = string.Join(", ", properties.Select(p => $"n.{p}"));
            var query = $"CREATE INDEX {indexName} FOR (n:{label}) ON ({propertyList})";

            await session.RunAsync(query);
            
            _logger.LogInformation("Created index {IndexName} for label {Label} on properties {Properties}", 
                indexName, label, string.Join(", ", properties));
            
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create index {IndexName}", indexName);
            return false;
        }
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            _driver?.Dispose();
            _disposed = true;
        }
    }
}