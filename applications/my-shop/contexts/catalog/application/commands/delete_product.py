"""Delete product command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.catalog.domain.product import Product


@dataclass
class DeleteProductCommand:
    """Delete product command."""

    product_id: str


class DeleteProductUseCase(BaseUseCase[DeleteProductCommand, None]):
    """Delete product use case.

    Handles product deletion (soft delete).
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: DeleteProductCommand) -> None:
        """Validate command."""
        if not command.product_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "product_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: DeleteProductCommand) -> None:
        """Handle command execution."""
        product_repo = self.uow.repository(Product)

        # Get product
        product = await product_repo.get(command.product_id)  # type: ignore[arg-type]
        if not product:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "product", "id": command.product_id},
            )

        # Delete product (soft delete via framework)
        await product_repo.delete(product)
