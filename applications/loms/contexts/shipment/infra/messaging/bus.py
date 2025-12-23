class MessageBus:
    async def publish(self, topic: str, envelope: dict):
        # Replace with Pulsar/Kafka adapter; keep as minimal logger for skeleton
        print(f"[BUS] publish topic={topic} event_type={envelope.get('event_type')} event_id={envelope.get('event_id')}")
