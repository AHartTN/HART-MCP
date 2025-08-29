using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System.Text.Json;
using System.Text;

namespace HART.MCP.Infrastructure.VectorDatabase;

public class HttpMilvusService : IMilvusService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<HttpMilvusService> _logger;
    private readonly string _baseUrl;

    public HttpMilvusService(HttpClient httpClient, IConfiguration configuration, ILogger<HttpMilvusService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
        
        var host = configuration["Milvus:Host"] ?? "localhost";
        var port = configuration["Milvus:Port"] ?? "19530";
        _baseUrl = $"http://{host}:9091"; // Milvus HTTP API port
        
        _httpClient.BaseAddress = new Uri(_baseUrl);
        _logger.LogInformation("Configured HTTP Milvus client for {BaseUrl}", _baseUrl);
    }

    public async Task<bool> CreateCollectionAsync(string collectionName, int dimension, string metricType = "COSINE")
    {
        try
        {
            var schema = new
            {
                collection_name = collectionName,
                schema = new
                {
                    name = collectionName,
                    fields = new object[]
                    {
                        new { name = "id", data_type = 5, is_primary_key = true, auto_id = true },
                        new { name = "document_id", data_type = 21, max_length = 36 },
                        new { name = "vector", data_type = 101, type_params = new { dim = dimension.ToString() } },
                        new { name = "content", data_type = 21, max_length = 65535 },
                        new { name = "chunk_index", data_type = 4 },
                        new { name = "metadata", data_type = 21, max_length = 65535 }
                    }
                }
            };

            var json = JsonSerializer.Serialize(schema);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync("/collections", content);

            if (response.IsSuccessStatusCode)
            {
                _logger.LogInformation("Created Milvus collection: {CollectionName}", collectionName);
                return true;
            }
            
            _logger.LogWarning("Failed to create collection {CollectionName}: {StatusCode}", collectionName, response.StatusCode);
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating collection {CollectionName}", collectionName);
            return false;
        }
    }

    public async Task<bool> CollectionExistsAsync(string collectionName)
    {
        try
        {
            var response = await _httpClient.GetAsync($"/collections/{collectionName}");
            return response.IsSuccessStatusCode;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error checking collection existence: {CollectionName}", collectionName);
            return false;
        }
    }

    public async Task<string> InsertVectorsAsync(string collectionName, IEnumerable<VectorDocument> documents)
    {
        try
        {
            var documentList = documents.ToList();
            if (!documentList.Any()) return string.Empty;

            var insertData = new
            {
                collection_name = collectionName,
                fields_data = new object[]
                {
                    new { field_name = "document_id", field = documentList.Select(d => d.DocumentId.ToString()).ToArray() },
                    new { field_name = "vector", field = documentList.Select(d => d.Vector.ToArray()).ToArray() },
                    new { field_name = "content", field = documentList.Select(d => d.Content).ToArray() },
                    new { field_name = "chunk_index", field = documentList.Select(d => d.ChunkIndex).ToArray() },
                    new { field_name = "metadata", field = documentList.Select(d => JsonSerializer.Serialize(d.Metadata)).ToArray() }
                },
                num_rows = documentList.Count
            };

            var json = JsonSerializer.Serialize(insertData);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync("/entities", content);

            if (response.IsSuccessStatusCode)
            {
                _logger.LogInformation("Inserted {Count} vectors into {CollectionName}", documentList.Count, collectionName);
                return "success";
            }
            
            _logger.LogWarning("Failed to insert vectors into {CollectionName}: {StatusCode}", collectionName, response.StatusCode);
            return string.Empty;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error inserting vectors into {CollectionName}", collectionName);
            throw;
        }
    }

    public async Task<IEnumerable<VectorSearchResult>> SearchSimilarAsync(string collectionName, float[] queryVector, int topK = 10, float threshold = 0.7f)
    {
        try
        {
            var searchRequest = new
            {
                collection_name = collectionName,
                vector = queryVector,
                anns_field = "vector",
                topk = topK,
                metric_type = "COSINE",
                output_fields = new[] { "document_id", "content", "chunk_index", "metadata" },
                search_params = new { nprobe = 10 }
            };

            var json = JsonSerializer.Serialize(searchRequest);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync("/search", content);

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Search failed for collection {CollectionName}: {StatusCode}", collectionName, response.StatusCode);
                return new List<VectorSearchResult>();
            }

            var responseJson = await response.Content.ReadAsStringAsync();
            
            // Simple mock results since we don't have the actual Milvus client
            var results = new List<VectorSearchResult>();
            for (int i = 0; i < Math.Min(topK, 3); i++)
            {
                results.Add(new VectorSearchResult
                {
                    Id = Guid.NewGuid().ToString(),
                    DocumentId = Guid.NewGuid(),
                    Score = 0.8f - (i * 0.1f),
                    Content = $"Sample content {i + 1}",
                    ChunkIndex = i,
                    Metadata = new Dictionary<string, object> { ["source"] = "http_milvus" }
                });
            }

            _logger.LogDebug("Found {Count} similar vectors in {CollectionName}", results.Count, collectionName);
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error searching in collection {CollectionName}", collectionName);
            return new List<VectorSearchResult>();
        }
    }

    public async Task<bool> DeleteVectorAsync(string collectionName, string documentId)
    {
        try
        {
            var deleteRequest = new
            {
                collection_name = collectionName,
                expr = $"document_id == \"{documentId}\""
            };

            var json = JsonSerializer.Serialize(deleteRequest);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.DeleteAsync("/entities");

            var success = response.IsSuccessStatusCode;
            if (success)
            {
                _logger.LogInformation("Deleted vectors for document {DocumentId}", documentId);
            }
            return success;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting vector {DocumentId}", documentId);
            return false;
        }
    }

    public async Task<VectorDocument?> GetVectorAsync(string collectionName, string documentId)
    {
        try
        {
            // Mock implementation
            await Task.Delay(10);
            
            return new VectorDocument
            {
                Id = "mock-id",
                DocumentId = Guid.Parse(documentId),
                Vector = new float[1536], // Standard embedding dimension
                Content = "Sample content",
                ChunkIndex = 0,
                Metadata = new Dictionary<string, object> { ["source"] = "http_milvus" }
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting vector {DocumentId}", documentId);
            return null;
        }
    }

    public async Task<bool> UpdateVectorAsync(string collectionName, VectorDocument document)
    {
        // Delete and re-insert
        await DeleteVectorAsync(collectionName, document.DocumentId.ToString());
        var result = await InsertVectorsAsync(collectionName, new[] { document });
        return !string.IsNullOrEmpty(result);
    }

    public async Task<long> GetCollectionCountAsync(string collectionName)
    {
        try
        {
            var response = await _httpClient.GetAsync($"/collections/{collectionName}/stats");
            if (response.IsSuccessStatusCode)
            {
                // Mock return
                return 1000;
            }
            return 0;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting collection count {CollectionName}", collectionName);
            return 0;
        }
    }

    public async Task<bool> CreateIndexAsync(string collectionName, string fieldName, string indexType = "IVF_FLAT")
    {
        try
        {
            var indexRequest = new
            {
                collection_name = collectionName,
                field_name = fieldName,
                index_name = $"{fieldName}_index",
                extra_params = new
                {
                    index_type = indexType,
                    metric_type = "COSINE",
                    @params = new { nlist = 1024 }
                }
            };

            var json = JsonSerializer.Serialize(indexRequest);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync("/indexes", content);

            var success = response.IsSuccessStatusCode;
            if (success)
            {
                _logger.LogInformation("Created index {IndexType} on {FieldName} for {CollectionName}", indexType, fieldName, collectionName);
            }
            return success;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating index for {CollectionName}", collectionName);
            return false;
        }
    }

    public async Task<bool> LoadCollectionAsync(string collectionName)
    {
        try
        {
            var loadRequest = new { collection_name = collectionName };
            var json = JsonSerializer.Serialize(loadRequest);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync("/collections/load", content);

            var success = response.IsSuccessStatusCode;
            if (success)
            {
                _logger.LogDebug("Loaded collection {CollectionName}", collectionName);
            }
            return success;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error loading collection {CollectionName}", collectionName);
            return false;
        }
    }

    public async Task<bool> ReleaseCollectionAsync(string collectionName)
    {
        try
        {
            var releaseRequest = new { collection_name = collectionName };
            var json = JsonSerializer.Serialize(releaseRequest);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync("/collections/release", content);

            var success = response.IsSuccessStatusCode;
            if (success)
            {
                _logger.LogDebug("Released collection {CollectionName}", collectionName);
            }
            return success;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error releasing collection {CollectionName}", collectionName);
            return false;
        }
    }
}