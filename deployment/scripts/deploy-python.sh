#!/bin/bash

# HART-MCP Python Legacy System Deployment Script
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
LEGACY_DIR="$PROJECT_ROOT/legacy-python"

echo -e "${BLUE}🐍 HART-MCP Python Legacy System Deployment${NC}"
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

# Copy Python Dockerfile to legacy directory
prepare_dockerfile() {
    log "Preparing Dockerfile for Python system..."
    
    if [[ ! -f "$LEGACY_DIR/Dockerfile.python" ]]; then
        cp "$DEPLOYMENT_DIR/Dockerfile.python" "$LEGACY_DIR/"
        log "✅ Dockerfile copied to legacy-python directory"
    else
        log "✅ Dockerfile.python already exists in legacy-python directory"
    fi
}

# Build and deploy Python system
deploy_python() {
    log "Starting Python legacy system deployment..."
    
    cd "$DEPLOYMENT_DIR"
    
    # Stop existing services
    log "Stopping existing services..."
    docker-compose -f docker-compose.python.yml down || true
    
    # Build and start services
    log "Building and starting Python legacy services..."
    docker-compose -f docker-compose.python.yml up -d --build
    
    log "✅ Python legacy system deployment started"
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to become healthy..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$DEPLOYMENT_DIR/docker-compose.python.yml" ps | grep -q "healthy\|Up"; then
            log "✅ Services are running"
            break
        fi
        
        log "Attempt $attempt/$max_attempts - Waiting for services..."
        sleep 10
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        warn "Services may not be fully healthy. Check with: docker-compose -f docker-compose.python.yml logs"
    fi
}

# Show deployment status
show_status() {
    log "Deployment status:"
    echo
    
    cd "$DEPLOYMENT_DIR"
    docker-compose -f docker-compose.python.yml ps
    
    echo
    log "Service URLs:"
    echo "  🐍 Python API: http://localhost:8000"
    echo "  📊 API Docs: http://localhost:8000/docs"
    echo "  🗄️  SQL Server 2025: ${SQL_SERVER_SERVER}:1433 (HART-MCP database)"
    echo "  🔍 Milvus: localhost:19530"
    echo "  🕸️  Neo4j Browser: http://localhost:7474"
    echo "  📦 MinIO Console: http://localhost:9001"
    
    echo
    log "Health check:"
    if curl -f http://localhost:8000/health &>/dev/null; then
        log "✅ Python API is healthy"
    else
        warn "❌ Python API health check failed"
    fi
}

# Show logs
show_logs() {
    if [[ "${1:-}" == "--logs" ]]; then
        log "Showing service logs (Press Ctrl+C to exit):"
        cd "$DEPLOYMENT_DIR"
        docker-compose -f docker-compose.python.yml logs -f
    fi
}

# Main deployment flow
main() {
    log "Starting deployment process..."
    
    check_prerequisites
    check_env_file
    prepare_dockerfile
    deploy_python
    wait_for_health
    show_status
    
    log "🎉 Python legacy system deployment completed!"
    echo
    echo "✅ Using your existing .env configuration"
    echo "Next steps:"
    echo "1. Test the API at http://localhost:8000/docs"
    echo "2. Monitor logs with: ./deploy-python.sh --logs"
    echo
    
    show_logs "$1"
}

# Handle script arguments
case "${1:-}" in
    --logs)
        cd "$DEPLOYMENT_DIR"
        docker-compose -f docker-compose.python.yml logs -f
        ;;
    --stop)
        log "Stopping Python legacy system..."
        cd "$DEPLOYMENT_DIR"
        docker-compose -f docker-compose.python.yml down
        log "✅ Services stopped"
        ;;
    --status)
        cd "$DEPLOYMENT_DIR"
        docker-compose -f docker-compose.python.yml --env-file .env.python ps
        ;;
    *)
        main "$1"
        ;;
esac