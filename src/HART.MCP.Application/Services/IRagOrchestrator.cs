namespace HART.MCP.Application.Services;

public interface IRagOrchestrator
{
    Task<string> GenerateResponseAsync(string query, Dictionary<string, object>? context = null, Func<Dictionary<string, object>, Task>? callback = null);
}

public interface IEmbeddingService
{
    Task<float[]> GenerateEmbeddingAsync(string text);
    Task<List<float[]>> GenerateEmbeddingsAsync(List<string> texts);
}

public interface ILlmService
{
    Task<string> GenerateResponseAsync(List<Dictionary<string, string>> messages);
    Task<string> GenerateResponseAsync(string prompt);
}

public interface IProjectStateService
{
    Task<T?> GetAsync<T>(string key);
    Task SetAsync<T>(string key, T value);
    Task<Dictionary<string, object>> GetAllAsync();
    Task ClearAsync();
}