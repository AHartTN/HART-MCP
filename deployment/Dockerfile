

# Multi-stage production-ready Dockerfile for HART-MCP C# Enterprise Solution
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 8080
EXPOSE 8081

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
ARG BUILD_CONFIGURATION=Release
WORKDIR /src

# Copy project files for dependency restoration
COPY ["src/HART.MCP.API/HART.MCP.API.csproj", "src/HART.MCP.API/"]
COPY ["src/HART.MCP.Application/HART.MCP.Application.csproj", "src/HART.MCP.Application/"]
COPY ["src/HART.MCP.Infrastructure/HART.MCP.Infrastructure.csproj", "src/HART.MCP.Infrastructure/"]
COPY ["src/HART.MCP.Domain/HART.MCP.Domain.csproj", "src/HART.MCP.Domain/"]
COPY ["src/HART.MCP.Shared/HART.MCP.Shared.csproj", "src/HART.MCP.Shared/"]
COPY ["src/HART.MCP.AI/HART.MCP.AI.csproj", "src/HART.MCP.AI/"]
COPY ["SqlClr/SqlClr.csproj", "SqlClr/"]

# Restore dependencies
RUN dotnet restore "src/HART.MCP.API/HART.MCP.API.csproj"

# Copy source code
COPY . .

# Build and publish application
WORKDIR "/src/src/HART.MCP.API"
RUN dotnet build "HART.MCP.API.csproj" -c $BUILD_CONFIGURATION -o /app/build
RUN dotnet publish "HART.MCP.API.csproj" -c $BUILD_CONFIGURATION -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app

# Copy published application
COPY --from=build /app/publish .

# Security hardening
RUN rm -rf /var/cache/apt/* && \
    rm -rf /tmp/* && \
    find /app -type d -exec chmod 755 {} + && \
    find /app -type f -exec chmod 644 {} + && \
    chmod +x /app/HART.MCP.API || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

USER appuser
ENTRYPOINT ["dotnet", "HART.MCP.API.dll"]