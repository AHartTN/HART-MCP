using Microsoft.Extensions.Logging;
using HART.MCP.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using HART.MCP.Application.Services;

namespace HART.MCP.Infrastructure.Services;

public class RagOrchestrator : IRagOrchestrator
{
    private readonly IEmbeddingService _embeddingService;
    private readonly ILlmService _llmService;
    private readonly ApplicationDbContext _context;
    private readonly ILogger<RagOrchestrator> _logger;

    public RagOrchestrator(
        IEmbeddingService embeddingService,
        ILlmService llmService,
        ApplicationDbContext context,
        ILogger<RagOrchestrator> logger)
    {
        _embeddingService = embeddingService;
        _llmService = llmService;
        _context = context;
        _logger = logger;
    }

    public async Task<string> GenerateResponseAsync(string query, Dictionary<string, object>? context = null, Func<Dictionary<string, object>, Task>? callback = null)
    {
        try
        {
            await NotifyCallback(callback, new Dictionary<string, object> { ["status"] = "starting_rag", ["query"] = query });

            // Generate query embedding
            var queryEmbedding = await _embeddingService.GenerateEmbeddingAsync(query);
            await NotifyCallback(callback, new Dictionary<string, object> { ["status"] = "embedding_generated" });

            // Perform document search and retrieval
            var relevantDocuments = await SearchRelevantDocumentsAsync(query);
            var contextText = BuildContextFromDocuments(relevantDocuments);
            
            await NotifyCallback(callback, new Dictionary<string, object> 
            { 
                ["status"] = "documents_retrieved", 
                ["document_count"] = relevantDocuments.Count 
            });

            // Generate LLM response
            var prompt = $@"Based on the following context, answer the user's question accurately and helpfully.

Context:
{contextText}

User Question: {query}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information, say so clearly.";

            await NotifyCallback(callback, new Dictionary<string, object> { ["status"] = "generating_llm_response" });

            var response = await _llmService.GenerateResponseAsync(prompt);

            await NotifyCallback(callback, new Dictionary<string, object> 
            { 
                ["status"] = "rag_complete", 
                ["response_length"] = response.Length,
                ["sources_used"] = relevantDocuments.Count
            });

            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "RAG orchestration failed for query: {Query}", query);
            await NotifyCallback(callback, new Dictionary<string, object> { ["error"] = ex.Message });
            throw;
        }
    }

    private async Task<List<DocumentResult>> SearchRelevantDocumentsAsync(string query)
    {
        try
        {
            // For now, do text-based search across documents and chunks
            // In production, this would use vector similarity search
            var documents = await _context.Documents
                .Include(d => d.Chunks)
                .Where(d => d.Status == Domain.Entities.DocumentStatus.Processed &&
                           (d.Title.Contains(query) || 
                            d.Content.Contains(query) ||
                            d.Chunks.Any(c => c.Content.Contains(query))))
                .Select(d => new DocumentResult
                {
                    Title = d.Title,
                    Content = d.Content.Length > 1000 ? d.Content.Substring(0, 1000) + "..." : d.Content,
                    RelevantChunks = d.Chunks
                        .Where(c => c.Content.Contains(query))
                        .Select(c => c.Content)
                        .Take(3)
                        .ToList()
                })
                .Take(5)
                .ToListAsync();

            _logger.LogInformation("Found {Count} relevant documents for query: {Query}", documents.Count, query);
            return documents;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error searching documents for query: {Query}", query);
            return new List<DocumentResult>();
        }
    }

    private string BuildContextFromDocuments(List<DocumentResult> documents)
    {
        if (!documents.Any())
        {
            return "No relevant documents found in the knowledge base.";
        }

        var contextParts = documents.Select(d =>
        {
            var content = d.RelevantChunks.Any() 
                ? string.Join("\n", d.RelevantChunks.Select(c => $"- {c}"))
                : d.Content;
            
            return $"Document: {d.Title}\nContent:\n{content}";
        });

        return string.Join("\n\n", contextParts);
    }

    private class DocumentResult
    {
        public string Title { get; set; } = string.Empty;
        public string Content { get; set; } = string.Empty;
        public List<string> RelevantChunks { get; set; } = new();
    }

    private static async Task NotifyCallback(Func<Dictionary<string, object>, Task>? callback, Dictionary<string, object> data)
    {
        if (callback != null)
        {
            try
            {
                await callback(data);
            }
            catch
            {
                // Ignore callback errors
                throw;
            }
        }
    }
}