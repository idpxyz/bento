from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from bento.application.ports.uow import UnitOfWork as IUnitOfWork


class UseCase[InputT, OutputT](Protocol):
    async def __call__(self, inp: InputT) -> OutputT: ...


class BaseUseCase[CommandT, ResultT](ABC):
    """Base use case with validation and UnitOfWork orchestration.

    Responsibilities:
        - validate(command): Optional pre-validation (override as needed)
        - handle(command): Business logic (abstract)
        - execute(command): Orchestrates validation, UoW, commit

    Usage:
        class CreateOrderUseCase(BaseUseCase[CreateOrderCommand, OrderId]):
            async def handle(self, command: CreateOrderCommand) -> OrderId:
                repo = self.uow.repository(Order)
                order = Order(...)
                await repo.save(order)
                return order.id
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def validate(self, command: CommandT) -> None:  # override if needed
        return None

    @abstractmethod
    async def handle(self, command: CommandT) -> ResultT:
        """Implement business logic and return result."""
        raise NotImplementedError

    async def execute(self, command: CommandT) -> ResultT:
        """Run the use case within a UnitOfWork with validation and commit."""
        await self.validate(command)
        async with self.uow:  # begin/cleanup
            result = await self.handle(command)
            await self.uow.commit()  # collects and persists events (Outbox)
            return result
