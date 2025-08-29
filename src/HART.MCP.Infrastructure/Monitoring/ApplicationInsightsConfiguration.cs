using Microsoft.ApplicationInsights.AspNetCore.Extensions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Serilog;
using Serilog.Events;

namespace HART.MCP.Infrastructure.Monitoring;

public static class ApplicationInsightsConfiguration
{
    public static IServiceCollection AddMonitoringServices(
        this IServiceCollection services,
        IConfiguration configuration,
        IHostEnvironment environment)
    {
        // Configure Application Insights
        services.AddApplicationInsightsTelemetry(options =>
        {
            options.ConnectionString = configuration["ApplicationInsights:ConnectionString"];
            options.EnableAdaptiveSampling = true;
            options.EnableQuickPulseMetricStream = true;
            options.EnableAuthenticationTrackingJavaScript = true;
            options.EnableDependencyTrackingTelemetryModule = true;
            options.EnableEventCounterCollectionModule = true;
        });

        // Configure Serilog
        ConfigureSerilog(configuration, environment);

        // Add custom telemetry
        services.AddSingleton<ITelemetryService, TelemetryService>();

        return services;
    }

    private static void ConfigureSerilog(IConfiguration configuration, IHostEnvironment environment)
    {
        var loggerConfig = new LoggerConfiguration()
            .ReadFrom.Configuration(configuration)
            .Enrich.FromLogContext()
            .Enrich.WithEnvironmentName()
            .Enrich.WithMachineName()
            .Enrich.WithProcessId()
            .Enrich.WithProcessName()
            .Enrich.WithThreadId()
            .WriteTo.Console(
                outputTemplate: "[{Timestamp:HH:mm:ss} {Level:u3}] {Message:lj} {Properties:j}{NewLine}{Exception}")
            .WriteTo.File(
                path: "logs/hart-mcp-.txt",
                rollingInterval: RollingInterval.Day,
                retainedFileCountLimit: 30,
                outputTemplate: "{Timestamp:yyyy-MM-dd HH:mm:ss.fff zzz} [{Level:u3}] {Message:lj} {Properties:j}{NewLine}{Exception}");

        // Add Application Insights sink in production
        if (environment.IsProduction())
        {
            var instrumentationKey = configuration["ApplicationInsights:InstrumentationKey"];
            if (!string.IsNullOrEmpty(instrumentationKey))
            {
                loggerConfig.WriteTo.ApplicationInsights(
                    instrumentationKey, 
                    TelemetryConverter.Traces,
                    LogEventLevel.Information);
            }
        }

        // Set minimum log levels based on environment
        if (environment.IsDevelopment())
        {
            loggerConfig.MinimumLevel.Debug()
                       .MinimumLevel.Override("Microsoft", LogEventLevel.Information)
                       .MinimumLevel.Override("System", LogEventLevel.Warning);
        }
        else
        {
            loggerConfig.MinimumLevel.Information()
                       .MinimumLevel.Override("Microsoft", LogEventLevel.Warning)
                       .MinimumLevel.Override("System", LogEventLevel.Error);
        }

        Log.Logger = loggerConfig.CreateLogger();
    }
}