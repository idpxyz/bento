from typing import Protocol


class UseCase[I, O](Protocol):
    async def __call__(self, inp: I) -> O: ...
