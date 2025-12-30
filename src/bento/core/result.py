from __future__ import annotations


class Result[T, E]:
    def __init__(self, ok: T | None = None, err: E | None = None):
        self._ok, self._err = ok, err

    @property
    def is_ok(self) -> bool:
        return self._err is None

    @property
    def is_err(self) -> bool:
        return self._err is not None

    def unwrap(self) -> T:
        if self.is_err:
            raise RuntimeError(f"Unwrap error: {self._err}")
        return self._ok


    def unwrap_err(self) -> E:
        if self.is_ok:
            raise RuntimeError("Tried to unwrap_err on Ok")
        return self._err



def Ok[T, E](value: T) -> Result[T, E]:
    return Result(ok=value)


def Err[T, E](error: E) -> Result[T, E]:
    return Result(err=error)
