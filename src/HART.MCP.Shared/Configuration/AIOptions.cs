namespace HART.MCP.Shared.Configuration;

public class AIOptions
{
    public const string SectionName = "AI";

    public string EmbeddingModel { get; set; } = "text-embedding-ada-002";
    
    public int EmbeddingDimensions { get; set; } = 1536;
    
    public int ChunkSize { get; set; } = 1000;
    
    public int ChunkOverlap { get; set; } = 200;
    
    public int MaxRetrievedChunks { get; set; } = 10;
    
    public double SimilarityThreshold { get; set; } = 0.7;
    
    public bool EnableTreeOfThought { get; set; } = true;
    
    public int TreeOfThoughtDepth { get; set; } = 3;
    
    public int TreeOfThoughtBranches { get; set; } = 3;
    
    public Dictionary<string, object> CustomSettings { get; set; } = new();
}