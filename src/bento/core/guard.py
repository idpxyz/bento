def require(condition: bool, message: str = "Invariant violated"):
    if not condition:
        raise ValueError(message)
