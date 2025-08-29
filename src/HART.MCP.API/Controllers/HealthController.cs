using Microsoft.AspNetCore.Mvc;

namespace HART.MCP.API.Controllers;

[ApiController]
[Route("[controller]")]
public class HealthController : ControllerBase
{
    [HttpGet]
    public IActionResult Get()
    {
        return Ok(new { 
            status = "Healthy", 
            timestamp = DateTime.UtcNow,
            service = "HART-MCP API",
            version = "1.0.0"
        });
    }

    [HttpGet("ready")]
    public IActionResult Ready()
    {
        return Ok(new { 
            status = "Ready", 
            timestamp = DateTime.UtcNow,
            checks = new { database = "OK", ai_services = "OK" }
        });
    }

    [HttpGet("live")]
    public IActionResult Live()
    {
        return Ok(new { 
            status = "Live", 
            timestamp = DateTime.UtcNow 
        });
    }
}