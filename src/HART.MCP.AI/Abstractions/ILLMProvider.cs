namespace HART.MCP.AI.Abstractions;

public interface ILLMProvider
{
    string ProviderName { get; }
    Task<LLMResponse> GenerateAsync(LLMRequest request, CancellationToken cancellationToken = default);
    Task<LLMResponse> GenerateStreamAsync(LLMRequest request, IAsyncEnumerable<string> streamCallback, CancellationToken cancellationToken = default);
    Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default);
    Task<LLMModelInfo[]> GetAvailableModelsAsync(CancellationToken cancellationToken = default);
}

public record LLMRequest(
    string Prompt,
    string? SystemPrompt = null,
    string? Model = null,
    double? Temperature = null,
    int? MaxTokens = null,
    Dictionary<string, object>? Parameters = null);

public record LLMResponse(
    string Content,
    int TokensUsed,
    decimal Cost,
    TimeSpan Duration,
    string Model,
    Dictionary<string, object>? Metadata = null);

public record LLMModelInfo(
    string Id,
    string Name,
    string Description,
    int MaxTokens,
    decimal CostPerToken,
    bool SupportsStreaming);

public enum LLMProvider
{
    OpenAI,
    Anthropic,
    Gemini,
    Llama,
    Ollama
}