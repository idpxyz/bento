class Address:
    """Simple postal address value object."""

    def __init__(self, line1: str, city: str, country: str) -> None:
        self.line1 = line1
        self.city = city
        self.country = country

    def __repr__(self) -> str:
        return f"Address(line1={self.line1!r}, city={self.city!r}, country={self.country!r})"
