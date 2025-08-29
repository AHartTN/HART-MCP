# HART-MCP Makefile for easy development and deployment
# Supports both Python legacy and C# enterprise systems

.PHONY: help python-dev python-deploy python-stop python-logs python-test
.PHONY: csharp-dev csharp-deploy csharp-stop csharp-logs csharp-test csharp-build
.PHONY: clean clean-all status fix-permissions setup-env

# Default target
help:
	@echo "🚀 HART-MCP Development & Deployment Commands"
	@echo "=============================================="
	@echo ""
	@echo "📁 Setup Commands:"
	@echo "  make setup-env        Create .env files for both systems"
	@echo "  make fix-permissions  Fix file permissions (Linux/Mac)"
	@echo ""
	@echo "🐍 Python Legacy System:"
	@echo "  make python-dev       Start Python system locally"
	@echo "  make python-deploy    Deploy Python system with Docker"
	@echo "  make python-stop      Stop Python Docker containers"
	@echo "  make python-logs      Show Python container logs"
	@echo "  make python-test      Run Python tests"
	@echo ""
	@echo "🏢 C# Enterprise System:"
	@echo "  make csharp-build     Build C# solution locally"
	@echo "  make csharp-dev       Start C# system locally"
	@echo "  make csharp-deploy    Deploy C# system with Docker"
	@echo "  make csharp-stop      Stop C# Docker containers"
	@echo "  make csharp-logs      Show C# container logs"
	@echo "  make csharp-test      Run C# tests"
	@echo ""
	@echo "🧹 Cleanup Commands:"
	@echo "  make clean           Clean build artifacts"
	@echo "  make clean-all       Stop all containers and clean"
	@echo "  make status          Show status of both systems"

# =============================================================================
# Setup Commands
# =============================================================================

setup-env:
	@echo "🔧 Setting up environment files..."
	@chmod +x deployment/scripts/*.sh
	@./deployment/scripts/deploy-python.sh --setup-env || echo "Python env setup skipped"
	@./deployment/scripts/deploy-csharp.sh --setup-env || echo "C# env setup skipped"
	@echo "✅ Environment setup complete"

fix-permissions:
	@echo "🔧 Fixing file permissions..."
	@chmod +x deployment/scripts/*.sh
	@chmod -R 755 deployment/scripts/
	@echo "✅ Permissions fixed"

# =============================================================================
# Python Legacy System
# =============================================================================

python-dev:
	@echo "🐍 Starting Python development server..."
	@cd legacy-python && python -m pip install -r requirements.txt
	@cd legacy-python && python server.py

python-deploy:
	@echo "🐍 Deploying Python legacy system..."
	@chmod +x deployment/scripts/deploy-python.sh
	@./deployment/scripts/deploy-python.sh

python-stop:
	@echo "🐍 Stopping Python system..."
	@chmod +x deployment/scripts/deploy-python.sh
	@./deployment/scripts/deploy-python.sh --stop

python-logs:
	@echo "🐍 Showing Python logs..."
	@chmod +x deployment/scripts/deploy-python.sh
	@./deployment/scripts/deploy-python.sh --logs

python-test:
	@echo "🐍 Running Python tests..."
	@cd legacy-python && python -m pytest tests/ -v --tb=short

python-coverage:
	@echo "🐍 Running Python tests with coverage..."
	@cd legacy-python && python -m pytest tests/ --cov=. --cov-report=html --cov-report=term

# =============================================================================
# C# Enterprise System
# =============================================================================

csharp-build:
	@echo "🏢 Building C# solution..."
	@cd enterprise-csharp && dotnet restore
	@cd enterprise-csharp && dotnet build --configuration Release

csharp-dev:
	@echo "🏢 Starting C# development server..."
	@cd enterprise-csharp && dotnet run --project src/HART.MCP.API

csharp-deploy:
	@echo "🏢 Deploying C# enterprise system..."
	@chmod +x deployment/scripts/deploy-csharp.sh
	@./deployment/scripts/deploy-csharp.sh

csharp-dev-deploy:
	@echo "🏢 Deploying C# system in development mode..."
	@chmod +x deployment/scripts/deploy-csharp.sh
	@./deployment/scripts/deploy-csharp.sh --dev

csharp-stop:
	@echo "🏢 Stopping C# system..."
	@chmod +x deployment/scripts/deploy-csharp.sh
	@./deployment/scripts/deploy-csharp.sh --stop

csharp-logs:
	@echo "🏢 Showing C# logs..."
	@chmod +x deployment/scripts/deploy-csharp.sh
	@./deployment/scripts/deploy-csharp.sh --logs

csharp-test:
	@echo "🏢 Running C# tests..."
	@cd enterprise-csharp && dotnet test --logger trx --collect:"XPlat Code Coverage"

csharp-test-unit:
	@echo "🏢 Running C# unit tests..."
	@cd enterprise-csharp && dotnet test tests/HART.MCP.UnitTests

csharp-test-integration:
	@echo "🏢 Running C# integration tests..."
	@cd enterprise-csharp && dotnet test tests/HART.MCP.IntegrationTests

# =============================================================================
# Database & SQL CLR Management
# =============================================================================

deploy-migrations:
	@echo "🗄️ Deploying database migrations..."
	@echo "Run these SQL scripts on your SQL Server 2025 instance:"
	@echo "  1. shared-resources/migrations/InitialCreate.sql"
	@echo "  2. shared-resources/migrations/DeploySqlClr.sql"
	@echo "Note: SQL CLR requires SQL Server 2025 for quantum model features"

sqlclr-build:
	@echo "⚡ Building SQL CLR assembly..."
	@cd enterprise-csharp/SqlClr && dotnet build --configuration Release

# =============================================================================
# Development Utilities
# =============================================================================

status:
	@echo "📊 System Status"
	@echo "==============="
	@echo ""
	@echo "🐍 Python Legacy System:"
	@docker-compose -f deployment/docker-compose.python.yml ps 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "🏢 C# Enterprise System:"
	@docker-compose -f deployment/docker-compose.csharp.yml ps 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "🔍 Health Checks:"
	@curl -s http://localhost:8000/health >/dev/null 2>&1 && echo "  ✅ Python API (http://localhost:8000)" || echo "  ❌ Python API (http://localhost:8000)"
	@curl -s http://localhost:8080/health >/dev/null 2>&1 && echo "  ✅ C# API (http://localhost:8080)" || echo "  ❌ C# API (http://localhost:8080)"

logs:
	@echo "📋 Showing logs for all systems..."
	@echo "Python logs:"
	@docker logs hart-mcp-python 2>/dev/null | tail -20 || echo "Python container not running"
	@echo ""
	@echo "C# logs:"
	@docker logs hart-mcp-csharp 2>/dev/null | tail -20 || echo "C# container not running"

# =============================================================================
# Cleanup Commands
# =============================================================================

clean:
	@echo "🧹 Cleaning build artifacts..."
	@cd legacy-python && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@cd legacy-python && find . -name "*.pyc" -delete 2>/dev/null || true
	@cd enterprise-csharp && dotnet clean 2>/dev/null || true
	@cd enterprise-csharp && find . -type d -name "bin" -exec rm -rf {} + 2>/dev/null || true
	@cd enterprise-csharp && find . -type d -name "obj" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Build artifacts cleaned"

clean-docker:
	@echo "🧹 Cleaning Docker containers and volumes..."
	@docker-compose -f deployment/docker-compose.python.yml down -v 2>/dev/null || true
	@docker-compose -f deployment/docker-compose.csharp.yml down -v 2>/dev/null || true
	@docker system prune -f
	@echo "✅ Docker resources cleaned"

clean-all: clean clean-docker
	@echo "🧹 Complete cleanup finished"

# =============================================================================
# Testing & Quality
# =============================================================================

test-all: python-test csharp-test
	@echo "✅ All tests completed"

format-python:
	@echo "🎨 Formatting Python code..."
	@cd legacy-python && python -m black . --line-length 88
	@cd legacy-python && python -m isort .
	@echo "✅ Python code formatted"

lint-python:
	@echo "🔍 Linting Python code..."
	@cd legacy-python && python -m ruff check .
	@echo "✅ Python code linted"

format-csharp:
	@echo "🎨 Formatting C# code..."
	@cd enterprise-csharp && dotnet format
	@echo "✅ C# code formatted"

# =============================================================================
# Quick Development Workflows
# =============================================================================

dev-python: 
	@echo "🚀 Quick Python development workflow..."
	@make python-dev

dev-csharp:
	@echo "🚀 Quick C# development workflow..."
	@make csharp-build
	@make csharp-dev

# Full development environment (both systems)
dev-all:
	@echo "🚀 Starting both development environments..."
	@echo "This will start both Python and C# systems in the background"
	@make python-deploy &
	@sleep 30
	@make csharp-deploy &
	@echo "✅ Both systems starting up..."
	@echo "Check status with: make status"

# =============================================================================
# Production Deployment
# =============================================================================

prod-python:
	@echo "🚀 Production Python deployment..."
	@make python-deploy
	@make status

prod-csharp:
	@echo "🚀 Production C# deployment..."
	@make csharp-deploy
	@make status

# =============================================================================
# Documentation
# =============================================================================

docs:
	@echo "📚 Available Documentation:"
	@echo "  - Main README: README.md"
	@echo "  - Python System: legacy-python/README.md"
	@echo "  - C# System: enterprise-csharp/README.md"
	@echo "  - Deployment Guide: shared-resources/docs/DEPLOYMENT.md"
	@echo ""
	@echo "🌐 Web Documentation (when running):"
	@echo "  - Python API Docs: http://localhost:8000/docs"
	@echo "  - C# Swagger UI: http://localhost:8080/swagger"