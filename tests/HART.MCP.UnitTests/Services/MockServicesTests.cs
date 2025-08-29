using HART.MCP.Application.Services;
using HART.MCP.AI.Services;
using HART.MCP.Application.Tools;
using Xunit;
using Microsoft.Extensions.Logging;
using Moq;

namespace HART.MCP.UnitTests.Services;

public class MockServicesTests
{
    [Fact]
    public async Task MockLlmService_GeneratesResponse()
    {
        // Arrange
        var mockLogger = new Mock<ILogger<HART.MCP.Application.Services.LlmService>>();
        var service = new HART.MCP.Application.Services.LlmService(mockLogger.Object);
        var messages = new List<Dictionary<string, string>>
        {
            new() { ["role"] = "user", ["content"] = "Hello" }
        };

        // Act
        var result = await service.GenerateResponseAsync(messages);

        // Assert
        Assert.NotNull(result);
        Assert.NotEmpty(result);
    }

    [Fact]
    public async Task ProjectStateService_StoresAndRetrievesData()
    {
        // Arrange
        var mockLogger = new Mock<ILogger<ProjectStateService>>();
        var service = new ProjectStateService(mockLogger.Object);
        var testKey = "test_key";
        var testValue = "test_value";

        // Act
        await service.SetAsync(testKey, testValue);
        var result = await service.GetAsync<string>(testKey);

        // Assert
        Assert.Equal(testValue, result);
    }

    [Fact]
    public void ToolRegistry_RegistersAndRetrievesTools()
    {
        // Arrange
        var registry = new ToolRegistry();
        var testTool = new TestTool();

        // Act
        registry.RegisterTool(testTool);
        var retrievedTool = registry.GetTool("TestTool");
        var allTools = registry.GetAvailableTools();

        // Assert
        Assert.NotNull(retrievedTool);
        Assert.Equal("TestTool", retrievedTool.Name);
        Assert.Single(allTools);
    }

    [Fact]
    public async Task FinishTool_ExecutesWithResult()
    {
        // Arrange
        var tool = new FinishTool();
        var parameters = new Dictionary<string, object>
        {
            ["result"] = "Task completed successfully"
        };

        // Act
        var result = await tool.ExecuteAsync(parameters);

        // Assert
        Assert.NotNull(result);
        Assert.Contains("Task completed successfully", result);
    }

    [Fact]
    public async Task RAGService_ReturnsBasicResponse()
    {
        // Arrange
        var mockEmbeddingLogger = new Mock<ILogger<HART.MCP.AI.Services.EmbeddingService>>();
        var mockRagLogger = new Mock<ILogger<RAGService>>();
        var mockLlmLogger = new Mock<ILogger<HART.MCP.Application.Services.LlmService>>();
        
        var embeddingService = new HART.MCP.AI.Services.EmbeddingService(mockEmbeddingLogger.Object);
        var llmService = new HART.MCP.Application.Services.LlmService(mockLlmLogger.Object);
        var service = new RAGService(embeddingService, llmService, mockRagLogger.Object);
        var request = new HART.MCP.AI.Abstractions.RAGRequest("Test query");

        // Act
        var response = await service.QueryAsync(request);

        // Assert
        Assert.NotNull(response);
        Assert.NotNull(response.Answer);
        Assert.NotNull(response.RetrievedChunks);
        Assert.NotNull(response.Metadata);
    }
}