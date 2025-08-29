using MediatR;
using HART.MCP.Domain.Entities;

namespace HART.MCP.Application.Documents.Queries;

public record GetDocumentQuery(Guid Id) : IRequest<DocumentDto>;

public record GetDocumentsQuery(
    int Page = 1,
    int PageSize = 20,
    string? SearchTerm = null,
    DocumentType? Type = null,
    DocumentStatus? Status = null) : IRequest<DocumentDto[]>;

public record DocumentDto(
    Guid Id,
    string Title,
    string OriginalFileName,
    DocumentType Type,
    DocumentStatus Status,
    long SizeBytes,
    string MimeType,
    DateTime CreatedAt,
    DateTime? ProcessedAt,
    string? ProcessingError,
    int ChunkCount);