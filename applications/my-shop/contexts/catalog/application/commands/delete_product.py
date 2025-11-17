"""Delete product command (placeholder)."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase


@dataclass
class DeleteProductCommand:
    """Delete product command."""

    product_id: str


class DeleteProductUseCase(BaseUseCase[DeleteProductCommand, None]):
    """Delete product use case (TODO: implement)."""

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: DeleteProductCommand) -> None:
        pass

    async def handle(self, command: DeleteProductCommand) -> None:
        raise NotImplementedError("TODO")
