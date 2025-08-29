namespace HART.MCP.Infrastructure.Monitoring;

public interface IPerformanceMonitor
{
    IDisposable BeginOperation(string operationName);
    void RecordDuration(string operationName, TimeSpan duration);
    void RecordCounter(string counterName, int value = 1);
    void RecordGauge(string gaugeName, double value);
    Task<HealthCheckResult> CheckHealthAsync();
}

public class HealthCheckResult
{
    public bool IsHealthy { get; set; }
    public string Status { get; set; } = string.Empty;
    public Dictionary<string, object> Data { get; set; } = new();
    public TimeSpan Duration { get; set; }
}