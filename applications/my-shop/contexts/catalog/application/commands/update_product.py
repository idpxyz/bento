"""Update product command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.catalog.domain.product import Product


@dataclass
class UpdateProductCommand:
    """Update product command."""

    product_id: str
    name: str | None = None
    description: str | None = None
    price: float | None = None


class UpdateProductUseCase(BaseUseCase[UpdateProductCommand, Product]):
    """Update product use case."""

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: UpdateProductCommand) -> None:
        """Validate command."""
        if not command.product_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "product_id", "reason": "cannot be empty"},
            )

        # At least one field must be provided
        if not command.name and not command.description and not command.price:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"reason": "at least one field must be provided"},
            )

        # Price validation
        if command.price is not None and command.price <= 0:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "price", "reason": "must be greater than 0"},
            )

    async def handle(self, command: UpdateProductCommand) -> Product:
        """Handle command execution."""
        product_repo = self.uow.repository(Product)

        # Get product
        product = await product_repo.get(command.product_id)  # type: ignore[arg-type]
        if not product:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "product", "id": command.product_id},
            )

        # Update fields
        if command.name:
            product.name = command.name.strip()

        if command.description:
            product.description = command.description.strip()

        if command.price is not None:
            product.price = command.price

        # Save changes
        await product_repo.save(product)

        return product
