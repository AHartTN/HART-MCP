using HART.MCP.Application.Tools;
using HART.MCP.Application.Services;
using HART.MCP.AI.Services;
using Microsoft.OpenApi.Models;

namespace HART.MCP.API;

public class Program
{
    public static async Task Main(string[] args)
    {
        var builder = WebApplication.CreateBuilder(args);

        // Configure logging
        builder.Logging.ClearProviders()
            .AddConsole()
            .AddDebug();

        // Add services to the container
        builder.Services.AddControllers();
        builder.Services.AddEndpointsApiExplorer();

        // Swagger/OpenAPI
        builder.Services.AddSwaggerGen(c =>
        {
            c.SwaggerDoc("v1", new OpenApiInfo 
            { 
                Title = "HART-MCP API", 
                Version = "v1",
                Description = "Multi-Agent Control Plane with RAG"
            });
        });

        // Core services
        builder.Services.AddSingleton<IProjectStateService, ProjectStateService>();
        builder.Services.AddSingleton<ILlmService, HART.MCP.Application.Services.LlmService>();
        builder.Services.AddSingleton<HART.MCP.AI.Abstractions.IEmbeddingService, HART.MCP.AI.Services.EmbeddingService>();

        // Infrastructure services (optional - only if databases are available)
        // Infrastructure project disabled due to API compatibility issues
        // builder.Services.AddSingleton<HART.MCP.Infrastructure.VectorDatabase.IMilvusService, HART.MCP.Infrastructure.VectorDatabase.MilvusService>();
        // builder.Services.AddSingleton<HART.MCP.Infrastructure.KnowledgeGraph.INeo4jService, HART.MCP.Infrastructure.KnowledgeGraph.Neo4jService>();
        // builder.Services.AddSingleton<HART.MCP.Infrastructure.Caching.ICacheService, HART.MCP.Infrastructure.Caching.MemoryCacheService>();

        // AI services with real implementations
        builder.Services.AddSingleton<HART.MCP.AI.Abstractions.IRAGService, HART.MCP.AI.Services.RAGService>();

        // Tool registry with basic tools
        builder.Services.AddSingleton<IToolRegistry>(provider =>
        {
            var registry = new ToolRegistry();
            registry.RegisterTool(new FinishTool());
            registry.RegisterTool(new TestTool());
            return registry;
        });

        // CORS
        builder.Services.AddCors(options =>
        {
            options.AddDefaultPolicy(builder =>
            {
                builder.AllowAnyOrigin()
                       .AllowAnyMethod()
                       .AllowAnyHeader();
            });
        });

        // Health checks
        builder.Services.AddHealthChecks();

        var app = builder.Build();

        // Configure the HTTP request pipeline
        if (app.Environment.IsDevelopment())
        {
            app.UseSwagger();
            app.UseSwaggerUI(c =>
            {
                c.SwaggerEndpoint("/swagger/v1/swagger.json", "HART-MCP API v1");
                c.RoutePrefix = "api/docs";
            });
        }

        // Always enable Swagger for this demo
        app.UseSwagger();
        app.UseSwaggerUI(c =>
        {
            c.SwaggerEndpoint("/swagger/v1/swagger.json", "HART-MCP API v1");
            c.RoutePrefix = "api/docs";
        });

        app.UseHttpsRedirection();
        app.UseCors();

        // Map controllers
        app.MapControllers();

        // Health check endpoints
        app.MapHealthChecks("/health");
        app.MapHealthChecks("/health/ready");
        app.MapHealthChecks("/health/live");

        app.Logger.LogInformation("🚀 Starting HART-MCP API...");
        await app.RunAsync();
    }
}