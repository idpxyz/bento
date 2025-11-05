from typing import Protocol, TypeVar, Generic

I = TypeVar("I")
O = TypeVar("O")

class UseCase(Protocol, Generic[I, O]):
    async def __call__(self, inp: I) -> O: ...
