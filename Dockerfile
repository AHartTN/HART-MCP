# Stage 1: Build dependencies
FROM python:3.11-slim-bookworm as builder

# Install unixODBC and dependencies for SQL Server (if needed in build stage)
# Keeping this for now, assuming some dependencies might need it during pip install
RUN apt-get update &&     apt-get install -y curl apt-transport-https gnupg &&     curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - &&     curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list &&     apt-get update &&     ACCEPT_EULA=Y apt-get install -y msodbcsql18 &&     apt-get install -y unixodbc-dev &&     rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final image
FROM python:3.11-slim-bookworm

# Install runtime dependencies for SQL Server (if not already installed in base image)
RUN apt-get update &&     apt-get install -y curl apt-transport-https gnupg &&     curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - &&     curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list &&     apt-get update &&     ACCEPT_EULA=Y apt-get install -y msodbcsql18 &&     apt-get install -y unixodbc-dev &&     rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the application code
COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]