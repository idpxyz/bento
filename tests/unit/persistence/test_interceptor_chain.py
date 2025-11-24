import pytest

from bento.persistence.interceptor.core.base import Interceptor, InterceptorChain
from bento.persistence.interceptor.core.types import (
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)


class RecorderInterceptor(Interceptor[dict]):
    def __init__(self, name: str, calls: list[str], priority: InterceptorPriority) -> None:
        self._name = name
        self._calls = calls
        self._priority = priority

    @property
    def priority(self) -> InterceptorPriority:
        return self._priority

    async def before_operation(
        self,
        context: InterceptorContext[dict],
        next_interceptor,
    ):
        self._calls.append(f"{self._name}.before")
        return await next_interceptor(context)

    async def after_operation(
        self,
        context: InterceptorContext[dict],
        result,
        next_interceptor,
    ):
        self._calls.append(f"{self._name}.after")
        return await next_interceptor(context, result)

    async def process_result(
        self,
        context: InterceptorContext[dict],
        result: dict,
        next_interceptor,
    ):
        self._calls.append(f"{self._name}.process_result")
        return await next_interceptor(context, result)

    async def on_error(
        self,
        context: InterceptorContext[dict],
        error: Exception,
        next_interceptor,
    ):
        self._calls.append(f"{self._name}.on_error")
        return await next_interceptor(context, error)


@pytest.mark.asyncio
async def test_interceptor_chain_order_and_flows():
    calls: list[str] = []

    hi = RecorderInterceptor("HI", calls, InterceptorPriority.HIGH)  # runs first
    norm = RecorderInterceptor("NORM", calls, InterceptorPriority.NORMAL)  # runs second

    chain = InterceptorChain[dict]([norm, hi])  # unsorted input; chain sorts by priority

    # Build context
    context = InterceptorContext[dict](
        session=None,  # type: ignore[arg-type]
        entity_type=dict,
        operation=OperationType.CREATE,
        entity={"x": 1},
        actor="tester",
    )

    # before
    await chain.execute_before(context)
    # after
    await chain.execute_after(context, result={"ok": True})
    # process single result
    await chain.process_result(context, result={"ok": True})
    # error flow
    with pytest.raises(RuntimeError):
        await chain.execute_on_error(context, RuntimeError("boom"))
    # batch results
    await chain.process_batch_results(context, results=[{"i": 1}, {"i": 2}])

    # Order assertions: HI interceptors wrap before NORM
    # For each phase, HI should be recorded before NORM
    phases = {
        "before": [i for i, c in enumerate(calls) if c.endswith(".before")],
        "after": [i for i, c in enumerate(calls) if c.endswith(".after")],
        "process_result": [i for i, c in enumerate(calls) if c.endswith(".process_result")][:1],
        # only check first single process_result call ordering
    }

    # Ensure there is at least one entry per phase
    assert all(len(idxs) >= 1 for idxs in phases.values())

    # HI should appear before NORM in before/after first occurrences
    assert calls[phases["before"][0]] == "HI.before"
    assert calls[phases["after"][0]] == "HI.after"

    # process_batch_results invokes process_result per item; ensure it's recorded
    assert any(c.startswith("HI.process_result") for c in calls)
    assert any(c.startswith("NORM.process_result") for c in calls)
