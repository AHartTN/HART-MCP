using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System.Text.Json;
using System.Text;
using HART.MCP.Application.Services;

namespace HART.MCP.AI.Services;

public class LlmService : ILlmService
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _configuration;
    private readonly ILogger<LlmService> _logger;
    private readonly string _apiKey;
    private readonly string _model;
    private readonly string _provider;

    public LlmService(HttpClient httpClient, IConfiguration configuration, ILogger<LlmService> logger)
    {
        _httpClient = httpClient;
        _configuration = configuration;
        _logger = logger;
        _provider = _configuration["AI:DefaultProvider"] ?? "Gemini";
        _apiKey = _configuration[$"AI:{_provider}:ApiKey"] ?? throw new InvalidOperationException($"API key not found for provider {_provider}");
        _model = _configuration[$"AI:{_provider}:Model"] ?? "gemini-pro";

        ConfigureHttpClient();
    }

    private void ConfigureHttpClient()
    {
        switch (_provider.ToLowerInvariant())
        {
            case "gemini":
                _httpClient.BaseAddress = new Uri("https://generativelanguage.googleapis.com/");
                break;
            case "openai":
                _httpClient.BaseAddress = new Uri("https://api.openai.com/");
                _httpClient.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _apiKey);
                break;
            case "anthropic":
                _httpClient.BaseAddress = new Uri("https://api.anthropic.com/");
                _httpClient.DefaultRequestHeaders.Add("x-api-key", _apiKey);
                _httpClient.DefaultRequestHeaders.Add("anthropic-version", "2023-06-01");
                break;
        }
    }

    public async Task<string> GenerateResponseAsync(List<Dictionary<string, string>> messages)
    {
        try
        {
            switch (_provider.ToLowerInvariant())
            {
                case "gemini":
                    return await CallGeminiAsync(messages);
                case "openai":
                    return await CallOpenAIAsync(messages);
                case "anthropic":
                    return await CallAnthropicAsync(messages);
                default:
                    throw new NotSupportedException($"Provider {_provider} not supported");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "LLM generation failed for provider {Provider}", _provider);
            throw;
        }
    }

    public async Task<string> GenerateResponseAsync(string prompt)
    {
        var messages = new List<Dictionary<string, string>>
        {
            new() { ["role"] = "user", ["content"] = prompt }
        };
        return await GenerateResponseAsync(messages);
    }

    private async Task<string> CallGeminiAsync(List<Dictionary<string, string>> messages)
    {
        var prompt = BuildPromptFromMessages(messages);
        
        var requestBody = new
        {
            contents = new[]
            {
                new
                {
                    parts = new[]
                    {
                        new { text = prompt }
                    }
                }
            },
            generationConfig = new
            {
                temperature = 0.7,
                maxOutputTokens = 2048,
                topP = 0.8,
                topK = 10
            }
        };

        var json = JsonSerializer.Serialize(requestBody);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync($"v1beta/models/{_model}:generateContent?key={_apiKey}", content);
        response.EnsureSuccessStatusCode();

        var responseJson = await response.Content.ReadAsStringAsync();
        var responseObj = JsonSerializer.Deserialize<JsonElement>(responseJson);
        
        return responseObj
            .GetProperty("candidates")[0]
            .GetProperty("content")
            .GetProperty("parts")[0]
            .GetProperty("text")
            .GetString() ?? "No response generated";
    }

    private async Task<string> CallOpenAIAsync(List<Dictionary<string, string>> messages)
    {
        var requestBody = new
        {
            model = _model,
            messages = messages.Select(m => new { role = m["role"], content = m["content"] }).ToArray(),
            temperature = 0.7,
            max_tokens = 2048
        };

        var json = JsonSerializer.Serialize(requestBody);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync("v1/chat/completions", content);
        response.EnsureSuccessStatusCode();

        var responseJson = await response.Content.ReadAsStringAsync();
        var responseObj = JsonSerializer.Deserialize<JsonElement>(responseJson);
        
        return responseObj
            .GetProperty("choices")[0]
            .GetProperty("message")
            .GetProperty("content")
            .GetString() ?? "No response generated";
    }

    private async Task<string> CallAnthropicAsync(List<Dictionary<string, string>> messages)
    {
        var systemMessage = messages.FirstOrDefault(m => m["role"] == "system")?["content"] ?? "";
        var userMessages = messages.Where(m => m["role"] != "system").ToList();

        var requestBody = new
        {
            model = _model,
            max_tokens = 2048,
            temperature = 0.7,
            system = systemMessage,
            messages = userMessages.Select(m => new { role = m["role"], content = m["content"] }).ToArray()
        };

        var json = JsonSerializer.Serialize(requestBody);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync("v1/messages", content);
        response.EnsureSuccessStatusCode();

        var responseJson = await response.Content.ReadAsStringAsync();
        var responseObj = JsonSerializer.Deserialize<JsonElement>(responseJson);
        
        return responseObj
            .GetProperty("content")[0]
            .GetProperty("text")
            .GetString() ?? "No response generated";
    }

    private static string BuildPromptFromMessages(List<Dictionary<string, string>> messages)
    {
        var prompt = new StringBuilder();
        
        foreach (var message in messages)
        {
            var role = message["role"];
            var content = message["content"];
            
            switch (role)
            {
                case "system":
                    prompt.AppendLine($"System: {content}");
                    break;
                case "user":
                    prompt.AppendLine($"Human: {content}");
                    break;
                case "assistant":
                    prompt.AppendLine($"Assistant: {content}");
                    break;
            }
        }
        
        prompt.AppendLine("Assistant:");
        return prompt.ToString();
    }
}