"""Delete product command and use case."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork
# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.catalog.domain.models.product import Product


@dataclass
class DeleteProductCommand:
    """Delete product command."""

    product_id: str


@command_handler
class DeleteProductHandler(CommandHandler[DeleteProductCommand, None]):
    """Delete product use case.

    Handles product deletion (soft delete).
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: DeleteProductCommand) -> None:
        """Validate command."""
        if not command.product_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "product_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: DeleteProductCommand) -> None:
        """Handle command execution."""
        product_repo = self.uow.repository(Product)

        # Get product
        product = await product_repo.get(command.product_id)  # type: ignore[arg-type]
        if not product:
            raise ApplicationException(
                reason_code="NOT_FOUND",
                details={"resource": "product", "id": command.product_id},
            )

        # Delete product (soft delete via framework)
        await product_repo.delete(product)
