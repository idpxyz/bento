"""Get product query (placeholder)."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase

from contexts.catalog.domain.product import Product


@dataclass
class GetProductQuery:
    """Get product query."""

    product_id: str


class GetProductUseCase(BaseUseCase[GetProductQuery, Product]):
    """Get product use case (TODO: implement)."""

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: GetProductQuery) -> None:
        pass

    async def handle(self, query: GetProductQuery) -> Product:
        raise NotImplementedError("TODO")
