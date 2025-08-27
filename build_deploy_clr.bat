@echo off

SET ProjectDir=SqlClr
SET ProjectName=SqlClr
SET OutputDir=%ProjectDir%\bin\Debug\net48
SET AssemblyName=%ProjectName%.dll
SET SqlServerInstance=.
SET DatabaseName=HART_MCP



ECHO Building SQL CLR project...
"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" %ProjectDir%\%ProjectName%.csproj /p:Configuration=Debug /p:Platform="Any CPU"

IF %ERRORLEVEL% NEQ 0 (
    ECHO Build failed.
    GOTO :EOF
)

ECHO Deploying SQL CLR assembly to SQL Server...

sqlcmd -S %SqlServerInstance% -d %DatabaseName% -Q "
    IF EXISTS (SELECT * FROM sys.assemblies WHERE name = '%ProjectName%')
        DROP ASSEMBLY [%ProjectName%];
    CREATE ASSEMBLY [%ProjectName%]
    FROM '%CD%\%OutputDir%\%AssemblyName%'
    WITH PERMISSION_SET = UNSAFE;
    IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[QueryModel]') AND type IN (N'FN', N'IF', N'TF', N'FS', N'FT'))
        DROP FUNCTION [dbo].[QueryModel];
    CREATE FUNCTION [dbo].[QueryModel](@modelPath NVARCHAR(4000), @offset BIGINT, @length INT)
    RETURNS VARBINARY(MAX)
    AS EXTERNAL NAME [%ProjectName%].[UserDefinedFunctions].QueryModel;
"

IF %ERRORLEVEL% NEQ 0 (
    ECHO Deployment failed.
    GOTO :EOF
)

ECHO SQL CLR deployment complete.

