using System.ComponentModel.DataAnnotations;

namespace HART.MCP.Shared.Configuration;

public class DatabaseOptions
{
    public const string SectionName = "Database";

    [Required]
    public string SqlServerConnectionString { get; set; } = string.Empty;
    
    [Required]
    public string MilvusHost { get; set; } = "localhost";
    
    public int MilvusPort { get; set; } = 19530;
    
    public string? MilvusUsername { get; set; }
    
    public string? MilvusPassword { get; set; }
    
    [Required]
    public string Neo4jUri { get; set; } = "bolt://localhost:7687";
    
    public string? Neo4jUsername { get; set; }
    
    public string? Neo4jPassword { get; set; }

    public int ConnectionTimeoutSeconds { get; set; } = 30;
    
    public int CommandTimeoutSeconds { get; set; } = 120;
    
    public bool EnableRetryOnFailure { get; set; } = true;
    
    public int MaxRetryCount { get; set; } = 3;
    
    public int MinPoolSize { get; set; } = 5;
    
    public int MaxPoolSize { get; set; } = 100;
}