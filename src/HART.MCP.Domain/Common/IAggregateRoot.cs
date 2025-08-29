using MediatR;

namespace HART.MCP.Domain.Common;

public interface IAggregateRoot
{
    IReadOnlyCollection<INotification> DomainEvents { get; }
    void ClearDomainEvents();
}