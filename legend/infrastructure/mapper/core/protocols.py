from typing import Protocol, TypeVar, runtime_checkable

S = TypeVar('S')  # Source type
T = TypeVar('T')  # Target type


@runtime_checkable
class SupportsMap(Protocol[S, T]):
    """Minimal protocol exposing the `map` method used in repositories.

    This avoids depending on the concrete BidirectionalMapper implementation
    while still letting static type checkers and IDEs recognise the method.
    """

    def map(self, source: S, /) -> T: ...
