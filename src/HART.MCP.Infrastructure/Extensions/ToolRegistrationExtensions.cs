using HART.MCP.Application.Services;
using HART.MCP.Application.Tools;
using HART.MCP.Infrastructure.Tools;
using HART.MCP.Infrastructure.Persistence;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace HART.MCP.Infrastructure.Extensions;

public static class ToolRegistrationExtensions
{
    public static IServiceCollection RegisterInfrastructureTools(this IServiceCollection services)
    {
        services.AddSingleton<IToolRegistry>(provider =>
        {
            var registry = new ToolRegistry();
            
            // Register all tools
            registry.RegisterTool(new FinishTool());
            registry.RegisterTool(new TestTool());
            registry.RegisterTool(new RagTool(provider.GetRequiredService<IRagOrchestrator>()));
            registry.RegisterTool(new WriteToSharedStateTool(provider.GetRequiredService<IProjectStateService>()));
            registry.RegisterTool(new ReadFromSharedStateTool(provider.GetRequiredService<IProjectStateService>()));
            
            // Database-dependent tools need to be created with scope
            var scope = provider.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            var loggerFactory = provider.GetRequiredService<ILoggerFactory>();
            
            registry.RegisterTool(new SearchDocumentsTool(context, loggerFactory.CreateLogger<SearchDocumentsTool>()));
            registry.RegisterTool(new ListAgentsTool(context, loggerFactory.CreateLogger<ListAgentsTool>()));
            
            return registry;
        });
        
        return services;
    }
}