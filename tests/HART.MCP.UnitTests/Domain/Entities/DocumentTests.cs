using AutoFixture.Xunit2;
using FluentAssertions;
using HART.MCP.Domain.Entities;
using Xunit;

namespace HART.MCP.UnitTests.Domain.Entities;

public class DocumentTests
{
    [Theory]
    [AutoData]
    public void Create_ValidDocument_ShouldSucceed(
        string title, 
        string content, 
        string fileName, 
        long sizeBytes, 
        string mimeType, 
        string hash)
    {
        // Act
        var document = new Document(title, content, fileName, DocumentType.Text, sizeBytes, mimeType, hash);

        // Assert
        document.Should().NotBeNull();
        document.Title.Should().Be(title);
        document.Content.Should().Be(content);
        document.OriginalFileName.Should().Be(fileName);
        document.Type.Should().Be(DocumentType.Text);
        document.SizeBytes.Should().Be(sizeBytes);
        document.MimeType.Should().Be(mimeType);
        document.Hash.Should().Be(hash);
        document.Status.Should().Be(DocumentStatus.Pending);
        document.Id.Should().NotBeEmpty();
        document.CreatedAt.Should().BeCloseTo(DateTime.UtcNow, TimeSpan.FromSeconds(1));
    }

    [Fact]
    public void Create_WithNullTitle_ShouldThrowArgumentException()
    {
        // Act & Assert
        var act = () => new Document(null!, "content", "file.txt", DocumentType.Text, 100, "text/plain", "hash");
        act.Should().Throw<ArgumentException>().WithParameterName("title");
    }

    [Theory]
    [AutoData]
    public void MarkAsProcessed_ShouldUpdateStatusAndTime(string title, string content, string fileName, string mimeType, string hash)
    {
        // Arrange
        var document = new Document(title, content, fileName, DocumentType.Text, 100, mimeType, hash);
        var beforeProcessed = DateTime.UtcNow;

        // Act
        document.MarkAsProcessed();

        // Assert
        document.Status.Should().Be(DocumentStatus.Processed);
        document.ProcessedAt.Should().NotBeNull();
        document.ProcessedAt.Should().BeOnOrAfter(beforeProcessed);
        document.ProcessingError.Should().BeNull();
    }

    [Theory]
    [AutoData]
    public void MarkAsProcessingFailed_ShouldUpdateStatusAndError(string title, string content, string fileName, string mimeType, string hash, string error)
    {
        // Arrange
        var document = new Document(title, content, fileName, DocumentType.Text, 100, mimeType, hash);

        // Act
        document.MarkAsProcessingFailed(error);

        // Assert
        document.Status.Should().Be(DocumentStatus.Failed);
        document.ProcessingError.Should().Be(error);
    }

    [Theory]
    [AutoData]
    public void AddChunk_ValidChunk_ShouldAddToCollection(string title, string content, string fileName, string mimeType, string hash)
    {
        // Arrange
        var document = new Document(title, content, fileName, DocumentType.Text, 100, mimeType, hash);
        var chunk = new DocumentChunk(document.Id, "chunk content", 0, 0, 13);

        // Act
        document.AddChunk(chunk);

        // Assert
        document.Chunks.Should().HaveCount(1);
        document.Chunks.First().Should().Be(chunk);
    }
}