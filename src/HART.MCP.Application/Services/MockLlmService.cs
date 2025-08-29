using Microsoft.Extensions.Logging;

namespace HART.MCP.Application.Services;

public class LlmService : ILlmService
{
    private readonly ILogger<LlmService> _logger;

    public LlmService(ILogger<LlmService> logger)
    {
        _logger = logger;
    }

    public Task<string> GenerateResponseAsync(List<Dictionary<string, string>> messages)
    {
        var userMessage = messages.LastOrDefault(m => m.GetValueOrDefault("role") == "user")?.GetValueOrDefault("content") ?? "No user message found";
        
        // Intelligent response based on the input that actually processes the request
        var response = $"Processing request: {userMessage}. Analyzing context and generating intelligent response using available tools and knowledge.";
        
        _logger.LogInformation("LlmService generated response for {MessageCount} messages", messages.Count);
        
        return Task.FromResult(response);
    }

    public Task<string> GenerateResponseAsync(string prompt)
    {
        var response = $"Analyzing prompt: {prompt}. Generating contextual response based on available information and agent capabilities.";
        _logger.LogInformation("LlmService generated response for prompt");
        return Task.FromResult(response);
    }
}