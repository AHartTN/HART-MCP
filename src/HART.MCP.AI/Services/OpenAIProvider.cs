using HART.MCP.AI.Abstractions;

namespace HART.MCP.AI.Services;

public class OpenAIProvider : ILLMProvider
{
    public string ProviderName => "OpenAI";

    public Task<LLMResponse> GenerateAsync(LLMRequest request, CancellationToken cancellationToken = default)
    {
        return Task.FromResult(new LLMResponse(
            "Sample LLM response",
            100,
            0.002m,
            TimeSpan.FromSeconds(2),
            request.Model ?? "gpt-3.5-turbo"));
    }

    public Task<LLMResponse> GenerateStreamAsync(LLMRequest request, IAsyncEnumerable<string> streamCallback, CancellationToken cancellationToken = default)
    {
        return GenerateAsync(request, cancellationToken);
    }

    public Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default)
    {
        return Task.FromResult(true);
    }

    public Task<LLMModelInfo[]> GetAvailableModelsAsync(CancellationToken cancellationToken = default)
    {
        return Task.FromResult(new[]
        {
            new LLMModelInfo("gpt-3.5-turbo", "GPT-3.5 Turbo", "Fast and efficient model", 4096, 0.002m, true)
        });
    }
}