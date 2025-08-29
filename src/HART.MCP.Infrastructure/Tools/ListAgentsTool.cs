using HART.MCP.Application.Tools;
using HART.MCP.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

namespace HART.MCP.Infrastructure.Tools;

public class ListAgentsTool : ITool
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<ListAgentsTool> _logger;

    public string Name => "ListAgentsTool";
    public string Description => "Lists all available agents in the system";

    public ListAgentsTool(ApplicationDbContext context, ILogger<ListAgentsTool> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<string?> ExecuteAsync(Dictionary<string, object> parameters)
    {
        try
        {
            var agents = await _context.Agents
                .Where(a => a.Status == Domain.Entities.AgentStatus.Active)
                .Select(a => new {
                    a.Name,
                    a.Description,
                    a.Type,
                    a.Status,
                    a.CreatedAt
                })
                .ToListAsync();

            if (!agents.Any())
            {
                return "No active agents found in the system";
            }

            var results = agents.Select(a => 
                $"**{a.Name}** (Type: {a.Type}, Status: {a.Status})\\n" +
                $"Description: {a.Description}\\n" +
                $"Created: {a.CreatedAt:yyyy-MM-dd}");

            _logger.LogInformation("Listed {Count} active agents", agents.Count);

            return $"Found {agents.Count} active agents:\\n\\n" + string.Join("\\n\\n", results);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error listing agents");
            return $"Error listing agents: {ex.Message}";
        }
    }
}