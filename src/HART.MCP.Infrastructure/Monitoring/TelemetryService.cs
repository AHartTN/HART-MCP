using Microsoft.ApplicationInsights;
using Microsoft.ApplicationInsights.DataContracts;
using Microsoft.Extensions.Logging;

namespace HART.MCP.Infrastructure.Monitoring;

public class TelemetryService : ITelemetryService
{
    private readonly TelemetryClient _telemetryClient;
    private readonly ILogger<TelemetryService> _logger;

    public TelemetryService(TelemetryClient telemetryClient, ILogger<TelemetryService> logger)
    {
        _telemetryClient = telemetryClient;
        _logger = logger;
    }

    public void TrackEvent(string eventName, Dictionary<string, string>? properties = null, Dictionary<string, double>? metrics = null)
    {
        try
        {
            _telemetryClient.TrackEvent(eventName, properties, metrics);
            _logger.LogDebug("Tracked event: {EventName}", eventName);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to track event: {EventName}", eventName);
        }
    }

    public void TrackDependency(string dependencyName, string commandName, DateTime startTime, TimeSpan duration, bool success)
    {
        try
        {
            _telemetryClient.TrackDependency(dependencyName, commandName, commandName, startTime, duration, success);
            _logger.LogDebug("Tracked dependency: {DependencyName} - {CommandName} ({Duration}ms)", 
                dependencyName, commandName, duration.TotalMilliseconds);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to track dependency: {DependencyName}", dependencyName);
        }
    }

    public void TrackException(Exception exception, Dictionary<string, string>? properties = null)
    {
        try
        {
            _telemetryClient.TrackException(exception, properties);
            _logger.LogError(exception, "Tracked exception: {ExceptionType}", exception.GetType().Name);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to track exception");
        }
    }

    public void TrackMetric(string name, double value, Dictionary<string, string>? properties = null)
    {
        try
        {
            _telemetryClient.TrackMetric(name, value, properties);
            _logger.LogDebug("Tracked metric: {MetricName} = {Value}", name, value);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to track metric: {MetricName}", name);
        }
    }

    public void TrackRequest(string name, DateTime startTime, TimeSpan duration, string responseCode, bool success)
    {
        try
        {
            _telemetryClient.TrackRequest(name, startTime, duration, responseCode, success);
            _logger.LogDebug("Tracked request: {RequestName} ({Duration}ms) - {ResponseCode}", 
                name, duration.TotalMilliseconds, responseCode);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to track request: {RequestName}", name);
        }
    }

    public IDisposable StartOperation(string operationName)
    {
        try
        {
            return _telemetryClient.StartOperation<RequestTelemetry>(operationName);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start operation: {OperationName}", operationName);
            return new NullDisposable();
        }
    }

    private class NullDisposable : IDisposable
    {
        public void Dispose() { }
    }
}