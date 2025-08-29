using HART.MCP.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace HART.MCP.Infrastructure.Persistence.Configurations;

public class DocumentConfiguration : IEntityTypeConfiguration<Document>
{
    public void Configure(EntityTypeBuilder<Document> builder)
    {
        builder.ToTable("Documents");
        
        builder.HasKey(d => d.Id);
        builder.Property(d => d.Id).ValueGeneratedNever();
        
        builder.Property(d => d.Title)
            .IsRequired()
            .HasMaxLength(500);
            
        builder.Property(d => d.Content)
            .IsRequired();
            
        builder.Property(d => d.OriginalFileName)
            .IsRequired()
            .HasMaxLength(255);
            
        builder.Property(d => d.MimeType)
            .IsRequired()
            .HasMaxLength(100);
            
        builder.Property(d => d.Hash)
            .IsRequired()
            .HasMaxLength(64);
            
        builder.Property(d => d.Type)
            .IsRequired()
            .HasConversion<int>();
            
        builder.Property(d => d.Status)
            .IsRequired()
            .HasConversion<int>();
            
        builder.Property(d => d.ProcessingError)
            .HasMaxLength(2000);
            
        builder.OwnsOne(d => d.Metadata, meta =>
        {
            meta.Property(m => m.Author).HasMaxLength(255);
            meta.Property(m => m.Subject).HasMaxLength(500);
            meta.Property(m => m.Keywords).HasMaxLength(1000);
            meta.Property(m => m.Language).HasMaxLength(10);
            meta.Property(m => m.Source).HasMaxLength(255);
            meta.Property(m => m.CustomProperties)
                .HasConversion(
                    v => System.Text.Json.JsonSerializer.Serialize(v, (System.Text.Json.JsonSerializerOptions?)null),
                    v => System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(v, (System.Text.Json.JsonSerializerOptions?)null) ?? new());
        });
        
        builder.HasMany(d => d.Chunks)
            .WithOne(c => c.Document)
            .HasForeignKey(c => c.DocumentId)
            .OnDelete(DeleteBehavior.Cascade);
            
        builder.HasIndex(d => d.Hash).IsUnique();
        builder.HasIndex(d => d.Status);
        builder.HasIndex(d => d.Type);
        builder.HasIndex(d => d.CreatedAt);
    }
}