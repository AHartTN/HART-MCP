using HART.MCP.Infrastructure.VectorDatabase;
using HART.MCP.Infrastructure.KnowledgeGraph;
using HART.MCP.Infrastructure.Monitoring;
using HART.MCP.Infrastructure.Services;
using HART.MCP.Application.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace HART.MCP.Infrastructure.Extensions;

public static class InfrastructureServiceExtensions
{
    public static IServiceCollection AddInfrastructureServices(
        this IServiceCollection services, 
        IConfiguration configuration,
        IHostEnvironment environment)
    {
        // Basic infrastructure services (database, repositories)
        ServiceCollectionExtensions.AddInfrastructureServices(services, configuration);
        
        // RAG Orchestrator service
        services.AddScoped<IRagOrchestrator, RagOrchestrator>();
        
        // Register all tools including database-dependent ones
        services.RegisterInfrastructureTools();
        
        // Vector database - temporarily disabled due to API changes
        // services.AddHttpClient<HttpMilvusService>();
        // services.AddScoped<IMilvusService, HttpMilvusService>();
        
        // Knowledge graph - temporarily disabled due to API changes
        // services.AddScoped<INeo4jService, Neo4jService>();
        
        // Monitoring - temporarily disabled to get API running
        // services.AddMonitoringServices(configuration, environment);
        
        return services;
    }
}