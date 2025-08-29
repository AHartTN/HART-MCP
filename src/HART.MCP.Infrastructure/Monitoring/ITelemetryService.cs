namespace HART.MCP.Infrastructure.Monitoring;

public interface ITelemetryService
{
    void TrackEvent(string eventName, Dictionary<string, string>? properties = null, Dictionary<string, double>? metrics = null);
    void TrackDependency(string dependencyName, string commandName, DateTime startTime, TimeSpan duration, bool success);
    void TrackException(Exception exception, Dictionary<string, string>? properties = null);
    void TrackMetric(string name, double value, Dictionary<string, string>? properties = null);
    void TrackRequest(string name, DateTime startTime, TimeSpan duration, string responseCode, bool success);
    IDisposable StartOperation(string operationName);
}