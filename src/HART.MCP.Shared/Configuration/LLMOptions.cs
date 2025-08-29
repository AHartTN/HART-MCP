using System.ComponentModel.DataAnnotations;

namespace HART.MCP.Shared.Configuration;

public class LLMOptions
{
    public const string SectionName = "LLM";

    [Required]
    public string Provider { get; set; } = "openai";
    
    [Required]
    public string ApiKey { get; set; } = string.Empty;
    
    public string? BaseUrl { get; set; }
    
    public string DefaultModel { get; set; } = "gpt-3.5-turbo";
    
    public double DefaultTemperature { get; set; } = 0.7;
    
    public int DefaultMaxTokens { get; set; } = 2048;
    
    public int TimeoutSeconds { get; set; } = 60;
    
    public int MaxRetries { get; set; } = 3;
    
    public Dictionary<string, string> ModelMappings { get; set; } = new();
    
    public Dictionary<string, object> ProviderSpecificSettings { get; set; } = new();
}