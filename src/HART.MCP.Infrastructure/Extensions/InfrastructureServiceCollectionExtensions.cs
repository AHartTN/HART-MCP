using HART.MCP.Infrastructure.Caching;
using HART.MCP.Infrastructure.Resilience;
using HART.MCP.Infrastructure.ConnectionPooling;
using HART.MCP.Infrastructure.SqlClr;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Configuration;
using HART.MCP.Shared.Configuration;

namespace HART.MCP.Infrastructure.Extensions;

public static class InfrastructureServiceCollectionExtensions
{
    public static IServiceCollection AddInfrastructureServices(
        this IServiceCollection services, 
        IConfiguration configuration)
    {
        // Configuration
        services.Configure<DatabaseOptions>(configuration.GetSection("Database"));
        
        // Caching - use Redis if available, otherwise in-memory
        var redisConnectionString = configuration.GetConnectionString("Redis");
        if (!string.IsNullOrEmpty(redisConnectionString))
        {
            services.AddStackExchangeRedisCache(options =>
            {
                options.Configuration = redisConnectionString;
                options.InstanceName = "HART-MCP";
            });
            services.AddScoped<ICacheService, RedisCacheService>();
        }
        else
        {
            services.AddMemoryCache();
            services.AddScoped<ICacheService, MemoryCacheService>();
        }

        // Performance and resilience
        services.AddSingleton<IResilienceService, ResilienceService>();
        services.AddSingleton<IDatabaseConnectionPool, DatabaseConnectionPool>();
        
        // SQL CLR services
        services.AddScoped<IQuantumModelService, QuantumModelService>();
        
        return services;
    }
}