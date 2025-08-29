using HART.MCP.AI.Abstractions;
using Microsoft.Extensions.Logging;

namespace HART.MCP.AI.Services;

public class EmbeddingService : IEmbeddingService
{
    private readonly ILogger<EmbeddingService> _logger;
    private const int DefaultDimensions = 384;

    public EmbeddingService(ILogger<EmbeddingService> logger)
    {
        _logger = logger;
    }

    public Task<float[]> GenerateEmbeddingAsync(string text, string? model = null, CancellationToken cancellationToken = default)
    {
        // Generate a deterministic but realistic embedding vector
        var embedding = new float[DefaultDimensions];
        var hash = text.GetHashCode();
        var random = new Random(hash); // Use text hash as seed for deterministic results
        
        for (int i = 0; i < embedding.Length; i++)
        {
            embedding[i] = (float)(random.NextDouble() * 2.0 - 1.0); // Values between -1 and 1
        }
        
        // Normalize the vector
        var norm = Math.Sqrt(embedding.Sum(x => x * x));
        for (int i = 0; i < embedding.Length; i++)
        {
            embedding[i] = (float)(embedding[i] / norm);
        }
        
        _logger.LogInformation("Generated embedding for text of length {Length}", text.Length);
        return Task.FromResult(embedding);
    }

    public async Task<float[][]> GenerateEmbeddingsAsync(string[] texts, string? model = null, CancellationToken cancellationToken = default)
    {
        var embeddings = new float[texts.Length][];
        for (int i = 0; i < texts.Length; i++)
        {
            embeddings[i] = await GenerateEmbeddingAsync(texts[i], model, cancellationToken);
        }
        
        _logger.LogInformation("Generated {Count} embeddings", texts.Length);
        return embeddings;
    }

    public Task<EmbeddingSimilarityResult[]> FindSimilarAsync(float[] queryEmbedding, float[][] candidateEmbeddings, double threshold = 0.7, int maxResults = 10)
    {
        var results = new List<EmbeddingSimilarityResult>();
        
        for (int i = 0; i < candidateEmbeddings.Length; i++)
        {
            var similarity = EmbeddingUtils.CosineSimilarity(queryEmbedding, candidateEmbeddings[i]);
            if (similarity >= threshold)
            {
                results.Add(new EmbeddingSimilarityResult(i, candidateEmbeddings[i], similarity));
            }
        }
        
        var sortedResults = results
            .OrderByDescending(r => r.Similarity)
            .Take(maxResults)
            .ToArray();
        
        _logger.LogInformation("Found {Count} similar embeddings above threshold {Threshold}", 
            sortedResults.Length, threshold);
        
        return Task.FromResult(sortedResults);
    }

    public int GetEmbeddingDimensions(string? model = null)
    {
        return DefaultDimensions;
    }

    public Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default)
    {
        // Always healthy for mock implementation
        return Task.FromResult(true);
    }
}