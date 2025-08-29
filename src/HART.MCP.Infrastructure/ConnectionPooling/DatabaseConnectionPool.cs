using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using HART.MCP.Shared.Configuration;
using System.Collections.Concurrent;

namespace HART.MCP.Infrastructure.ConnectionPooling;

public interface IDatabaseConnectionPool : IDisposable
{
    Task<SqlConnection> GetConnectionAsync(CancellationToken cancellationToken = default);
    Task ReturnConnectionAsync(SqlConnection connection);
    Task<T> ExecuteWithConnectionAsync<T>(Func<SqlConnection, Task<T>> operation, CancellationToken cancellationToken = default);
    Task ExecuteWithConnectionAsync(Func<SqlConnection, Task> operation, CancellationToken cancellationToken = default);
}

public class DatabaseConnectionPool : IDatabaseConnectionPool, IDisposable
{
    private readonly ILogger<DatabaseConnectionPool> _logger;
    private readonly DatabaseOptions _options;
    private readonly ConcurrentQueue<SqlConnection> _availableConnections = new();
    private readonly SemaphoreSlim _connectionSemaphore;
    private readonly Timer _maintenanceTimer;
    private int _activeConnections;
    private bool _disposed;

    public DatabaseConnectionPool(ILogger<DatabaseConnectionPool> logger, IOptions<DatabaseOptions> options)
    {
        _logger = logger;
        _options = options.Value;
        _connectionSemaphore = new SemaphoreSlim(_options.MaxPoolSize, _options.MaxPoolSize);
        
        // Initialize pool with minimum connections
        InitializePool();
        
        // Start maintenance timer (clean up idle connections every 5 minutes)
        _maintenanceTimer = new Timer(PerformMaintenance, null, 
            TimeSpan.FromMinutes(5), TimeSpan.FromMinutes(5));
    }

    public async Task<SqlConnection> GetConnectionAsync(CancellationToken cancellationToken = default)
    {
        if (_disposed)
            throw new ObjectDisposedException(nameof(DatabaseConnectionPool));

        await _connectionSemaphore.WaitAsync(cancellationToken);

        try
        {
            // Try to get an existing connection
            if (_availableConnections.TryDequeue(out var connection))
            {
                // Validate connection is still good
                if (await IsConnectionValidAsync(connection))
                {
                    _logger.LogDebug("Reusing pooled connection. Active: {ActiveConnections}", _activeConnections);
                    return connection;
                }
                else
                {
                    await SafeDisposeConnection(connection);
                }
            }

            // Create new connection
            connection = new SqlConnection(_options.SqlServerConnectionString);
            await connection.OpenAsync(cancellationToken);
            
            Interlocked.Increment(ref _activeConnections);
            
            _logger.LogDebug("Created new pooled connection. Active: {ActiveConnections}", _activeConnections);
            return connection;
        }
        catch
        {
            _connectionSemaphore.Release();
            throw;
        }
    }

    public async Task ReturnConnectionAsync(SqlConnection connection)
    {
        if (_disposed || connection == null)
        {
            await SafeDisposeConnection(connection);
            _connectionSemaphore.Release();
            return;
        }

        try
        {
            if (connection.State == System.Data.ConnectionState.Open && 
                await IsConnectionValidAsync(connection))
            {
                _availableConnections.Enqueue(connection);
                _logger.LogDebug("Returned connection to pool. Available: {AvailableConnections}", 
                    _availableConnections.Count);
            }
            else
            {
                await SafeDisposeConnection(connection);
                Interlocked.Decrement(ref _activeConnections);
            }
        }
        finally
        {
            _connectionSemaphore.Release();
        }
    }

    public async Task<T> ExecuteWithConnectionAsync<T>(Func<SqlConnection, Task<T>> operation, CancellationToken cancellationToken = default)
    {
        var connection = await GetConnectionAsync(cancellationToken);
        try
        {
            return await operation(connection);
        }
        finally
        {
            await ReturnConnectionAsync(connection);
        }
    }

    public async Task ExecuteWithConnectionAsync(Func<SqlConnection, Task> operation, CancellationToken cancellationToken = default)
    {
        await ExecuteWithConnectionAsync(async connection =>
        {
            await operation(connection);
            return true;
        }, cancellationToken);
    }

    private void InitializePool()
    {
        var minConnections = _options.MinPoolSize;
        
        Task.Run(async () =>
        {
            for (int i = 0; i < minConnections; i++)
            {
                try
                {
                    var connection = new SqlConnection(_options.SqlServerConnectionString);
                    await connection.OpenAsync();
                    _availableConnections.Enqueue(connection);
                    Interlocked.Increment(ref _activeConnections);
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Failed to initialize connection {Index} in pool", i);
                }
            }
            
            _logger.LogInformation("Initialized connection pool with {ConnectionCount} connections", 
                _availableConnections.Count);
        });
    }

    private async Task<bool> IsConnectionValidAsync(SqlConnection connection)
    {
        try
        {
            if (connection.State != System.Data.ConnectionState.Open)
                return false;

            // Quick validation query
            using var command = new SqlCommand("SELECT 1", connection);
            command.CommandTimeout = 5;
            await command.ExecuteScalarAsync();
            return true;
        }
        catch
        {
            return false;
        }
    }

    private async Task SafeDisposeConnection(SqlConnection? connection)
    {
        if (connection == null) return;
        
        try
        {
            if (connection.State == System.Data.ConnectionState.Open)
                await connection.CloseAsync();
            connection.Dispose();
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Error disposing connection");
        }
    }

    private async void PerformMaintenance(object? state)
    {
        if (_disposed) return;

        try
        {
            var connectionsToRemove = new List<SqlConnection>();
            var connectionsToKeep = new List<SqlConnection>();

            // Check all available connections
            while (_availableConnections.TryDequeue(out var connection))
            {
                if (await IsConnectionValidAsync(connection))
                {
                    connectionsToKeep.Add(connection);
                }
                else
                {
                    connectionsToRemove.Add(connection);
                }
            }

            // Dispose invalid connections
            foreach (var connection in connectionsToRemove)
            {
                await SafeDisposeConnection(connection);
                Interlocked.Decrement(ref _activeConnections);
            }

            // Return valid connections to pool
            foreach (var connection in connectionsToKeep)
            {
                _availableConnections.Enqueue(connection);
            }

            _logger.LogDebug("Pool maintenance completed. Removed {RemovedCount} invalid connections. Active: {ActiveConnections}",
                connectionsToRemove.Count, _activeConnections);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error during connection pool maintenance");
        }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        _maintenanceTimer?.Dispose();

        // Dispose all connections
        while (_availableConnections.TryDequeue(out var connection))
        {
            SafeDisposeConnection(connection).GetAwaiter().GetResult();
        }

        _connectionSemaphore?.Dispose();
        _logger.LogInformation("Database connection pool disposed");
    }
}