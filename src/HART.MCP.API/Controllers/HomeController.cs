using Microsoft.AspNetCore.Mvc;

namespace HART.MCP.API.Controllers;

[ApiController]
[Route("")]
public class HomeController : ControllerBase
{
    [HttpGet]
    public IActionResult Index()
    {
        return Ok(new { 
            message = "HART-MCP Multi-Agent Control Plane API",
            version = "1.0.0",
            endpoints = new {
                health = "/health",
                api_docs = "/api/docs",
                mcp = "/api/mcp",
                test = "/api/mcp/test"
            }
        });
    }

    [HttpGet("api")]
    public IActionResult Api()
    {
        return Ok(new { 
            message = "HART-MCP API",
            endpoints = new {
                mcp = "/api/mcp",
                rag = "/api/rag",
                ingest = "/api/ingest",
                documents = "/api/documents"
            }
        });
    }
}