using HART.MCP.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace HART.MCP.Infrastructure.Persistence.Configurations;

public class DocumentChunkConfiguration : IEntityTypeConfiguration<DocumentChunk>
{
    public void Configure(EntityTypeBuilder<DocumentChunk> builder)
    {
        builder.ToTable("DocumentChunks");
        
        builder.HasKey(c => c.Id);
        builder.Property(c => c.Id).ValueGeneratedNever();
        
        builder.Property(c => c.DocumentId)
            .IsRequired();
            
        builder.Property(c => c.Content)
            .IsRequired()
            .HasMaxLength(4000);
            
        builder.Property(c => c.ChunkIndex)
            .IsRequired();
            
        builder.Property(c => c.StartPosition)
            .IsRequired();
            
        builder.Property(c => c.EndPosition)
            .IsRequired();
            
        builder.Property(c => c.EmbeddingModel)
            .HasMaxLength(50);
            
        builder.Property(c => c.Embedding)
            .HasConversion(
                v => string.Join(',', v.Select(f => f.ToString("F6"))),
                v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).Select(float.Parse).ToArray());
            
        builder.HasOne(c => c.Document)
            .WithMany(d => d.Chunks)
            .HasForeignKey(c => c.DocumentId)
            .OnDelete(DeleteBehavior.Cascade);
            
        builder.HasIndex(c => c.DocumentId);
        builder.HasIndex(c => c.ChunkIndex);
        builder.HasIndex(c => c.EmbeddingModel);
        builder.HasIndex(c => c.CreatedAt);
    }
}