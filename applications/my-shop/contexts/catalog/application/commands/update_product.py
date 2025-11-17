"""Update product command (placeholder)."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase

from contexts.catalog.domain.product import Product


@dataclass
class UpdateProductCommand:
    """Update product command."""

    product_id: str
    name: str | None = None
    price: float | None = None


class UpdateProductUseCase(BaseUseCase[UpdateProductCommand, Product]):
    """Update product use case (TODO: implement)."""

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: UpdateProductCommand) -> None:
        pass

    async def handle(self, command: UpdateProductCommand) -> Product:
        raise NotImplementedError("TODO")
