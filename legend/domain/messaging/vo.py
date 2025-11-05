from dataclasses import dataclass


@dataclass(frozen=True)
class MessageId:
    value: str

@dataclass(frozen=True)
class TopicName:
    value: str
