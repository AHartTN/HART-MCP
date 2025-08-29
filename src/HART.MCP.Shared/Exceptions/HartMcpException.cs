namespace HART.MCP.Shared.Exceptions;

public class HartMcpException : Exception
{
    public string? ErrorCode { get; }
    public new Dictionary<string, object> Data { get; }

    public HartMcpException(string message, string? errorCode = null) : base(message)
    {
        ErrorCode = errorCode;
        Data = new Dictionary<string, object>();
    }

    public HartMcpException(string message, Exception innerException, string? errorCode = null) 
        : base(message, innerException)
    {
        ErrorCode = errorCode;
        Data = new Dictionary<string, object>();
    }

    public HartMcpException WithData(string key, object value)
    {
        Data[key] = value;
        return this;
    }
}

public class ValidationException : HartMcpException
{
    public ValidationException(string message) : base(message, "VALIDATION_ERROR")
    {
    }

    public ValidationException(string message, Dictionary<string, string[]> errors) : base(message, "VALIDATION_ERROR")
    {
        WithData("Errors", errors);
    }
}

public class NotFoundException : HartMcpException
{
    public NotFoundException(string message) : base(message, "NOT_FOUND")
    {
    }

    public NotFoundException(string entityName, object key) 
        : base($"Entity '{entityName}' with key '{key}' was not found.", "NOT_FOUND")
    {
        WithData("EntityName", entityName);
        WithData("Key", key);
    }
}

public class BusinessRuleException : HartMcpException
{
    public BusinessRuleException(string message) : base(message, "BUSINESS_RULE_VIOLATION")
    {
    }
}

public class ExternalServiceException : HartMcpException
{
    public string ServiceName { get; }

    public ExternalServiceException(string serviceName, string message) 
        : base($"External service '{serviceName}' error: {message}", "EXTERNAL_SERVICE_ERROR")
    {
        ServiceName = serviceName;
        WithData("ServiceName", serviceName);
    }

    public ExternalServiceException(string serviceName, string message, Exception innerException) 
        : base($"External service '{serviceName}' error: {message}", innerException, "EXTERNAL_SERVICE_ERROR")
    {
        ServiceName = serviceName;
        WithData("ServiceName", serviceName);
    }
}