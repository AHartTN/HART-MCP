using HART.MCP.Domain.Common;
using HART.MCP.Infrastructure.Persistence;
using HART.MCP.Infrastructure.Persistence.Repositories;
using HART.MCP.Infrastructure.Data;
using HART.MCP.Shared.Configuration;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace HART.MCP.Infrastructure.Extensions;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddInfrastructureServices(this IServiceCollection services, IConfiguration configuration)
    {
        // Database Context
        services.AddDbContext<ApplicationDbContext>(options =>
            options.UseSqlServer(configuration.GetConnectionString("DefaultConnection") 
                ?? configuration.GetSection("Database:SqlServerConnectionString").Value));

        // Unit of Work
        services.AddScoped<IUnitOfWork>(provider => provider.GetRequiredService<ApplicationDbContext>());

        // Repositories
        services.AddScoped(typeof(IRepository<>), typeof(BaseRepository<>));
        
        // Data seeder
        services.AddScoped<DatabaseSeeder>();

        // Health Checks
        services.AddHealthChecks()
            .AddDbContextCheck<ApplicationDbContext>("database");

        return services;
    }
}

// Placeholder health check classes - would need full implementation
public class MilvusHealthCheck : Microsoft.Extensions.Diagnostics.HealthChecks.IHealthCheck
{
    private readonly IConfiguration _configuration;
    
    public MilvusHealthCheck(IConfiguration configuration)
    {
        _configuration = configuration;
    }
    
    public async Task<Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult> CheckHealthAsync(
        Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckContext context, 
        CancellationToken cancellationToken = default)
    {
        // Implementation would check Milvus connectivity
        await Task.Delay(1, cancellationToken);
        return Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult.Healthy();
    }
}

public class Neo4jHealthCheck : Microsoft.Extensions.Diagnostics.HealthChecks.IHealthCheck
{
    private readonly IConfiguration _configuration;
    
    public Neo4jHealthCheck(IConfiguration configuration)
    {
        _configuration = configuration;
    }
    
    public async Task<Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult> CheckHealthAsync(
        Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckContext context, 
        CancellationToken cancellationToken = default)
    {
        // Implementation would check Neo4j connectivity
        await Task.Delay(1, cancellationToken);
        return Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult.Healthy();
    }
}