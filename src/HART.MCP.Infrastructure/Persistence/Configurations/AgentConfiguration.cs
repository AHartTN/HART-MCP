using HART.MCP.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace HART.MCP.Infrastructure.Persistence.Configurations;

public class AgentConfiguration : IEntityTypeConfiguration<Agent>
{
    public void Configure(EntityTypeBuilder<Agent> builder)
    {
        builder.ToTable("Agents");
        
        builder.HasKey(a => a.Id);
        builder.Property(a => a.Id).ValueGeneratedNever();
        
        builder.Property(a => a.Name)
            .IsRequired()
            .HasMaxLength(200);
            
        builder.Property(a => a.Type)
            .IsRequired()
            .HasConversion<int>();
            
        builder.Property(a => a.Description)
            .HasMaxLength(1000);
            
        builder.Property(a => a.SystemPrompt)
            .HasMaxLength(4000);
            
        builder.Property(a => a.Status)
            .IsRequired()
            .HasConversion<int>();
            
        // Configure the AgentConfiguration owned entity
        builder.OwnsOne(a => a.Configuration, config =>
        {
            config.Property(c => c.ModelName).HasMaxLength(100);
            config.Property(c => c.Temperature);
            config.Property(c => c.MaxTokens);
            config.Property(c => c.TimeoutSeconds);
            config.Property(c => c.EnableMemory);
            config.Property(c => c.EnableToolUse);
            config.Property(c => c.CustomSettings)
                .HasConversion(
                    v => System.Text.Json.JsonSerializer.Serialize(v, (System.Text.Json.JsonSerializerOptions?)null),
                    v => System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(v, (System.Text.Json.JsonSerializerOptions?)null) ?? new())
                .HasMaxLength(2000);
        });
            
        // Configure the AgentCapabilities owned entity
        builder.OwnsOne(a => a.Capabilities, caps =>
        {
            caps.Property(c => c.CanProcessDocuments);
            caps.Property(c => c.CanPerformRAG);
            caps.Property(c => c.CanUseTreeOfThought);
            caps.Property(c => c.CanDelegateToOthers);
            caps.Property(c => c.CanAccessExternalAPIs);
            
            caps.Property(c => c.SupportedFileTypes)
                .HasConversion(
                    v => string.Join(',', v),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList())
                .HasMaxLength(1000);
                
            caps.Property(c => c.SupportedLanguages)
                .HasConversion(
                    v => string.Join(',', v),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList())
                .HasMaxLength(500);
                
            caps.Property(c => c.AvailableTools)
                .HasConversion(
                    v => string.Join(',', v),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList())
                .HasMaxLength(2000);
                
            caps.Property(c => c.CustomCapabilities)
                .HasConversion(
                    v => System.Text.Json.JsonSerializer.Serialize(v, (System.Text.Json.JsonSerializerOptions?)null),
                    v => System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(v, (System.Text.Json.JsonSerializerOptions?)null) ?? new())
                .HasMaxLength(4000);
        });
        
        builder.HasMany(a => a.Executions)
            .WithOne(e => e.Agent)
            .HasForeignKey(e => e.AgentId)
            .OnDelete(DeleteBehavior.Cascade);
            
        builder.HasIndex(a => a.Name).IsUnique();
        builder.HasIndex(a => a.Type);
        builder.HasIndex(a => a.Status);
        builder.HasIndex(a => a.CreatedAt);
    }
}