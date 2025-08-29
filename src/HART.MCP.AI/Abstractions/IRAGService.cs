using HART.MCP.Domain.Entities;

namespace HART.MCP.AI.Abstractions;

public interface IRAGService
{
    Task<RAGResponse> QueryAsync(RAGRequest request, CancellationToken cancellationToken = default);
    Task<RAGResponse> QueryWithTreeOfThoughtAsync(TreeOfThoughtRAGRequest request, CancellationToken cancellationToken = default);
    Task<DocumentChunk[]> RetrieveRelevantChunksAsync(string query, int maxResults = 10, double threshold = 0.7, CancellationToken cancellationToken = default);
    Task<string> GenerateResponseAsync(string query, DocumentChunk[] relevantChunks, string? systemPrompt = null, CancellationToken cancellationToken = default);
}

public record RAGRequest(
    string Query,
    string? SystemPrompt = null,
    int MaxRetrievedChunks = 10,
    double SimilarityThreshold = 0.7,
    bool IncludeMetadata = true,
    Dictionary<string, object>? Filters = null);

public record TreeOfThoughtRAGRequest(
    string Query,
    string? SystemPrompt = null,
    int MaxRetrievedChunks = 10,
    double SimilarityThreshold = 0.7,
    int TreeDepth = 3,
    int BranchingFactor = 3,
    bool IncludeThoughtProcess = false) : RAGRequest(Query, SystemPrompt, MaxRetrievedChunks, SimilarityThreshold);

public record RAGResponse(
    string Answer,
    DocumentChunk[] RetrievedChunks,
    RAGMetadata Metadata);

public record RAGMetadata(
    TimeSpan ProcessingTime,
    int TokensUsed,
    decimal Cost,
    string Model,
    int ChunksRetrieved,
    double AverageSimilarity,
    string? TreeOfThoughtData = null,
    Dictionary<string, object>? AdditionalData = null);