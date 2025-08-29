namespace HART.MCP.AI.Abstractions;

public interface IEmbeddingService
{
    Task<float[]> GenerateEmbeddingAsync(string text, string? model = null, CancellationToken cancellationToken = default);
    Task<float[][]> GenerateEmbeddingsAsync(string[] texts, string? model = null, CancellationToken cancellationToken = default);
    Task<EmbeddingSimilarityResult[]> FindSimilarAsync(float[] queryEmbedding, float[][] candidateEmbeddings, double threshold = 0.7, int maxResults = 10);
    int GetEmbeddingDimensions(string? model = null);
    Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default);
}

public record EmbeddingSimilarityResult(
    int Index,
    float[] Embedding,
    double Similarity);

public static class EmbeddingUtils
{
    public static double CosineSimilarity(float[] a, float[] b)
    {
        if (a.Length != b.Length)
            throw new ArgumentException("Vectors must have the same length");

        double dotProduct = 0;
        double magnitudeA = 0;
        double magnitudeB = 0;

        for (int i = 0; i < a.Length; i++)
        {
            dotProduct += a[i] * b[i];
            magnitudeA += a[i] * a[i];
            magnitudeB += b[i] * b[i];
        }

        magnitudeA = Math.Sqrt(magnitudeA);
        magnitudeB = Math.Sqrt(magnitudeB);

        if (magnitudeA == 0 || magnitudeB == 0)
            return 0;

        return dotProduct / (magnitudeA * magnitudeB);
    }
}