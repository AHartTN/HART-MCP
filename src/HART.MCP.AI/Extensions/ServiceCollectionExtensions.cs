using HART.MCP.AI.Abstractions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace HART.MCP.AI.Extensions;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAIServices(this IServiceCollection services, IConfiguration configuration)
    {
        // AI Services - using placeholder implementations
        services.AddScoped<IEmbeddingService, Services.OpenAIEmbeddingService>();
        services.AddScoped<IRAGService, Services.RAGService>();
        
        // LLM Providers
        services.AddScoped<ILLMProvider, Services.OpenAIProvider>();
        
        // HTTP Clients for AI services
        services.AddHttpClient("OpenAI", client =>
        {
            client.BaseAddress = new Uri("https://api.openai.com/v1/");
            client.DefaultRequestHeaders.Add("User-Agent", "HART-MCP/1.0");
        });
        
        return services;
    }
}