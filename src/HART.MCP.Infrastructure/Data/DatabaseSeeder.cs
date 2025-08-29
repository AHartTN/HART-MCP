using HART.MCP.Domain.Entities;
using HART.MCP.Domain.ValueObjects;
using HART.MCP.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

namespace HART.MCP.Infrastructure.Data;

public class DatabaseSeeder
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<DatabaseSeeder> _logger;

    public DatabaseSeeder(ApplicationDbContext context, ILogger<DatabaseSeeder> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task SeedAsync()
    {
        try
        {
            await _context.Database.EnsureCreatedAsync();
            
            // Check if data already exists
            var existingAgents = await _context.Agents.CountAsync();
            if (existingAgents > 0)
            {
                _logger.LogInformation("Database already seeded with {AgentCount} agents", existingAgents);
                return;
            }

            _logger.LogInformation("Seeding database with initial data...");

            // Create sample agents
            var orchestratorAgent = new Agent(
                "Master Orchestrator",
                "Primary orchestrator agent that coordinates specialist agents",
                AgentType.Orchestrator);
            orchestratorAgent.Activate();
            orchestratorAgent.SetSystemPrompt("You are the Master Orchestrator. Your job is to break down complex tasks and delegate to specialist agents. Always use DelegateToSpecialistTool for complex tasks and FinishTool when complete.");

            var ragAgent = new Agent(
                "RAG Specialist",
                "Specialist agent for Retrieval-Augmented Generation tasks",
                AgentType.RAG);
            ragAgent.Activate();
            ragAgent.SetSystemPrompt("You are a RAG specialist. Use your knowledge and retrieved documents to provide accurate, contextual answers. Always cite your sources.");

            var researchAgent = new Agent(
                "Research Specialist",
                "Specialist agent for research and information gathering tasks",
                AgentType.Specialist);
            researchAgent.Activate();
            researchAgent.SetSystemPrompt("You are a research specialist. Gather information, analyze data, and provide comprehensive research summaries.");

            _context.Agents.AddRange(orchestratorAgent, ragAgent, researchAgent);

            // Create sample documents
            var doc1Content = "# HART-MCP Documentation\n\nHART-MCP is a Multi-Agent Control Plane with RAG capabilities. It supports orchestrator and specialist agents working together to solve complex problems.";
            var sampleDoc1 = new Document(
                "Getting Started with HART-MCP",
                doc1Content,
                "hart-mcp-guide.md",
                DocumentType.Text,
                doc1Content.Length,
                "text/markdown",
                "hash1234");
            
            sampleDoc1.MarkAsProcessed();
            var chunk1 = new DocumentChunk(sampleDoc1.Id, "HART-MCP is a Multi-Agent Control Plane with RAG capabilities. It supports orchestrator and specialist agents.", 0, 0, 120);
            sampleDoc1.AddChunk(chunk1);
            
            var doc2Content = "# Agent Architecture\n\nThe HART-MCP system uses a hierarchical agent architecture with orchestrators delegating tasks to specialists. Each agent has specific capabilities and roles.";
            var sampleDoc2 = new Document(
                "Agent Architecture Overview",
                doc2Content,
                "agent-architecture.md", 
                DocumentType.Text,
                doc2Content.Length,
                "text/markdown",
                "hash5678");
                
            sampleDoc2.MarkAsProcessed();
            var chunk2 = new DocumentChunk(sampleDoc2.Id, "The HART-MCP system uses a hierarchical agent architecture with orchestrators and specialists.", 0, 0, 108);
            sampleDoc2.AddChunk(chunk2);

            _context.Documents.AddRange(sampleDoc1, sampleDoc2);

            await _context.SaveChangesAsync();

            _logger.LogInformation("Database seeded successfully with {AgentCount} agents and {DocumentCount} documents", 
                3, 2);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error seeding database");
            throw;
        }
    }
}