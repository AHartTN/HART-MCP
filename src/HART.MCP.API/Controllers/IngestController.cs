using Microsoft.AspNetCore.Mvc;

namespace HART.MCP.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class IngestController : ControllerBase
{
    private readonly ILogger<IngestController> _logger;

    public IngestController(ILogger<IngestController> logger)
    {
        _logger = logger;
    }

    [HttpPost("document")]
    public IActionResult IngestDocument([FromBody] IngestRequest request)
    {
        try
        {
            var documentId = Guid.NewGuid();
            var chunks = ChunkText(request.Content ?? "", request.ChunkSize ?? 1000, request.Overlap ?? 100);

            _logger.LogInformation("Document ingested: {DocumentId}, Chunks: {ChunkCount}", documentId, chunks.Count);

            return Ok(new { 
                document_id = documentId,
                chunks_created = chunks.Count,
                status = "success",
                message = "Document ingested (mock implementation)"
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Document ingestion failed");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    private List<string> ChunkText(string text, int chunkSize, int overlap)
    {
        var chunks = new List<string>();
        var currentIndex = 0;

        while (currentIndex < text.Length)
        {
            var endIndex = Math.Min(currentIndex + chunkSize, text.Length);
            var chunk = text.Substring(currentIndex, endIndex - currentIndex);
            chunks.Add(chunk);

            currentIndex += chunkSize - overlap;
            if (currentIndex >= text.Length) break;
        }

        return chunks;
    }

    public class IngestRequest
    {
        public string? Content { get; set; }
        public string? Title { get; set; }
        public string? ContentType { get; set; }
        public string? Source { get; set; }
        public int? ChunkSize { get; set; }
        public int? Overlap { get; set; }
    }
}