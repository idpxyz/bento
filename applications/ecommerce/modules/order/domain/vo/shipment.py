class Shipment:
    """Abstract shipment value object."""

    carrier: str


class ShipmentFedex(Shipment):
    def __init__(self, tracking_no: str, service: str | None = None) -> None:
        self.carrier = "fedex"
        self.tracking_no = tracking_no
        self.service = service

    def __repr__(self) -> str:
        return f"ShipmentFedex(tracking_no={self.tracking_no!r}, service={self.service!r})"


class ShipmentLocal(Shipment):
    def __init__(self, tracking_no: str | None = None, service: str | None = None) -> None:
        self.carrier = "local"
        self.tracking_no = tracking_no
        self.service = service

    def __repr__(self) -> str:
        return f"ShipmentLocal(tracking_no={self.tracking_no!r}, service={self.service!r})"
