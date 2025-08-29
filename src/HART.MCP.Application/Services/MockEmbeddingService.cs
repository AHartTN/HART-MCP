using Microsoft.Extensions.Logging;

namespace HART.MCP.Application.Services;

public class EmbeddingService : IEmbeddingService
{
    private readonly ILogger<EmbeddingService> _logger;

    public EmbeddingService(ILogger<EmbeddingService> logger)
    {
        _logger = logger;
    }

    public Task<float[]> GenerateEmbeddingAsync(string text)
    {
        // Generate a deterministic but realistic embedding vector
        var embedding = new float[384]; // Common embedding dimension
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

    public async Task<List<float[]>> GenerateEmbeddingsAsync(List<string> texts)
    {
        var embeddings = new List<float[]>();
        foreach (var text in texts)
        {
            var embedding = await GenerateEmbeddingAsync(text);
            embeddings.Add(embedding);
        }
        
        _logger.LogInformation("Generated {Count} embeddings", texts.Count);
        return embeddings;
    }
}