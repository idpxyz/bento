import importlib

import pytest

MODULES = [
    # infrastructure small modules
    "bento.infrastructure.cache",
    "bento.infrastructure.emailer",
    "bento.infrastructure.locker",
    "bento.infrastructure.search",
    "bento.infrastructure.storage",
    "bento.infrastructure.tx",
    # repository adapters
    "bento.infrastructure.repository",
    "bento.infrastructure.repository.adapter",
    "bento.infrastructure.repository.simple_adapter",
    # messaging
    "bento.messaging.codec",
    "bento.messaging.codec.base",
    "bento.messaging.codec.json",
    "bento.messaging.envelope",
    "bento.messaging.event_bus",
    "bento.messaging.outbox",
    "bento.messaging.topics",
    # interfaces
    "bento.interfaces.http",
    "bento.interfaces.scheduler",
    "bento.interfaces.grpc",
    "bento.interfaces.graphql",
    # persistence wrapper modules
    "bento.persistence.repository",
]


@pytest.mark.parametrize("mod_name", MODULES)
def test_import_module(mod_name: str):
    mod = importlib.import_module(mod_name)
    assert mod is not None
