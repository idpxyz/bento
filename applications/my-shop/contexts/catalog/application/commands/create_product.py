"""Create product command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID

from contexts.catalog.domain.product import Product


@dataclass
class CreateProductCommand:
    """Create product command."""

    name: str
    description: str
    price: float
    stock: int = 0
    category_id: str | None = None


class CreateProductUseCase(BaseUseCase[CreateProductCommand, Product]):
    """Create product use case."""

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: CreateProductCommand) -> None:
        """Validate command."""
        if not command.name or not command.name.strip():
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "name", "reason": "cannot be empty"},
            )

        if command.price <= 0:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "price", "reason": "must be greater than 0"},
            )

    async def handle(self, command: CreateProductCommand) -> Product:
        """Handle command execution."""
        product_id = str(ID.generate())
        product = Product(
            id=product_id,
            name=command.name.strip(),
            description=command.description.strip() if command.description else "",
            price=command.price,
        )

        # Persist via repository
        product_repo = self.uow.repository(Product)
        await product_repo.save(product)

        return product
