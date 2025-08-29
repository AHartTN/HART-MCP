using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace HART.MCP.Application.Services;

public class ProjectStateService : IProjectStateService
{
    private readonly ConcurrentDictionary<string, object> _state = new();
    private readonly ILogger<ProjectStateService> _logger;

    public ProjectStateService(ILogger<ProjectStateService> logger)
    {
        _logger = logger;
    }

    public Task<T?> GetAsync<T>(string key)
    {
        try
        {
            if (_state.TryGetValue(key, out var value))
            {
                if (value is T directValue)
                {
                    return Task.FromResult<T?>(directValue);
                }

                // Try to deserialize if it's a JSON string
                if (value is string jsonValue && typeof(T) != typeof(string))
                {
                    try
                    {
                        var deserialized = JsonSerializer.Deserialize<T>(jsonValue);
                        return Task.FromResult(deserialized);
                    }
                    catch (JsonException ex)
                    {
                        _logger.LogWarning(ex, "Failed to deserialize value for key {Key} to type {Type}", key, typeof(T).Name);
                    }
                }

                // Try direct conversion
                try
                {
                    var converted = (T)Convert.ChangeType(value, typeof(T));
                    return Task.FromResult<T?>(converted);
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Failed to convert value for key {Key} to type {Type}", key, typeof(T).Name);
                }
            }

            return Task.FromResult<T?>(default);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving value for key {Key}", key);
            return Task.FromResult<T?>(default);
        }
    }

    public Task SetAsync<T>(string key, T value)
    {
        try
        {
            if (value == null)
            {
                _state.TryRemove(key, out _);
                _logger.LogDebug("Removed key {Key} from project state", key);
            }
            else
            {
                // Store complex objects as JSON strings
                if (typeof(T) != typeof(string) && typeof(T).IsClass && typeof(T) != typeof(object))
                {
                    var jsonValue = JsonSerializer.Serialize(value);
                    _state.AddOrUpdate(key, jsonValue, (_, _) => jsonValue);
                }
                else
                {
                    _state.AddOrUpdate(key, value, (_, _) => value);
                }

                _logger.LogDebug("Set key {Key} in project state with type {Type}", key, typeof(T).Name);
            }

            return Task.CompletedTask;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error setting value for key {Key}", key);
            return Task.CompletedTask;
        }
    }

    public Task<Dictionary<string, object>> GetAllAsync()
    {
        try
        {
            var snapshot = _state.ToDictionary(kvp => kvp.Key, kvp => kvp.Value);
            _logger.LogDebug("Retrieved {Count} items from project state", snapshot.Count);
            return Task.FromResult(snapshot);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving all project state");
            return Task.FromResult(new Dictionary<string, object>());
        }
    }

    public Task ClearAsync()
    {
        try
        {
            var count = _state.Count;
            _state.Clear();
            _logger.LogInformation("Cleared {Count} items from project state", count);
            return Task.CompletedTask;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error clearing project state");
            return Task.CompletedTask;
        }
    }

    public Task<bool> ContainsKeyAsync(string key)
    {
        return Task.FromResult(_state.ContainsKey(key));
    }

    public Task<bool> RemoveAsync(string key)
    {
        var removed = _state.TryRemove(key, out _);
        if (removed)
        {
            _logger.LogDebug("Removed key {Key} from project state", key);
        }
        return Task.FromResult(removed);
    }

    public Task<int> CountAsync()
    {
        return Task.FromResult(_state.Count);
    }

    public Task<IEnumerable<string>> GetKeysAsync()
    {
        return Task.FromResult<IEnumerable<string>>(_state.Keys.ToList());
    }
}