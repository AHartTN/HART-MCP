# HART-MCP Database Migration Script
# Executes SQL migrations in order against target database

param(
    [Parameter(Mandatory=$true)]
    [string]$ConnectionString,
    
    [Parameter(Mandatory=$false)]
    [string]$MigrationPath = ".",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

# Import SQL Server module
Import-Module SqlServer -ErrorAction SilentlyContinue

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

function Get-MigrationFiles {
    param([string]$Path)
    
    return Get-ChildItem -Path $Path -Filter "*.sql" | 
           Where-Object { $_.Name -match '^\d{3}_.*\.sql$' } |
           Sort-Object Name
}

function Test-DatabaseConnection {
    param([string]$ConnectionString)
    
    try {
        $connection = New-Object System.Data.SqlClient.SqlConnection($ConnectionString)
        $connection.Open()
        $connection.Close()
        return $true
    }
    catch {
        Write-Log "Database connection failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Initialize-MigrationTable {
    param([string]$ConnectionString)
    
    $sql = @"
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DatabaseMigrations')
BEGIN
    CREATE TABLE [DatabaseMigrations] (
        [Id] INT IDENTITY(1,1) PRIMARY KEY,
        [MigrationName] NVARCHAR(255) NOT NULL UNIQUE,
        [ExecutedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [ExecutedBy] NVARCHAR(255) NOT NULL DEFAULT SYSTEM_USER,
        [ChecksumBefore] NVARCHAR(64) NULL,
        [ChecksumAfter] NVARCHAR(64) NULL
    );
    PRINT 'Created DatabaseMigrations table';
END
"@

    try {
        Invoke-Sqlcmd -ConnectionString $ConnectionString -Query $sql
        Write-Log "Migration tracking table initialized"
    }
    catch {
        Write-Log "Failed to initialize migration table: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Get-AppliedMigrations {
    param([string]$ConnectionString)
    
    $sql = "SELECT MigrationName FROM DatabaseMigrations ORDER BY Id"
    
    try {
        $result = Invoke-Sqlcmd -ConnectionString $ConnectionString -Query $sql
        return $result | ForEach-Object { $_.MigrationName }
    }
    catch {
        Write-Log "Failed to get applied migrations: $($_.Exception.Message)" "ERROR"
        return @()
    }
}

function Execute-Migration {
    param(
        [string]$ConnectionString,
        [System.IO.FileInfo]$MigrationFile,
        [bool]$DryRun
    )
    
    $migrationName = $MigrationFile.BaseName
    Write-Log "Processing migration: $migrationName"
    
    if ($DryRun) {
        Write-Log "DRY RUN - Would execute: $($MigrationFile.FullName)" "INFO"
        return $true
    }
    
    try {
        # Read and execute migration file
        $migrationSql = Get-Content $MigrationFile.FullName -Raw
        
        # Replace template variables
        $migrationSql = $migrationSql.Replace('$(date)', (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
        
        # Start transaction for migration
        $transactionSql = @"
BEGIN TRANSACTION;
TRY
    $migrationSql
    
    -- Record successful migration
    INSERT INTO DatabaseMigrations (MigrationName) VALUES ('$migrationName');
    
    COMMIT TRANSACTION;
    PRINT 'Migration $migrationName completed successfully';
END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION;
    DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
    DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
    DECLARE @ErrorState INT = ERROR_STATE();
    
    RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
END CATCH;
"@
        
        Invoke-Sqlcmd -ConnectionString $ConnectionString -Query $transactionSql -Verbose
        Write-Log "Migration $migrationName executed successfully" "SUCCESS"
        return $true
    }
    catch {
        Write-Log "Migration $migrationName failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Main execution
Write-Log "HART-MCP Database Migration Starting"

# Validate connection
if (-not (Test-DatabaseConnection -ConnectionString $ConnectionString)) {
    Write-Log "Cannot proceed without database connection" "ERROR"
    exit 1
}

# Initialize migration tracking
try {
    Initialize-MigrationTable -ConnectionString $ConnectionString
}
catch {
    Write-Log "Failed to initialize migration system" "ERROR"
    exit 1
}

# Get migration files
$migrationFiles = Get-MigrationFiles -Path $MigrationPath
if ($migrationFiles.Count -eq 0) {
    Write-Log "No migration files found in $MigrationPath"
    exit 0
}

Write-Log "Found $($migrationFiles.Count) migration files"

# Get already applied migrations
$appliedMigrations = Get-AppliedMigrations -ConnectionString $ConnectionString
Write-Log "Found $($appliedMigrations.Count) previously applied migrations"

# Execute pending migrations
$pendingMigrations = $migrationFiles | Where-Object { 
    $_.BaseName -notin $appliedMigrations 
}

if ($pendingMigrations.Count -eq 0) {
    Write-Log "No pending migrations to execute"
    exit 0
}

Write-Log "Executing $($pendingMigrations.Count) pending migrations"

$successCount = 0
$failureCount = 0

foreach ($migration in $pendingMigrations) {
    if (Execute-Migration -ConnectionString $ConnectionString -MigrationFile $migration -DryRun $DryRun) {
        $successCount++
    }
    else {
        $failureCount++
        if (-not $Force) {
            Write-Log "Stopping migration due to failure (use -Force to continue)" "ERROR"
            break
        }
    }
}

Write-Log "Migration complete: $successCount successful, $failureCount failed"

if ($failureCount -gt 0) {
    exit 1
}
else {
    exit 0
}