using HART.MCP.Application.Tools;
using HART.MCP.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

namespace HART.MCP.Infrastructure.Tools;

public class SearchDocumentsTool : ITool
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<SearchDocumentsTool> _logger;

    public string Name => "SearchDocumentsTool";
    public string Description => "Searches through documents in the knowledge base";

    public SearchDocumentsTool(ApplicationDbContext context, ILogger<SearchDocumentsTool> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<string?> ExecuteAsync(Dictionary<string, object> parameters)
    {
        try
        {
            var query = parameters.GetValueOrDefault("input")?.ToString()
                       ?? parameters.GetValueOrDefault("query")?.ToString();

            if (string.IsNullOrEmpty(query))
            {
                return "Error: No search query provided";
            }

            // Simple text search across documents and chunks
            var documents = await _context.Documents
                .Include(d => d.Chunks)
                .Where(d => d.Title.Contains(query) || 
                           d.Content.Contains(query) ||
                           d.Chunks.Any(c => c.Content.Contains(query)))
                .Select(d => new {
                    d.Title,
                    d.Status,
                    d.Type,
                    ChunkCount = d.Chunks.Count,
                    MatchingChunks = d.Chunks
                        .Where(c => c.Content.Contains(query))
                        .Select(c => c.Content.Substring(0, Math.Min(200, c.Content.Length)))
                        .ToList()
                })
                .Take(10)
                .ToListAsync();

            if (!documents.Any())
            {
                return $"No documents found matching '{query}'";
            }

            var results = documents.Select(d => 
                $"**{d.Title}** (Type: {d.Type}, Status: {d.Status}, {d.ChunkCount} chunks)\n" +
                (d.MatchingChunks.Any() ? 
                    "Matching content:\n" + string.Join("\n", d.MatchingChunks.Select(c => $"- {c}...")) : 
                    "Title/metadata match"));

            _logger.LogInformation("Document search for '{Query}' found {Count} results", query, documents.Count);

            return $"Found {documents.Count} documents matching '{query}':\n\n" + string.Join("\n\n", results);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error searching documents");
            return $"Error searching documents: {ex.Message}";
        }
    }
}