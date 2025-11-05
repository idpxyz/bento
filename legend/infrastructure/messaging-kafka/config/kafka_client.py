from typing import Dict, Optional

from confluent_kafka import Consumer as ConfluentConsumer
from confluent_kafka import Producer as ConfluentProducer
from confluent_kafka.schema_registry import SchemaRegistryClient

from idp.framework.infrastructure.messaging.config.settings import get_settings


def get_kafka_config() -> Dict[str, str]:
    """
    Get Kafka configuration for producers and consumers.

    Returns:
        Dict[str, str]: Kafka configuration dictionary
    """
    settings = get_settings()
    config = {
        "bootstrap.servers": ",".join(settings.kafka.bootstrap_servers),
        "security.protocol": settings.kafka.security_protocol,
    }

    # Add SASL configuration if needed
    if settings.kafka.sasl_mechanism:
        config["sasl.mechanism"] = settings.kafka.sasl_mechanism

    if settings.kafka.sasl_username and settings.kafka.sasl_password:
        config["sasl.username"] = settings.kafka.sasl_username
        config["sasl.password"] = settings.kafka.sasl_password

    return config


def create_producer(client_id: Optional[str] = None) -> ConfluentProducer:
    """
    Create a Kafka producer with the configured settings.

    Args:
        client_id (Optional[str]): Optional client ID override

    Returns:
        ConfluentProducer: Configured Kafka producer
    """
    settings = get_settings()
    config = get_kafka_config()

    # Add producer-specific configuration
    producer_config = {
        **config,
        "client.id": client_id
        or f"{settings.producer.client_id_prefix}-{id(client_id)}",
        "acks": settings.producer.acks,
        "compression.type": settings.producer.compression_type,
        "batch.size": settings.producer.batch_size,
        "linger.ms": settings.producer.linger_ms,
        "retries": settings.producer.retries,
        "max.in.flight.requests.per.connection": settings.producer.max_in_flight,
        "enable.idempotence": settings.producer.idempotence,
        "delivery.timeout.ms": settings.producer.delivery_timeout_ms,
    }

    return ConfluentProducer(producer_config)


def create_consumer(
    group_id: str, client_id: Optional[str] = None
) -> ConfluentConsumer:
    """
    Create a Kafka consumer with the configured settings.

    Args:
        group_id (str): Consumer group ID
        client_id (Optional[str]): Optional client ID override

    Returns:
        ConfluentConsumer: Configured Kafka consumer
    """
    settings = get_settings()
    config = get_kafka_config()

    # Add consumer-specific configuration
    consumer_config = {
        **config,
        "group.id": f"{settings.consumer.group_id_prefix}-{group_id}",
        "client.id": client_id
        or f"{settings.consumer.group_id_prefix}-{group_id}-{id(client_id)}",
        "auto.offset.reset": settings.consumer.auto_offset_reset,
        "enable.auto.commit": settings.consumer.enable_auto_commit,
        "max.poll.interval.ms": settings.consumer.max_poll_interval_ms,
        "max.poll.records": settings.consumer.max_poll_records,
        "session.timeout.ms": settings.consumer.session_timeout_ms,
        "heartbeat.interval.ms": settings.consumer.heartbeat_interval_ms,
        "isolation.level": settings.consumer.isolation_level,
    }

    return ConfluentConsumer(consumer_config)


def create_schema_registry_client() -> SchemaRegistryClient:
    """
    Create a Schema Registry client with the configured settings.

    Returns:
        SchemaRegistryClient: Configured Schema Registry client
    """
    settings = get_settings()

    schema_registry_config = {
        "url": settings.schema_registry.url,
    }

    # Add authentication if needed
    if settings.schema_registry.auth_user and settings.schema_registry.auth_password:
        schema_registry_config["basic.auth.user.info"] = (
            f"{settings.schema_registry.auth_user}:{settings.schema_registry.auth_password}"
        )

    return SchemaRegistryClient(schema_registry_config)
