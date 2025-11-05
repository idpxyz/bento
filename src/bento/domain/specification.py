from typing import Protocol, TypeVar

T = TypeVar("T", contravariant=True)


class Specification(Protocol[T]):
    def is_satisfied_by(self, candidate: T) -> bool: ...


class AndSpecification[T]:
    def __init__(self, a: Specification[T], b: Specification[T]) -> None:
        self.a = a
        self.b = b

    def is_satisfied_by(self, candidate: T) -> bool:
        return self.a.is_satisfied_by(candidate) and self.b.is_satisfied_by(candidate)


def and_spec(a: Specification[T], b: Specification[T]) -> Specification[T]:
    return AndSpecification(a, b)
