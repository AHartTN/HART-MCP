using Microsoft.Extensions.DependencyInjection;
using HART.MCP.Application.Services;
using HART.MCP.AI.Abstractions;

namespace HART.MCP.AI.Extensions;

public static class AIServiceExtensions
{
    public static IServiceCollection AddAIServices(this IServiceCollection services)
    {
        services.AddSingleton<ILlmService, HART.MCP.Application.Services.LlmService>();
        services.AddSingleton<HART.MCP.AI.Abstractions.IEmbeddingService, HART.MCP.AI.Services.EmbeddingService>();
        services.AddSingleton<IRAGService, HART.MCP.AI.Services.RAGService>();
        
        return services;
    }
}