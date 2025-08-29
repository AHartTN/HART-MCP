using Microsoft.AspNetCore.Mvc;

namespace HART.MCP.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class DocumentsController : ControllerBase
{
    private readonly ILogger<DocumentsController> _logger;

    public DocumentsController(ILogger<DocumentsController> logger)
    {
        _logger = logger;
    }

    [HttpGet]
    public IActionResult GetDocuments()
    {
        return Ok(new { 
            documents = new object[0],
            count = 0,
            message = "Document storage not yet implemented" 
        });
    }

    [HttpGet("{id:guid}")]
    public IActionResult GetDocument(Guid id)
    {
        return NotFound(new { message = "Document not found", id });
    }

    [HttpPost]
    public IActionResult CreateDocument([FromBody] object request)
    {
        var documentId = Guid.NewGuid();
        return CreatedAtAction(nameof(GetDocument), new { id = documentId }, new { 
            id = documentId, 
            status = "created",
            message = "Document creation not fully implemented"
        });
    }
}