using Microsoft.Extensions.Logging;

namespace HART.MCP.Infrastructure.Resilience;

public interface IResilienceService
{
    Task<T> ExecuteAsync<T>(Func<Task<T>> operation, string operationName, CancellationToken cancellationToken = default);
    Task ExecuteAsync(Func<Task> operation, string operationName, CancellationToken cancellationToken = default);
}

public class ResilienceService : IResilienceService
{
    private readonly ILogger<ResilienceService> _logger;
    private readonly Dictionary<string, DateTime> _circuitBreakerState = new();
    private readonly Dictionary<string, int> _failureCounts = new();
    private readonly TimeSpan _circuitBreakerDuration = TimeSpan.FromSeconds(30);
    private const int _maxFailures = 3;

    public ResilienceService(ILogger<ResilienceService> logger)
    {
        _logger = logger;
    }

    public async Task<T> ExecuteAsync<T>(Func<Task<T>> operation, string operationName, CancellationToken cancellationToken = default)
    {
        // Check circuit breaker state
        if (IsCircuitBreakerOpen(operationName))
        {
            var ex = new InvalidOperationException($"Circuit breaker is open for operation: {operationName}");
            _logger.LogError(ex, "Circuit breaker is open for operation: {OperationName}", operationName);
            throw ex;
        }

        var maxRetries = 3;
        for (int attempt = 0; attempt <= maxRetries; attempt++)
        {
            try
            {
                _logger.LogDebug("Executing resilient operation: {OperationName}, Attempt: {Attempt}", operationName, attempt + 1);
                var result = await operation();
                
                // Reset failure count on success
                ResetFailureCount(operationName);
                return result;
            }
            catch (Exception ex) when (attempt < maxRetries && IsTransientException(ex))
            {
                var delay = TimeSpan.FromSeconds(Math.Pow(2, attempt));
                _logger.LogWarning("Retry {Retry} for {OperationName} in {Delay}ms due to: {Exception}",
                    attempt + 1, operationName, delay.TotalMilliseconds, ex.Message);
                
                await Task.Delay(delay, cancellationToken);
            }
            catch (Exception ex)
            {
                // Record failure and potentially open circuit breaker
                RecordFailure(operationName);
                _logger.LogError(ex, "Resilient operation failed: {OperationName}", operationName);
                throw;
            }
        }

        // All retries exhausted
        var finalEx = new InvalidOperationException($"Operation {operationName} failed after {maxRetries + 1} attempts");
        RecordFailure(operationName);
        _logger.LogError(finalEx, "Operation failed after all retries: {OperationName}", operationName);
        throw finalEx;
    }

    public async Task ExecuteAsync(Func<Task> operation, string operationName, CancellationToken cancellationToken = default)
    {
        await ExecuteAsync(async () =>
        {
            await operation();
            return true;
        }, operationName, cancellationToken);
    }

    private bool IsTransientException(Exception ex)
    {
        return ex is HttpRequestException or TaskCanceledException or TimeoutException;
    }

    private bool IsCircuitBreakerOpen(string operationName)
    {
        if (_circuitBreakerState.TryGetValue(operationName, out var openTime))
        {
            if (DateTime.UtcNow - openTime < _circuitBreakerDuration)
            {
                return true;
            }
            else
            {
                // Circuit breaker timeout expired, reset
                _circuitBreakerState.Remove(operationName);
                _failureCounts.Remove(operationName);
                _logger.LogInformation("Circuit breaker closed for operation: {OperationName}", operationName);
            }
        }
        return false;
    }

    private void RecordFailure(string operationName)
    {
        _failureCounts.TryGetValue(operationName, out var count);
        _failureCounts[operationName] = count + 1;

        if (_failureCounts[operationName] >= _maxFailures)
        {
            _circuitBreakerState[operationName] = DateTime.UtcNow;
            _logger.LogError("Circuit breaker opened for operation: {OperationName} after {Failures} failures", 
                operationName, _failureCounts[operationName]);
        }
    }

    private void ResetFailureCount(string operationName)
    {
        _failureCounts.Remove(operationName);
        _circuitBreakerState.Remove(operationName);
    }
}