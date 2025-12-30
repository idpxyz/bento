"""Bento Framework Application Layer.

Pure CQRS application layer with Command and Query Handlers.
"""

# Main exports for the application layer
from bento.application.cqrs import (
    CommandHandler,
    ObservableCommandHandler,
    ObservableQueryHandler,
    QueryHandler,
)
from bento.application.decorators import command_handler, query_handler
from bento.application.dto import BaseDTO
from bento.application.ports.uow import UnitOfWork

__all__ = [
    "CommandHandler",
    "QueryHandler",
    "ObservableCommandHandler",
    "ObservableQueryHandler",
    "command_handler",
    "query_handler",
    "BaseDTO",
    "UnitOfWork",
]
