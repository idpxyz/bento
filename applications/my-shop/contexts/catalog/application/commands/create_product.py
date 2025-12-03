"""Create product command and use case."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID

from contexts.catalog.domain.models.product import Product


@dataclass
class CreateProductCommand:
    """Create product command."""

    name: str
    description: str
    price: float
    stock: int = 0
    sku: str | None = None
    brand: str | None = None
    is_active: bool = True
    category_id: str | None = None  # 可选的分类ID


@command_handler
class CreateProductHandler(CommandHandler[CreateProductCommand, Product]):
    """Create product command handler."""

    def __init__(self, uow: UnitOfWork) -> None:
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
        product_id = ID.generate()
        product = Product(
            id=product_id,
            name=command.name.strip(),
            description=command.description.strip() if command.description else "",
            price=command.price,
            stock=command.stock,
            sku=command.sku,
            brand=command.brand,
            is_active=command.is_active,
            category_id=ID(command.category_id) if command.category_id else None,  # 关联分类
        )

        # Persist via repository
        product_repo = self.uow.repository(Product)
        await product_repo.save(product)

        return product
