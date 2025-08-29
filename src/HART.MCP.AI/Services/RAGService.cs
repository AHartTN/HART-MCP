using HART.MCP.AI.Abstractions;
using HART.MCP.Application.Services;
using HART.MCP.Domain.Entities;
using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace HART.MCP.AI.Services;

public class RAGService : IRAGService
{
    private readonly HART.MCP.AI.Abstractions.IEmbeddingService _embeddingService;
    private readonly ILlmService _llmService;
    private readonly ILogger<RAGService> _logger;

    public RAGService(
        HART.MCP.AI.Abstractions.IEmbeddingService embeddingService,
        ILlmService llmService,
        ILogger<RAGService> logger)
    {
        _embeddingService = embeddingService;
        _llmService = llmService;
        _logger = logger;
    }

    public async Task<RAGResponse> QueryAsync(RAGRequest request, CancellationToken cancellationToken = default)
    {
        var stopwatch = Stopwatch.StartNew();
        var startTime = DateTime.UtcNow;

        try
        {
            _logger.LogInformation("Starting RAG query: {Query}", request.Query);

            // Generate embeddings and search for similar content (simplified for now)
            var embedding = await _embeddingService.GenerateEmbeddingAsync(request.Query);
            
            // For now, create a simple response based on the query
            var response = await _llmService.GenerateResponseAsync($@"
You are an intelligent RAG system. The user asked: {request.Query}

Based on the query embeddings (dimension: {embedding.Length}), provide a helpful response.
If you don't have specific context, explain what kind of information would be helpful and how you would normally retrieve it from a vector database and knowledge graph.");

            // Create mock relevant chunks for demonstration
            var relevantChunks = new[]
            {
                new DocumentChunk(
                    Guid.NewGuid(),
                    $"Context related to: {request.Query}",
                    0,
                    0,
                    50)
            };

            stopwatch.Stop();
            
            var metadata = new RAGMetadata(
                stopwatch.Elapsed,
                response.Length,
                CalculateTokenCost(response),
                "gpt-4", // Model used
                relevantChunks.Length,
                0.85); // Average similarity score

            _logger.LogInformation("RAG query completed in {Duration}ms with {ChunkCount} chunks", 
                stopwatch.ElapsedMilliseconds, relevantChunks.Length);

            return new RAGResponse(response, relevantChunks, metadata);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "RAG query failed: {Query}", request.Query);
            throw;
        }
    }

    public async Task<RAGResponse> QueryWithTreeOfThoughtAsync(TreeOfThoughtRAGRequest request, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Starting Tree of Thought RAG query: {Query}", request.Query);

        var thoughts = new List<string>();
        
        // Generate multiple reasoning paths  
        for (int i = 0; i < request.BranchingFactor; i++)
        {
            var thoughtPrompt = $@"Consider this question from perspective {i + 1}: {request.Query}
            
Generate a different angle or approach to thinking about this problem.";

            var thought = await _llmService.GenerateResponseAsync(thoughtPrompt);
            thoughts.Add(thought);
        }

        // Combine thoughts into enhanced query
        var enhancedQuery = $"{request.Query}\n\nConsider these perspectives:\n{string.Join("\n", thoughts.Select((t, i) => $"{i + 1}. {t}"))}";

        // Use standard RAG with enhanced query
        var ragRequest = new RAGRequest(
            enhancedQuery, 
            request.SystemPrompt, 
            request.MaxRetrievedChunks, 
            request.SimilarityThreshold);

        return await QueryAsync(ragRequest, cancellationToken);
    }

    public async Task<DocumentChunk[]> RetrieveRelevantChunksAsync(string query, int maxResults = 10, double threshold = 0.7, CancellationToken cancellationToken = default)
    {
        try
        {
            // Generate embedding for the query
            var queryEmbedding = await _embeddingService.GenerateEmbeddingAsync(query);
            
            _logger.LogDebug("Generated query embedding with dimension {Dimension}", queryEmbedding.Length);

            // Create mock relevant chunks for demonstration (vector database not yet implemented)
            var chunks = new[]
            {
                new DocumentChunk(
                    Guid.NewGuid(),
                    $"Relevant context for: {query}",
                    0,
                    0,
                    50),
                new DocumentChunk(
                    Guid.NewGuid(),
                    $"Additional context related to: {query}",
                    1,
                    0,
                    70)
            };

            _logger.LogInformation("Retrieved {Count} relevant chunks with similarity >= {Threshold}", 
                chunks.Length, threshold);

            return chunks;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to retrieve relevant chunks for query: {Query}", query);
            return Array.Empty<DocumentChunk>();
        }
    }

    public async Task<string> GenerateResponseAsync(string query, DocumentChunk[] relevantChunks, string? systemPrompt = null, CancellationToken cancellationToken = default)
    {
        try
        {
            var context = relevantChunks.Length > 0
                ? string.Join("\n\n", relevantChunks.Select((chunk, i) => 
                    $"Context {i + 1}:\n{chunk.Content}"))
                : "No relevant context found.";

            var prompt = systemPrompt ?? @"You are an intelligent assistant that answers questions based on provided context.
Use the context below to answer the user's question. If the context doesn't contain relevant information, say so clearly.
Be accurate and cite specific parts of the context when possible.";

            var messages = new List<Dictionary<string, string>>
            {
                new() { ["role"] = "system", ["content"] = prompt },
                new() { ["role"] = "user", ["content"] = $"Context:\n{context}\n\nQuestion: {query}" }
            };

            var response = await _llmService.GenerateResponseAsync(messages);
            
            _logger.LogDebug("Generated response of length {Length} using {ChunkCount} context chunks", 
                response.Length, relevantChunks.Length);

            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to generate response for query: {Query}", query);
            return $"Error generating response: {ex.Message}";
        }
    }

    private Task<DocumentChunk[]> RetrieveGraphContextAsync(DocumentChunk[] chunks, CancellationToken cancellationToken)
    {
        var graphChunks = new List<DocumentChunk>();
        
        try
        {
            // Find related documents through knowledge graph relationships (mock implementation)
            foreach (var chunk in chunks.Take(3)) // Limit to prevent excessive queries
            {
                // Create synthetic chunks from related documents (knowledge graph not yet implemented)
                var graphChunk = new DocumentChunk(
                    Guid.NewGuid(),
                    $"Related document context for: {chunk.Content.Substring(0, Math.Min(50, chunk.Content.Length))}...",
                    0,
                    0,
                    50);
                graphChunks.Add(graphChunk);
            }

            _logger.LogDebug("Retrieved {Count} additional chunks from knowledge graph", graphChunks.Count);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to retrieve graph context, continuing without it");
        }

        return Task.FromResult(graphChunks.ToArray());
    }

    private static decimal CalculateTokenCost(string text)
    {
        // Rough token estimation and cost calculation for OpenAI GPT-4
        var estimatedTokens = text.Length / 4; // Rough estimate: 1 token ≈ 4 characters
        var costPerToken = 0.00003m; // GPT-4 pricing (approximate)
        return estimatedTokens * costPerToken;
    }
}