using HART.MCP.Domain.Entities;
using MediatR;

namespace HART.MCP.Application.Documents.Commands;

public record CreateDocumentCommand(
    string Title,
    string Content,
    string OriginalFileName,
    DocumentType Type,
    long SizeBytes,
    string MimeType,
    string Hash) : IRequest<Guid>;

public record ProcessDocumentCommand(Guid DocumentId) : IRequest;

public record DeleteDocumentCommand(Guid DocumentId) : IRequest;