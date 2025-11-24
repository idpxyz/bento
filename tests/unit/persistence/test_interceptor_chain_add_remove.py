import pytest

from bento.persistence.interceptor.core.base import Interceptor, InterceptorChain
from bento.persistence.interceptor.core.types import (
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)


class TagInterceptor(Interceptor[dict]):
    def __init__(self, tag: str, calls: list[str], priority: InterceptorPriority) -> None:
        self.tag = tag
        self.calls = calls
        self._priority = priority

    @property
    def priority(self) -> InterceptorPriority:
        return self._priority

    async def before_operation(self, context: InterceptorContext[dict], next_interceptor):
        self.calls.append(self.tag)
        return await next_interceptor(context)


@pytest.mark.asyncio
async def test_add_and_remove_interceptor_affects_order():
    calls: list[str] = []
    a = TagInterceptor("A", calls, InterceptorPriority.NORMAL)
    b = TagInterceptor("B", calls, InterceptorPriority.HIGH)

    chain = InterceptorChain[dict]([a])
    chain.add_interceptor(b)  # B should execute before A due to higher priority

    ctx = InterceptorContext[dict](
        session=None,  # type: ignore[arg-type]
        entity_type=dict,
        operation=OperationType.CREATE,
        entity={},
    )

    await chain.execute_before(ctx)
    assert calls[0] == "B" and calls[1] == "A"

    # Now remove B and ensure only A runs
    calls.clear()
    chain.remove_interceptor(b)
    await chain.execute_before(ctx)
    assert calls == ["A"]
