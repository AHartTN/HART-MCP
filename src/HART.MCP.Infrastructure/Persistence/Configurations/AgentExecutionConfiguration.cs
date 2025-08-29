using HART.MCP.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace HART.MCP.Infrastructure.Persistence.Configurations;

public class AgentExecutionConfiguration : IEntityTypeConfiguration<AgentExecution>
{
    public void Configure(EntityTypeBuilder<AgentExecution> builder)
    {
        builder.ToTable("AgentExecutions");
        
        builder.HasKey(e => e.Id);
        builder.Property(e => e.Id).ValueGeneratedNever();
        
        builder.Property(e => e.AgentId)
            .IsRequired();
            
        builder.Property(e => e.Query)
            .IsRequired()
            .HasMaxLength(2000);
            
        builder.Property(e => e.Response)
            .HasMaxLength(8000);
            
        builder.Property(e => e.Status)
            .IsRequired()
            .HasConversion<int>();
            
        builder.Property(e => e.ErrorMessage)
            .HasMaxLength(2000);
            
        builder.Property(e => e.TreeOfThoughtData)
            .HasMaxLength(4000);
            
        builder.HasOne(e => e.Agent)
            .WithMany(a => a.Executions)
            .HasForeignKey(e => e.AgentId)
            .OnDelete(DeleteBehavior.Cascade);
            
        builder.HasIndex(e => e.AgentId);
        builder.HasIndex(e => e.Status);
        builder.HasIndex(e => e.CreatedAt);
        builder.HasIndex(e => e.StartTime);
        builder.HasIndex(e => e.EndTime);
    }
}