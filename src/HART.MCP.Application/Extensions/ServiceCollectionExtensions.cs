using System.Reflection;
using MediatR;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Hosting;
using System.ComponentModel.DataAnnotations;
using HART.MCP.Application.Services;
using HART.MCP.Application.Tools;

namespace HART.MCP.Application.Extensions;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddApplicationServices(this IServiceCollection services, IConfiguration configuration)
    {
        // Core services
        services.AddSingleton<IProjectStateService, ProjectStateService>();
        
        // Note: Tool registration is now handled by Infrastructure layer
        
        // MediatR with custom behaviors
        services.AddMediatR(cfg =>
        {
            cfg.RegisterServicesFromAssembly(Assembly.GetExecutingAssembly());
            cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(ValidationBehavior<,>));
            cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(LoggingBehavior<,>));
            cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(PerformanceBehavior<,>));
            cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(CachingBehavior<,>));
        });

        // Native .NET validation service
        services.AddSingleton<IValidationService, ValidationService>();

        // HTTP client with default timeout
        services.AddHttpClient("default", client =>
        {
            client.Timeout = TimeSpan.FromSeconds(30);
        });

        // Background services for async processing - TODO: Implement these services when needed
        // services.AddHostedService<DocumentProcessingService>();
        // services.AddHostedService<MetricsCollectionService>();

        return services;
    }

}

// Validation Service Interface and Implementation
public interface IValidationService
{
    Task<ValidationResult> ValidateAsync<T>(T instance, CancellationToken cancellationToken = default);
    ValidationResult Validate<T>(T instance);
}

public class ValidationService : IValidationService
{
    public async Task<ValidationResult> ValidateAsync<T>(T instance, CancellationToken cancellationToken = default)
    {
        return await Task.FromResult(Validate(instance));
    }

    public ValidationResult Validate<T>(T instance)
    {
        if (instance == null)
            return new ValidationResult("Instance cannot be null");

        var context = new ValidationContext(instance);
        var results = new List<ValidationResult>();
        
        bool isValid = Validator.TryValidateObject(instance, context, results, validateAllProperties: true);
        
        if (!isValid)
        {
            var errors = results.Select(r => r.ErrorMessage ?? "Unknown validation error");
            return new ValidationResult(string.Join("; ", errors));
        }

        return ValidationResult.Success!;
    }
}

// MediatR Pipeline Behaviors
public class ValidationBehavior<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
    where TRequest : notnull
{
    private readonly IValidationService _validationService;

    public ValidationBehavior(IValidationService validationService)
    {
        _validationService = validationService;
    }

    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken cancellationToken)
    {
        var validationResult = await _validationService.ValidateAsync(request, cancellationToken);
        
        if (validationResult != ValidationResult.Success)
        {
            throw new HART.MCP.Shared.Exceptions.ValidationException(
                validationResult.ErrorMessage ?? "Validation failed",
                new Dictionary<string, string[]> { { "Request", new[] { validationResult.ErrorMessage ?? "Validation failed" } } });
        }

        return await next();
    }
}

public class LoggingBehavior<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
    where TRequest : notnull
{
    private readonly ILogger<LoggingBehavior<TRequest, TResponse>> _logger;

    public LoggingBehavior(ILogger<LoggingBehavior<TRequest, TResponse>> logger)
    {
        _logger = logger;
    }

    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken cancellationToken)
    {
        var requestName = typeof(TRequest).Name;
        _logger.LogInformation("Handling {RequestName}", requestName);

        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        try
        {
            var response = await next();
            _logger.LogInformation("Handled {RequestName} in {ElapsedMs}ms", requestName, stopwatch.ElapsedMilliseconds);
            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling {RequestName} after {ElapsedMs}ms", requestName, stopwatch.ElapsedMilliseconds);
            throw;
        }
    }
}

public class PerformanceBehavior<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
    where TRequest : notnull
{
    private readonly ILogger<PerformanceBehavior<TRequest, TResponse>> _logger;

    public PerformanceBehavior(ILogger<PerformanceBehavior<TRequest, TResponse>> logger)
    {
        _logger = logger;
    }

    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken cancellationToken)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var response = await next();
        stopwatch.Stop();

        var elapsedMilliseconds = stopwatch.ElapsedMilliseconds;
        if (elapsedMilliseconds > 500) // Log slow requests
        {
            var requestName = typeof(TRequest).Name;
            _logger.LogWarning("Long running request: {RequestName} ({ElapsedMs}ms)", requestName, elapsedMilliseconds);
        }

        return response;
    }
}

public class CachingBehavior<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
    where TRequest : notnull
{
    // Implementation would depend on caching strategy
    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken cancellationToken)
    {
        // For now, just pass through - implement caching logic based on request type
        return await next();
    }
}

// Background Services
public class DocumentProcessingService : BackgroundService
{
    private readonly ILogger<DocumentProcessingService> _logger;
    private readonly IServiceProvider _serviceProvider;

    public DocumentProcessingService(ILogger<DocumentProcessingService> logger, IServiceProvider serviceProvider)
    {
        _logger = logger;
        _serviceProvider = serviceProvider;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Document processing service started");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using var scope = _serviceProvider.CreateScope();
                // Process pending documents asynchronously
                await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in document processing service");
                await Task.Delay(TimeSpan.FromMinutes(5), stoppingToken);
            }
        }

        _logger.LogInformation("Document processing service stopped");
    }
}

public class MetricsCollectionService : BackgroundService
{
    private readonly ILogger<MetricsCollectionService> _logger;

    public MetricsCollectionService(ILogger<MetricsCollectionService> logger)
    {
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Metrics collection service started");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                // Collect and emit metrics
                await Task.Delay(TimeSpan.FromSeconds(30), stoppingToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in metrics collection service");
                await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
            }
        }

        _logger.LogInformation("Metrics collection service stopped");
    }
}