using HART.MCP.Application.Agents;
using HART.MCP.Application.Tools;
using HART.MCP.Application.Services;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;

namespace HART.MCP.API;

public static class AgentTester
{
    public static async Task<string> TestAgentExecution()
    {
        var services = new ServiceCollection();
        services.AddLogging(builder => builder.AddConsole());
        services.AddSingleton<IProjectStateService, ProjectStateService>();
        services.AddSingleton<ILlmService, LlmService>();
        
        services.AddSingleton<IToolRegistry>(provider =>
        {
            var registry = new ToolRegistry();
            registry.RegisterTool(new FinishTool());
            registry.RegisterTool(new TestTool());
            return registry;
        });
        
        var serviceProvider = services.BuildServiceProvider();
        
        var updateCallback = new Func<Dictionary<string, object>, Task>(async (update) =>
        {
            Console.WriteLine($"Update: {string.Join(", ", update.Select(kv => $"{kv.Key}={kv.Value}"))}");
            await Task.CompletedTask;
        });

        var toolRegistry = serviceProvider.GetRequiredService<IToolRegistry>();
        var llmService = serviceProvider.GetRequiredService<ILlmService>();
        var projectState = serviceProvider.GetRequiredService<IProjectStateService>();
        var loggerFactory = serviceProvider.GetRequiredService<ILoggerFactory>();

        var agent = new SpecialistAgent(
            1,
            "TestSpecialist",
            "Test Specialist Agent",
            toolRegistry,
            llmService,
            projectState,
            loggerFactory.CreateLogger<SpecialistAgent>(),
            updateCallback);

        try
        {
            var result = await agent.RunAsync("Hello, please test the system and return a result");
            return $"SUCCESS: {result}";
        }
        catch (Exception ex)
        {
            return $"ERROR: {ex.Message}";
        }
    }
}