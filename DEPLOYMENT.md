# HART-MCP Production Deployment Guide 🚀

## 📋 Pre-Deployment Checklist

### ✅ Infrastructure Requirements
- [ ] Docker Engine 24.0+ installed
- [ ] Docker Compose v2.0+ installed
- [ ] Minimum 8GB RAM available
- [ ] 20GB+ disk space for databases
- [ ] Network access to external services (if using cloud LLMs)

### ✅ Security Configuration
- [ ] Strong API keys configured in `.env`
- [ ] Database passwords are secure (12+ characters)
- [ ] SSL certificates generated (for production)
- [ ] Firewall rules configured for ports 8000, 5432, 19530, 7687
- [ ] Non-root user created for deployment

### ✅ Environment Setup
- [ ] `.env` file created and validated
- [ ] All required API keys added
- [ ] Database connection strings tested
- [ ] LLM fallback order configured

## 🚀 Production Deployment Steps

### Step 1: Environment Preparation
```bash
# Clone repository
git clone https://github.com/your-org/HART-MCP.git
cd HART-MCP

# Create production environment file
cp .env.example .env

# Edit configuration (use secure values)
nano .env
```

### Step 2: Configuration Validation
```bash
# Validate configuration before deployment
python -c "from config import validate_config; print(validate_config())"

# Should output: {'valid': True, 'errors': [], 'warnings': [...]}
```

### Step 3: Database Initialization
```bash
# Initialize databases (one-time setup)
python setup_databases.py

# Verify database connections
python -c "
import asyncio
from db_connectors import test_all_connections
asyncio.run(test_all_connections())
"
```

### Step 4: Production Deployment
```bash
# Deploy full production stack
docker-compose --profile production up --build -d

# Verify all services are healthy
docker-compose ps
docker-compose logs hart-mcp

# Run health checks
curl -f http://localhost:8000/health || echo "Health check failed"
curl -f http://localhost:8000/api/info || echo "API check failed"
```

### Step 5: Load Testing & Validation
```bash
# Test LLM fallback system
python test_llm_fallback.py

# Run comprehensive tests
pytest -v --cov

# Performance baseline
curl -X POST "http://localhost:8000/agent/tot" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is artificial intelligence?"}'
```

## 🔧 Production Configuration

### Essential Environment Variables
```bash
# Security
API_KEY=secure-random-key-256-bits
ENABLE_CORS=false
TRUSTED_HOSTS=yourdomain.com,api.yourdomain.com

# Performance
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=300
CACHE_TTL=3600
ENABLE_CACHING=true

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
LOG_LEVEL=INFO

# Database Connection Pooling
SQL_SERVER_POOL_SIZE=10
REDIS_POOL_SIZE=20
```

### Resource Limits (docker-compose.override.yml)
```yaml
version: '3.8'
services:
  hart-mcp:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
    restart: unless-stopped
    
  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
          
  milvus-standalone:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G
```

## 📊 Monitoring & Observability

### Health Monitoring
```bash
# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "🔍 System Health Check"
echo "======================"

# API Health
echo -n "API Health: "
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ HEALTHY"
else
    echo "❌ UNHEALTHY"
fi

# Database Status
echo -n "Database Status: "
if curl -sf http://localhost:8000/status > /dev/null; then
    echo "✅ CONNECTED"
else
    echo "❌ DISCONNECTED"
fi

# Container Status
echo "Container Status:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}"

echo ""
echo "📊 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
EOF

chmod +x monitor.sh
```

### Log Management
```bash
# Configure log rotation
cat > /etc/logrotate.d/hart-mcp << 'EOF'
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0644 root root
}
EOF

# Centralized logging
docker-compose logs -f --tail=100 hart-mcp | tee -a /var/log/hart-mcp.log
```

## 🛡️ Security Best Practices

### SSL/TLS Configuration
```bash
# Generate SSL certificates (using Let's Encrypt)
certbot certonly --standalone -d yourdomain.com

# Update nginx.conf with SSL
```

### Network Security
```bash
# Configure firewall (Ubuntu/Debian)
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Docker network isolation
docker network create --driver bridge --internal hart-internal
```

### API Security
```bash
# Rate limiting configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# API key rotation strategy
API_KEY_ROTATION_DAYS=90
```

## 🔄 Backup & Disaster Recovery

### Database Backups
```bash
# Automated backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/hart-mcp/$(date +%Y-%m-%d)"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
docker-compose exec postgres pg_dump -U hart_user hart_mcp > $BACKUP_DIR/postgres.sql

# Milvus backup
docker-compose exec milvus-standalone mkdir -p /backup
docker-compose cp milvus-standalone:/var/lib/milvus $BACKUP_DIR/milvus

# Neo4j backup
docker-compose exec neo4j neo4j-admin dump --database=neo4j --to=/backup/neo4j.dump
docker-compose cp neo4j:/backup/neo4j.dump $BACKUP_DIR/

# Compress backups
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "✅ Backup completed: $BACKUP_DIR.tar.gz"
EOF

chmod +x backup.sh

# Schedule daily backups
echo "0 2 * * * /path/to/backup.sh" | crontab -
```

### Disaster Recovery
```bash
# Recovery script
cat > restore.sh << 'EOF'
#!/bin/bash
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

echo "🔄 Starting disaster recovery..."

# Stop services
docker-compose down

# Extract backup
tar -xzf $BACKUP_FILE
BACKUP_DIR=$(basename $BACKUP_FILE .tar.gz)

# Restore databases
docker-compose up postgres -d
sleep 10
docker-compose exec postgres psql -U hart_user -c "DROP DATABASE IF EXISTS hart_mcp;"
docker-compose exec postgres createdb -U hart_user hart_mcp
cat $BACKUP_DIR/postgres.sql | docker-compose exec -T postgres psql -U hart_user hart_mcp

# Restore other services
docker-compose up -d

echo "✅ Recovery completed"
EOF

chmod +x restore.sh
```

## 🚀 Scaling & Performance

### Horizontal Scaling
```bash
# Scale application instances
docker-compose up --scale hart-mcp=3 -d

# Load balancer configuration (nginx.conf)
upstream hart-mcp {
    server hart-mcp-1:8000;
    server hart-mcp-2:8000;
    server hart-mcp-3:8000;
}
```

### Performance Tuning
```bash
# Database optimization
SQL_SERVER_POOL_SIZE=20
MILVUS_INDEX_TYPE=IVF_FLAT
NEO4J_HEAP_SIZE=2G

# Application tuning
UVICORN_WORKERS=4
UVICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
WEB_CONCURRENCY=4
```

## 📈 Metrics & Analytics

### Prometheus Integration
```yaml
# Add to docker-compose.yml
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Key Metrics to Monitor
- Request latency (p95, p99)
- Database connection pool utilization
- LLM response times and success rates
- Memory usage and garbage collection
- Error rates by endpoint

## 🆘 Troubleshooting

### Common Issues
1. **Database Connection Timeouts**
   ```bash
   # Increase connection timeout
   SQL_SERVER_TIMEOUT=60
   ```

2. **Memory Issues**
   ```bash
   # Monitor memory usage
   docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"
   ```

3. **LLM Rate Limits**
   ```bash
   # Check fallback logs
   docker-compose logs hart-mcp | grep "fallback"
   ```

### Emergency Procedures
```bash
# Quick restart
docker-compose restart hart-mcp

# Full system restart
docker-compose down && docker-compose up -d

# Emergency shutdown
docker-compose down --remove-orphans
```

## ✅ Post-Deployment Verification

### System Validation
```bash
# Run full test suite
python -m pytest tests/ -v

# Validate all endpoints
curl -X GET "http://localhost:8000/health"
curl -X GET "http://localhost:8000/api/info"
curl -X POST "http://localhost:8000/agent/bdi" -H "Content-Type: application/json" -d '{}'

# Performance baseline
ab -n 1000 -c 10 http://localhost:8000/health
```

### Success Criteria
- [ ] All health checks pass
- [ ] Database connections stable
- [ ] LLM fallback working
- [ ] API response time < 2s
- [ ] Memory usage < 80%
- [ ] No error logs in past 24h

---

## 📞 Support Contacts

- **Production Issues**: ops@yourcompany.com
- **Security Incidents**: security@yourcompany.com  
- **General Support**: support@yourcompany.com

**🎉 Congratulations!** Your HART-MCP system is now production-ready!