using HART.MCP.Domain.Entities;
using System.Data.SqlClient;

namespace HART.MCP.Infrastructure.SqlClr;

/// <summary>
/// Enterprise service interface for SQL CLR Quantum Model operations
/// Provides async, resilient, and observable access to quantum model functionality
/// </summary>
public interface IQuantumModelService
{
    /// <summary>
    /// Asynchronously load a quantum model with proper error handling and metrics
    /// </summary>
    Task<QuantumModelLoadResult> LoadModelAsync(
        string modelPath, 
        string modelName, 
        long parameterCount,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Perform quantum inference with observability and resilience
    /// </summary>
    Task<QuantumInferenceResult> InferAsync(
        string modelName,
        string prompt,
        double temperature = 0.7,
        int maxTokens = 2048,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Stream model parameters with proper async enumeration
    /// </summary>
    IAsyncEnumerable<ModelParameter> StreamParametersAsync(
        string modelName,
        long startIndex = 0,
        long count = 1000,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Perform model surgery operations with audit logging
    /// </summary>
    Task<ModelSurgeryResult> PerformModelSurgeryAsync(
        string modelName,
        string layerName,
        byte[] newWeights,
        ModelSurgeryOperation operation,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Get real-time model health and performance metrics
    /// </summary>
    Task<ModelHealthMetrics> GetModelHealthAsync(
        string modelName,
        CancellationToken cancellationToken = default);
}

public record QuantumModelLoadResult(
    string ModelName,
    long ParameterCount,
    long MemoryFootprintBytes,
    string Status,
    string[] Capabilities,
    TimeSpan LoadTime,
    string? ErrorMessage = null);

public record QuantumInferenceResult(
    string Content,
    double[] QuantumStates,
    TimeSpan InferenceTime,
    int TokensGenerated,
    double CoherenceScore,
    string[] ActiveQuantumDimensions);

public record ModelParameter(
    long Index,
    string LayerName,
    float Value,
    float Gradient,
    double Significance,
    string QuantumState);

public record ModelSurgeryResult(
    bool Success,
    string Operation,
    string LayerName,
    TimeSpan SurgeryTime,
    string? ErrorMessage = null);

public record ModelHealthMetrics(
    string ModelName,
    double MemoryUsageMB,
    double CpuUtilizationPercent,
    long InferenceCount,
    TimeSpan AverageInferenceTime,
    double QuantumCoherenceScore,
    DateTime LastAccessed);

public enum ModelSurgeryOperation
{
    Replace,
    Merge,
    Evolve,
    QuantumEntangle
}