# Use an official Python runtime as a parent image
FROM python:3.10-slim-bookworm

# Install unixODBC and dependencies for SQL Server
RUN apt-get update &&     apt-get install -y curl apt-transport-https gnupg &&     curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - &&     curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list &&     apt-get update &&     ACCEPT_EULA=Y apt-get install -y msodbcsql18 &&     apt-get install -y unixodbc-dev &&     rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Make the startup script executable
RUN chmod +x /app/start_gunicorn.sh

EXPOSE 8080
CMD ["/app/start_gunicorn.sh"]
