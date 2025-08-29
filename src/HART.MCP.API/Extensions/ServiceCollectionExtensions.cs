using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Hosting;
using Microsoft.OpenApi.Models;
using HART.MCP.Shared.Extensions;
using HART.MCP.Application.Extensions;
// using InfraExtensions = HART.MCP.Infrastructure.Extensions;
using HART.MCP.AI.Extensions;

namespace HART.MCP.API.Extensions;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddApiServices(this IServiceCollection services, IConfiguration configuration)
    {
        // CORS
        services.AddCors(options =>
        {
            options.AddDefaultPolicy(builder =>
            {
                builder.AllowAnyOrigin()
                       .AllowAnyMethod()
                       .AllowAnyHeader();
            });
        });

        // Swagger/OpenAPI
        services.AddSwaggerGen(c =>
        {
            c.SwaggerDoc("v1", new OpenApiInfo 
            { 
                Title = "HART-MCP API", 
                Version = "v1",
                Description = "Multi-Agent Control Plane with RAG and Tree of Thought"
            });
        });

        // Health Checks
        services.AddHealthChecks();

        return services;
    }

    public static IServiceCollection AddWebServices(this IServiceCollection services, IConfiguration configuration, IHostEnvironment environment)
    {
        // Configure Kestrel server options
        services.Configure<Microsoft.AspNetCore.Server.Kestrel.Core.KestrelServerOptions>(serverOptions =>
        {
            serverOptions.AddServerHeader = false;
            serverOptions.Limits.MaxConcurrentConnections = 1000;
            serverOptions.Limits.MaxConcurrentUpgradedConnections = 1000;
            serverOptions.Limits.MaxRequestBodySize = 52428800; // 50MB
            serverOptions.Limits.RequestHeadersTimeout = TimeSpan.FromSeconds(30);
            serverOptions.Limits.KeepAliveTimeout = TimeSpan.FromMinutes(2);
        });

        // Modern JSON configuration using native .NET 8
        services.ConfigureHttpJsonOptions(options =>
        {
            options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
            options.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
            options.SerializerOptions.PropertyNameCaseInsensitive = true;
            options.SerializerOptions.WriteIndented = environment.IsDevelopment();
        });

        // Controllers with native model validation
        services.AddControllers(options =>
        {
            options.SuppressAsyncSuffixInActionNames = false;
            options.Filters.Add<Microsoft.AspNetCore.Mvc.ProducesResponseTypeAttribute>();
        })
        .AddJsonOptions(options =>
        {
            options.JsonSerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
            options.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
            options.JsonSerializerOptions.WriteIndented = environment.IsDevelopment();
        })
        .ConfigureApiBehaviorOptions(options =>
        {
            // Use native validation problem details
            options.InvalidModelStateResponseFactory = context =>
            {
                var problemDetails = new Microsoft.AspNetCore.Mvc.ValidationProblemDetails(context.ModelState)
                {
                    Type = "https://tools.ietf.org/html/rfc7231#section-6.5.1",
                    Title = "One or more validation errors occurred.",
                    Status = 400,
                    Instance = context.HttpContext.Request.Path
                };
                return new Microsoft.AspNetCore.Mvc.BadRequestObjectResult(problemDetails);
            };
        });

        // Modern endpoints
        services.AddEndpointsApiExplorer();

        // HTTP logging for development
        if (environment.IsDevelopment())
        {
            services.AddHttpLogging(options =>
            {
                options.LoggingFields = Microsoft.AspNetCore.HttpLogging.HttpLoggingFields.RequestPath |
                                      Microsoft.AspNetCore.HttpLogging.HttpLoggingFields.RequestMethod |
                                      Microsoft.AspNetCore.HttpLogging.HttpLoggingFields.ResponseStatusCode |
                                      Microsoft.AspNetCore.HttpLogging.HttpLoggingFields.Duration;
            });
        }

        // Performance optimizations
        services.AddResponseCompression(options =>
        {
            options.EnableForHttps = true;
        });
        
        services.AddResponseCaching();
        services.AddMemoryCache();

        // Security
        services.AddHsts(options =>
        {
            options.Preload = true;
            options.IncludeSubDomains = true;
            options.MaxAge = TimeSpan.FromDays(365);
        });

        services.Configure<ForwardedHeadersOptions>(options =>
        {
            options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
        });

        // Native rate limiting
        services.AddRateLimiter(options =>
        {
            options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(httpContext =>
                RateLimitPartition.GetFixedWindowLimiter(
                    partitionKey: httpContext.User.Identity?.Name ?? httpContext.Request.Headers.Host.ToString(),
                    factory: partition => new FixedWindowRateLimiterOptions
                    {
                        AutoReplenishment = true,
                        PermitLimit = 100,
                        Window = TimeSpan.FromMinutes(1)
                    }));
        });

        // Application layers
        services.AddSharedServices(configuration);
        services.AddApplicationServices(configuration);
        // Infrastructure disabled due to API compatibility issues
        // InfraExtensions.InfrastructureServiceExtensions.AddInfrastructureServices(services, configuration, environment);
        services.AddAIServices();
        services.AddApiServices(configuration);

        return services;
    }
}