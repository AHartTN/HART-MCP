#!/bin/bash

# HART-MCP Enterprise C# System Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"
ENTERPRISE_DIR="$PROJECT_ROOT/enterprise-csharp"

echo -e "${BLUE}🏢 HART-MCP Enterprise C# System Deployment${NC}"
echo "=============================================="

# Function to log messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v dotnet &> /dev/null; then
        warn ".NET SDK not found. Docker build will handle this, but local development won't work."
    else
        local dotnet_version=$(dotnet --version)
        log "✅ .NET SDK version: $dotnet_version"
    fi
    
    log "✅ Prerequisites check passed"
}

# Check .env file exists
check_env_file() {
    local env_file="$PROJECT_ROOT/.env"
    
    if [[ ! -f "$env_file" ]]; then
        error "Main .env file not found at $env_file"
        error "Please ensure your .env file exists in the project root"
        exit 1
    else
        log "✅ Using existing .env file with your database configurations"
    fi
}

# Fix package version issues
fix_package_versions() {
    log "Fixing C# package version issues..."
    
    # Update package versions in project files
    local api_project="$ENTERPRISE_DIR/src/HART.MCP.API/HART.MCP.API.csproj"
    local infra_project="$ENTERPRISE_DIR/src/HART.MCP.Infrastructure/HART.MCP.Infrastructure.csproj"
    
    if [[ -f "$api_project" ]]; then
        # Fix AspNetCore.RateLimiting version (doesn't exist in 8.0.1)
        sed -i 's/Microsoft\.AspNetCore\.RateLimiting" Version="8\.0\.1"/Microsoft.AspNetCore.RateLimiting" Version="7.0.14"/g' "$api_project" 2>/dev/null || true
        
        # Update vulnerable Microsoft.Extensions.Caching.Memory
        sed -i 's/Microsoft\.Extensions\.Caching\.Memory" Version="8\.0\.0"/Microsoft.Extensions.Caching.Memory" Version="8.0.1"/g' "$api_project" 2>/dev/null || true
    fi
    
    if [[ -f "$infra_project" ]]; then
        # Update vulnerable Microsoft.Extensions.Caching.Memory
        sed -i 's/Microsoft\.Extensions\.Caching\.Memory" Version="8\.0\.0"/Microsoft.Extensions.Caching.Memory" Version="8.0.1"/g' "$infra_project" 2>/dev/null || true
    fi
    
    log "✅ Package versions updated"
}

# Build C# solution
build_solution() {
    log "Building C# solution..."
    
    cd "$ENTERPRISE_DIR"
    
    # Clean and restore
    if command -v dotnet &> /dev/null; then
        log "Cleaning and restoring solution..."
        dotnet clean --verbosity minimal
        dotnet restore --verbosity minimal
        
        log "Building solution..."
        if dotnet build --configuration Release --verbosity minimal --no-restore; then
            log "✅ Solution built successfully"
        else
            warn "Solution build failed locally, but Docker build may still work"
        fi
    else
        log "Skipping local build - will build in Docker"
    fi
}

# Deploy database migrations
deploy_migrations() {
    log "Checking database migration requirements..."
    
    local migration_file="$PROJECT_ROOT/shared-resources/migrations/InitialCreate.sql"
    if [[ -f "$migration_file" ]]; then
        log "Database migration script found at: $migration_file"
        log "Please run the migration scripts manually on your SQL Server:"
        echo "  1. $migration_file"
        echo "  2. $PROJECT_ROOT/shared-resources/migrations/DeploySqlClr.sql"
        echo ""
        read -p "Have you run the database migrations? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warn "Database migrations are required for full functionality"
        fi
    fi
}

# Build and deploy C# system
deploy_csharp() {
    log "Starting Enterprise C# system deployment..."
    
    cd "$DEPLOYMENT_DIR"
    
    # Stop existing services
    log "Stopping existing services..."
    docker-compose -f docker-compose.csharp.yml --env-file .env.csharp down || true
    
    # Build and start services
    log "Building and starting Enterprise C# services..."
    docker-compose -f docker-compose.csharp.yml --env-file .env.csharp up -d --build
    
    log "✅ Enterprise C# system deployment started"
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to become healthy..."
    
    local max_attempts=60  # C# takes longer to start
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f http://localhost:8080/health &>/dev/null; then
            log "✅ C# API is healthy"
            break
        fi
        
        log "Attempt $attempt/$max_attempts - Waiting for C# API to start..."
        sleep 5
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        warn "C# API may not be fully healthy. Check logs with: docker-compose -f docker-compose.csharp.yml logs hart-csharp"
    fi
}

# Show deployment status
show_status() {
    log "Deployment status:"
    echo
    
    cd "$DEPLOYMENT_DIR"
    docker-compose -f docker-compose.csharp.yml --env-file .env.csharp ps
    
    echo
    log "Service URLs:"
    echo "  🏢 C# API: http://localhost:8080"
    echo "  📊 Swagger UI: http://localhost:8080/swagger"
    echo "  📈 Health Check: http://localhost:8080/health"
    echo "  📊 Detailed Health: http://localhost:8080/health/detailed"
    echo "  🗄️  SQL Server 2025: host.docker.internal:1433 (your standalone instance)"
    echo "  🔄 Redis: localhost:6379"
    echo "  🕸️  Neo4j Browser: http://localhost:7474"
    
    echo
    log "Health check:"
    if curl -f http://localhost:8080/health &>/dev/null; then
        log "✅ C# API is healthy"
        
        # Test a simple API endpoint
        if curl -f http://localhost:8080/api/system/info &>/dev/null; then
            log "✅ API endpoints are responding"
        fi
    else
        warn "❌ C# API health check failed"
    fi
}

# Show logs
show_logs() {
    if [[ "${1:-}" == "--logs" ]]; then
        log "Showing service logs (Press Ctrl+C to exit):"
        cd "$DEPLOYMENT_DIR"
        docker-compose -f docker-compose.csharp.yml --env-file .env.csharp logs -f
    fi
}

# Development mode (removed containerized SQL Server - using your standalone instance)
deploy_dev_mode() {
    log "Starting development mode using your standalone SQL Server 2025..."
    
    cd "$DEPLOYMENT_DIR"
    docker-compose -f docker-compose.csharp.yml --env-file .env.csharp up -d --build
    
    log "✅ Development environment started"
    log "Note: Connecting to your standalone SQL Server 2025 instance with SQL CLR support"
}

# Main deployment flow
main() {
    local mode="${1:-production}"
    
    log "Starting deployment process in $mode mode..."
    
    check_prerequisites
    create_env_file
    fix_package_versions
    build_solution
    
    if [[ "$mode" == "development" ]]; then
        deploy_dev_mode
    else
        deploy_migrations
        deploy_csharp
    fi
    
    wait_for_health
    show_status
    
    log "🎉 Enterprise C# system deployment completed!"
    echo
    echo "Next steps:"
    echo "1. Update .env.csharp with your actual API keys and credentials"
    echo "2. Test the API at http://localhost:8080/swagger"
    echo "3. Monitor logs with: ./deploy-csharp.sh --logs"
    echo "4. Run database migrations if not already done"
    echo
    
    show_logs "$2"
}

# Handle script arguments
case "${1:-}" in
    --logs)
        cd "$DEPLOYMENT_DIR"
        docker-compose -f docker-compose.csharp.yml --env-file .env.csharp logs -f
        ;;
    --stop)
        log "Stopping Enterprise C# system..."
        cd "$DEPLOYMENT_DIR"
        docker-compose -f docker-compose.csharp.yml --env-file .env.csharp down
        log "✅ Services stopped"
        ;;
    --status)
        cd "$DEPLOYMENT_DIR"
        docker-compose -f docker-compose.csharp.yml --env-file .env.csharp ps
        ;;
    --dev|development)
        main "development" "$2"
        ;;
    *)
        main "production" "$1"
        ;;
esac