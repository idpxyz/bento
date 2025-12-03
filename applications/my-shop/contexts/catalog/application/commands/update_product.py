"""Update product command and use case."""

from dataclasses import dataclass

from bento.application.ports.uow import UnitOfWork
from bento.application.cqrs import CommandHandler
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID

from contexts.catalog.domain.product import Product


@dataclass
class UpdateProductCommand:
    """Update product command."""

    product_id: str
    name: str | None = None
    description: str | None = None
    price: float | None = None
    stock: int | None = None
    sku: str | None = None
    brand: str | None = None
    is_active: bool | None = None
    category_id: str | None = None  # 可选：更新分类


class UpdateProductHandler(CommandHandler[UpdateProductCommand, Product]):
    """Update product use case."""

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: UpdateProductCommand) -> None:
        """Validate command."""
        if not command.product_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "product_id", "reason": "cannot be empty"},
            )

        # At least one field must be provided
        if (
            not command.name
            and not command.description
            and not command.price
            and command.stock is None
            and not command.sku
            and not command.brand
            and command.is_active is None
            and command.category_id is None
        ):
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
            product.change_price(command.price)  # 使用业务方法

        if command.stock is not None:
            product.stock = command.stock

        if command.sku is not None:
            product.sku = command.sku

        if command.brand is not None:
            product.brand = command.brand

        if command.is_active is not None:
            product.is_active = command.is_active

        if command.category_id is not None:
            if command.category_id:
                # ✅ 转换 str 为 ID 类型
                product.assign_to_category(ID(command.category_id))
            else:
                product.remove_from_category()

        # Save changes
        await product_repo.save(product)

        return product
