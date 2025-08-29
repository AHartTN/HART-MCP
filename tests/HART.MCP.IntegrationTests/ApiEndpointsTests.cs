using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using System.Net;
using System.Net.Http.Json;
using Xunit;

namespace HART.MCP.IntegrationTests;

public class ApiEndpointsTests : IClassFixture<WebApplicationFactory<HART.MCP.API.Program>>
{
    private readonly WebApplicationFactory<HART.MCP.API.Program> _factory;
    private readonly HttpClient _client;

    public ApiEndpointsTests(WebApplicationFactory<HART.MCP.API.Program> factory)
    {
        _factory = factory;
        _client = _factory.CreateClient();
    }

    [Fact]
    public async Task GetRoot_ReturnsSuccessAndCorrectContentType()
    {
        // Act
        var response = await _client.GetAsync("/");

        // Assert
        response.EnsureSuccessStatusCode();
        Assert.Equal("application/json; charset=utf-8", 
            response.Content.Headers.ContentType?.ToString());
        
        var content = await response.Content.ReadAsStringAsync();
        Assert.Contains("HART-MCP Multi-Agent Control Plane API", content);
    }

    [Fact]
    public async Task GetHealth_ReturnsHealthy()
    {
        // Act
        var response = await _client.GetAsync("/health");

        // Assert
        response.EnsureSuccessStatusCode();
        var content = await response.Content.ReadAsStringAsync();
        Assert.Contains("Healthy", content);
    }

    [Fact]
    public async Task GetApiInfo_ReturnsEndpointsList()
    {
        // Act
        var response = await _client.GetAsync("/api");

        // Assert
        response.EnsureSuccessStatusCode();
        var content = await response.Content.ReadAsStringAsync();
        Assert.Contains("endpoints", content);
    }

    [Fact]
    public async Task GetMcpTest_ReturnsSuccess()
    {
        // Act
        var response = await _client.GetAsync("/api/mcp/test");

        // Assert
        response.EnsureSuccessStatusCode();
        var content = await response.Content.ReadAsStringAsync();
        Assert.Contains("SUCCESS", content);
    }

    [Fact]
    public async Task PostMcp_CreatesMission()
    {
        // Arrange
        var request = new { query = "Test mission", agentId = 1 };

        // Act
        var response = await _client.PostAsJsonAsync("/api/mcp", request);

        // Assert
        response.EnsureSuccessStatusCode();
        var content = await response.Content.ReadAsStringAsync();
        Assert.Contains("mission_id", content);
    }

    [Fact]
    public async Task PostRagQuery_ReturnsValidResponse()
    {
        // Arrange
        var request = new { query = "Test query" };

        // Act
        var response = await _client.PostAsJsonAsync("/api/rag/query", request);

        // Assert
        response.EnsureSuccessStatusCode();
        var content = await response.Content.ReadAsStringAsync();
        Assert.Contains("answer", content.ToLower());
    }

    [Fact] 
    public async Task PostIngestDocument_AcceptsDocument()
    {
        // Arrange
        var request = new 
        { 
            content = "This is test content for ingestion",
            title = "Test Document",
            contentType = "text/plain"
        };

        // Act
        var response = await _client.PostAsJsonAsync("/api/ingest/document", request);

        // Assert - Should either succeed or return meaningful error
        Assert.True(response.StatusCode == HttpStatusCode.OK || 
                   response.StatusCode == HttpStatusCode.ServiceUnavailable);
    }

    [Fact]
    public async Task GetDocuments_ReturnsDocumentsList()
    {
        // Act
        var response = await _client.GetAsync("/api/documents");

        // Assert - Should either succeed or return meaningful error
        Assert.True(response.StatusCode == HttpStatusCode.OK || 
                   response.StatusCode == HttpStatusCode.ServiceUnavailable);
    }

    [Theory]
    [InlineData("/health/ready")]
    [InlineData("/health/live")]
    public async Task HealthEndpoints_ReturnSuccess(string endpoint)
    {
        // Act
        var response = await _client.GetAsync(endpoint);

        // Assert
        response.EnsureSuccessStatusCode();
    }

    [Fact]
    public async Task InvalidEndpoint_Returns404()
    {
        // Act
        var response = await _client.GetAsync("/api/nonexistent");

        // Assert
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }
}