# HART-MCP Production Deployment Guide

## Overview

This guide covers the complete production deployment of the HART-MCP system, including infrastructure setup, security configuration, monitoring, and maintenance procedures.

## Prerequisites

### Azure Resources Required

1. **Azure Key Vault** - For secrets management
2. **Azure Container Registry** (optional) - For container images
3. **Azure Application Insights** - For monitoring and telemetry
4. **Azure SQL Database** or **SQL Server** - Primary database
5. **Azure Container Instances** or **Azure App Service** - Application hosting

### Local Development Tools

- .NET 8.0 SDK
- Docker Desktop
- PowerShell 7.0+
- SQL Server Management Studio (optional)
- Azure CLI

## Security Configuration

### 1. Azure Key Vault Setup

```bash
# Create Key Vault
az keyvault create --name "hart-mcp-key-vault" \
                   --resource-group "HART-MCP" \
                   --location "East US"

# Add application secrets
az keyvault secret set --vault-name "hart-mcp-key-vault" \
                       --name "SqlServerConnectionString" \
                       --value "Data Source=server;Initial Catalog=HART_MCP;..."

az keyvault secret set --vault-name "hart-mcp-key-vault" \
                       --name "GeminiApiKey" \
                       --value "your-gemini-api-key"

# Grant application access
az keyvault set-policy --name "hart-mcp-key-vault" \
                       --object-id "your-app-service-principal-id" \
                       --secret-permissions get list
```

### 2. Environment Variables

**Production Environment Variables:**

```bash
ASPNETCORE_ENVIRONMENT=Production
AZURE_KEYVAULT_URL=https://hart-mcp-key-vault.vault.azure.net/
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret  # Store in Key Vault
AZURE_TENANT_ID=your-tenant-id
ApplicationInsights__ConnectionString=your-app-insights-connection-string
```

**Development Environment (.env file):**
- Keep your existing `.env` file for local development
- Never commit production credentials to source control
- Use Azure CLI for production secret management

### 3. Database Security

```sql
-- Create dedicated application user
CREATE LOGIN [HART_MCP_APP] WITH PASSWORD = 'SecurePassword123!';
CREATE USER [HART_MCP_APP] FOR LOGIN [HART_MCP_APP];

-- Grant minimal required permissions
ALTER ROLE db_datareader ADD MEMBER [HART_MCP_APP];
ALTER ROLE db_datawriter ADD MEMBER [HART_MCP_APP];
GRANT EXECUTE ON SCHEMA::dbo TO [HART_MCP_APP];
```

## Infrastructure Deployment

### Option 1: Azure Container Instances (Recommended for start)

```bash
# Build and push image
docker build -f deployment/Dockerfile.csharp -t hart-mcp:latest .
docker tag hart-mcp:latest your-registry.azurecr.io/hart-mcp:latest
docker push your-registry.azurecr.io/hart-mcp:latest

# Deploy to ACI
az container create \
    --resource-group HART-MCP \
    --name hart-mcp-production \
    --image your-registry.azurecr.io/hart-mcp:latest \
    --cpu 2 \
    --memory 4 \
    --registry-login-server your-registry.azurecr.io \
    --registry-username your-username \
    --registry-password your-password \
    --environment-variables \
        ASPNETCORE_ENVIRONMENT=Production \
        AZURE_KEYVAULT_URL=https://hart-mcp-key-vault.vault.azure.net/ \
    --secure-environment-variables \
        AZURE_CLIENT_ID=your-client-id \
        AZURE_CLIENT_SECRET=your-client-secret \
        AZURE_TENANT_ID=your-tenant-id \
    --ports 8080 \
    --dns-name-label hart-mcp-prod
```

### Option 2: Azure App Service

```bash
# Create App Service Plan
az appservice plan create \
    --name hart-mcp-plan \
    --resource-group HART-MCP \
    --sku P1V2 \
    --is-linux

# Create Web App
az webapp create \
    --resource-group HART-MCP \
    --plan hart-mcp-plan \
    --name hart-mcp-prod \
    --deployment-container-image-name your-registry.azurecr.io/hart-mcp:latest

# Configure application settings
az webapp config appsettings set \
    --resource-group HART-MCP \
    --name hart-mcp-prod \
    --settings AZURE_KEYVAULT_URL=https://hart-mcp-key-vault.vault.azure.net/
```

### Option 3: Docker Compose (Self-hosted)

```yaml
# Use deployment/docker-compose.csharp.yml
docker-compose -f deployment/docker-compose.csharp.yml up -d
```

## Database Migration

### Automated Migration (Production)

```powershell
# Run migration script
.\database\migrations\migrate.ps1 -ConnectionString "Data Source=prod-server;Initial Catalog=HART_MCP;User ID=migration_user;Password=secure_password"

# Verify migration
.\database\migrations\migrate.ps1 -ConnectionString "..." -DryRun
```

### Manual Migration Steps

1. **Backup existing database**
2. **Run migration script**
3. **Verify schema changes**
4. **Test application connectivity**

## CI/CD Pipeline Setup

### GitHub Actions Secrets

Configure the following secrets in your GitHub repository:

```
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET  
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP
AZURE_KEYVAULT_URL
GITHUB_TOKEN (automatically provided)
```

### Pipeline Features

- **Automated testing** with SQL Server container
- **Security scanning** with CodeQL
- **Docker image building** and pushing to registry
- **Automated deployment** to staging/production
- **Database migrations** on deployment
- **Health checks** post-deployment

## Monitoring and Logging

### Application Insights Configuration

```csharp
// Configured automatically via ApplicationInsightsConfiguration.cs
// Key metrics tracked:
// - Request duration and success rate
// - Dependency calls (SQL, Neo4j, Milvus)
// - Custom business metrics
// - Exception tracking
// - Performance counters
```

### Log Aggregation

**Structured Logging with Serilog:**
- Console output for containers
- File logging with rotation
- Application Insights integration
- Contextual enrichment (environment, process, thread)

### Health Checks

Available endpoints:
- `/health` - Basic health check
- `/health/ready` - Readiness probe  
- `/health/live` - Liveness probe

### Alerting Rules

**Set up Azure Monitor alerts for:**
- High error rate (> 5% in 5 minutes)
- High response time (> 2s average)
- Database connection failures
- Memory usage > 80%
- CPU usage > 85%

## Performance Optimization

### Database Optimization

```sql
-- Index maintenance
ALTER INDEX ALL ON Documents REORGANIZE;
ALTER INDEX ALL ON Embeddings REBUILD;

-- Update statistics
UPDATE STATISTICS Documents;
UPDATE STATISTICS Embeddings;
```

### Application Performance

1. **Connection Pooling** - Configured in appsettings.json
2. **Caching** - Redis for distributed caching (optional)
3. **Rate Limiting** - Configured per endpoint
4. **Compression** - Gzip enabled for responses

## Backup and Recovery

### Database Backup

```sql
-- Full backup
BACKUP DATABASE [HART_MCP] 
TO DISK = 'C:\Backups\HART_MCP_Full.bak'
WITH FORMAT, INIT, SKIP, NOREWIND, NOUNLOAD, STATS = 10;

-- Differential backup (daily)
BACKUP DATABASE [HART_MCP] 
TO DISK = 'C:\Backups\HART_MCP_Diff.bak'
WITH DIFFERENTIAL, FORMAT, INIT, SKIP, NOREWIND, NOUNLOAD, STATS = 10;
```

### Application State

- **Vector embeddings** - Stored in Milvus (backup via Milvus tools)
- **Knowledge graph** - Stored in Neo4j (backup via Neo4j Admin)
- **Application logs** - Retained for 30 days, archived to blob storage

## Troubleshooting

### Common Issues

1. **Key Vault Access Denied**
   - Check service principal permissions
   - Verify AZURE_CLIENT_ID/SECRET/TENANT_ID
   - Ensure Key Vault URL is correct

2. **Database Connection Issues**  
   - Check connection string format
   - Verify firewall rules
   - Test SQL Server connectivity

3. **Container Startup Failures**
   - Check environment variables
   - Review application logs
   - Verify image build process

### Diagnostic Commands

```bash
# Check container logs
docker logs hart-mcp-production

# Test health endpoint
curl https://your-app-url/health

# Check Azure resource status
az resource list --resource-group HART-MCP --output table
```

### Log Analysis Queries

```kusto
// Application Insights - Error tracking
exceptions
| where timestamp > ago(1h)
| summarize count() by type, outerMessage
| order by count_ desc

// Performance monitoring  
requests
| where timestamp > ago(1h)
| summarize avg(duration), percentile(duration, 95) by name
| order by avg_duration desc
```

## Maintenance Procedures

### Regular Maintenance

**Daily:**
- Monitor health endpoints
- Check error logs
- Verify backup completion

**Weekly:**
- Review performance metrics
- Update dependencies (security patches)
- Clean old log files

**Monthly:**
- Database maintenance (index optimization)
- Security vulnerability scanning
- Capacity planning review

### Update Process

1. **Test in staging environment**
2. **Schedule maintenance window**
3. **Deploy with zero-downtime strategy**
4. **Monitor post-deployment metrics**
5. **Rollback plan if issues detected**

## Security Checklist

- [ ] All secrets stored in Azure Key Vault
- [ ] HTTPS enforced in production
- [ ] Database access restricted to application user
- [ ] Container running as non-root user
- [ ] Network security groups configured
- [ ] Audit logging enabled
- [ ] Regular security scanning
- [ ] Dependency vulnerability monitoring

## Support and Escalation

### Monitoring Thresholds

- **P1 (Critical)**: Application down, data loss
- **P2 (High)**: Performance degradation, partial functionality loss  
- **P3 (Medium)**: Minor issues, workarounds available
- **P4 (Low)**: Enhancement requests, documentation updates

### Contact Information

- **On-call Engineer**: [Your contact]
- **Database Administrator**: [DBA contact]
- **Azure Support**: [Support plan details]

---

## Quick Reference

### Essential URLs
- Production App: `https://hart-mcp-prod.azurecontainer.io`
- Health Check: `https://hart-mcp-prod.azurecontainer.io/health`
- Application Insights: [Azure Portal Link]
- Key Vault: [Azure Portal Link]

### Key Commands
```bash
# Check application status
az container show --resource-group HART-MCP --name hart-mcp-production

# View logs
az container logs --resource-group HART-MCP --name hart-mcp-production

# Restart application  
az container restart --resource-group HART-MCP --name hart-mcp-production
```