using HART.MCP.AI.Abstractions;
using HART.MCP.Domain.Entities;
using Microsoft.AspNetCore.Mvc;

namespace HART.MCP.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RAGController : ControllerBase
{
    private readonly IRAGService _ragService;
    private readonly ILogger<RAGController> _logger;

    public RAGController(IRAGService ragService, ILogger<RAGController> logger)
    {
        _ragService = ragService;
        _logger = logger;
    }

    [HttpPost("query")]
    public async Task<ActionResult<RAGResponse>> Query([FromBody] RAGRequest request)
    {
        _logger.LogInformation("Processing RAG query: {Query}", request.Query);
        var result = await _ragService.QueryAsync(request);
        return Ok(result);
    }

    [HttpPost("query/tree-of-thought")]
    public async Task<ActionResult<RAGResponse>> QueryWithTreeOfThought([FromBody] TreeOfThoughtRAGRequest request)
    {
        _logger.LogInformation("Processing Tree of Thought RAG query: {Query}", request.Query);
        var result = await _ragService.QueryWithTreeOfThoughtAsync(request);
        return Ok(result);
    }

    [HttpPost("retrieve")]
    public async Task<ActionResult<DocumentChunk[]>> RetrieveChunks([FromBody] RetrieveChunksRequest request)
    {
        var chunks = await _ragService.RetrieveRelevantChunksAsync(
            request.Query, 
            request.MaxResults, 
            request.Threshold);
        return Ok(chunks);
    }
}

public record RetrieveChunksRequest(
    string Query,
    int MaxResults = 10,
    double Threshold = 0.7);