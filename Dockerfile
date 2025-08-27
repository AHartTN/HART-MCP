# Multi-stage production-ready Dockerfile for HART-MCP
FROM python:3.11-slim-bookworm as builder

# Install build dependencies and SQL Server ODBC driver
RUN apt-get update && \
    apt-get install -y \
        curl \
        apt-transport-https \
        gnupg \
        gcc \
        g++ \
        unixodbc-dev && \
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    echo "deb [arch=amd64] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final production image
FROM python:3.11-slim-bookworm

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y \
        curl \
        apt-transport-https \
        gnupg \
        unixodbc && \
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    echo "deb [arch=amd64] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create non-root user for security
RUN useradd -m -u 1000 hartuser && \
    mkdir -p /app /app/logs /app/static && \
    chown -R hartuser:hartuser /app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/hartuser/.local
ENV PATH=/home/hartuser/.local/bin:$PATH

# Copy application code with proper ownership
COPY --chown=hartuser:hartuser . .

# Switch to non-root user
USER hartuser

# Create necessary directories
RUN mkdir -p logs

# Expose application port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production-ready startup command with proper workers and logging
CMD ["python", "-m", "uvicorn", "server:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--access-log", \
     "--log-level", "info"]