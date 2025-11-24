import os

import pytest

from bento.adapters.cache import CacheBackend, CacheConfig, SerializerType


def _clear_cache_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ.keys()):
        if key.startswith("CACHE_") or key in {"REDIS_URL"}:
            monkeypatch.delenv(key, raising=False)


def test_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no CACHE_* env vars are set, defaults should be used."""
    _clear_cache_env(monkeypatch)

    config = CacheConfig.from_env()

    assert config.backend is CacheBackend.MEMORY
    assert config.prefix == ""
    assert config.ttl is None
    assert config.max_size == 10000
    assert config.redis_url is None
    assert config.serializer is SerializerType.JSON
    assert config.enable_stats is True
    assert config.enable_breakdown_protection is True


def test_from_env_valid_custom_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom but valid env values should be parsed correctly."""
    _clear_cache_env(monkeypatch)

    monkeypatch.setenv("CACHE_BACKEND", "redis")
    monkeypatch.setenv("CACHE_PREFIX", "myshop:")
    monkeypatch.setenv("CACHE_TTL", "300")
    monkeypatch.setenv("CACHE_MAX_SIZE", "5000")
    monkeypatch.setenv("CACHE_SERIALIZER", "pickle")
    monkeypatch.setenv("CACHE_ENABLE_STATS", "false")
    monkeypatch.setenv("CACHE_ENABLE_BREAKDOWN_PROTECTION", "0")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    config = CacheConfig.from_env()

    assert config.backend is CacheBackend.REDIS
    assert config.prefix == "myshop:"
    assert config.ttl == 300
    assert config.max_size == 5000
    assert config.redis_url == "redis://localhost:6379/0"
    assert config.serializer is SerializerType.PICKLE
    assert config.enable_stats is False
    assert config.enable_breakdown_protection is False


@pytest.mark.parametrize("value", ["redisx", "", "MEMORY-"])
def test_from_env_invalid_backend_raises(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """Invalid CACHE_BACKEND values should raise a clear error."""
    _clear_cache_env(monkeypatch)
    monkeypatch.setenv("CACHE_BACKEND", value)

    with pytest.raises(ValueError) as exc:
        CacheConfig.from_env()

    assert "CACHE_BACKEND" in str(exc.value)


@pytest.mark.parametrize(
    "name,value",
    [
        ("CACHE_TTL", "abc"),
        ("CACHE_MAX_SIZE", "1.5"),
    ],
)
def test_from_env_invalid_int_raises(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    """Invalid integer envs should raise contextual errors."""
    _clear_cache_env(monkeypatch)
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError) as exc:
        CacheConfig.from_env()

    # Error message should contain the env name
    assert name in str(exc.value)


@pytest.mark.parametrize("value", ["on", "off", "maybe"])
def test_from_env_invalid_bool_raises(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """Invalid boolean envs should raise contextual errors."""
    _clear_cache_env(monkeypatch)
    monkeypatch.setenv("CACHE_ENABLE_STATS", value)

    with pytest.raises(ValueError) as exc:
        CacheConfig.from_env()

    assert "CACHE_ENABLE_STATS" in str(exc.value)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("no", False),
    ],
)
def test_from_env_bool_variants(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    """Common boolean representations should be accepted."""
    _clear_cache_env(monkeypatch)
    monkeypatch.setenv("CACHE_ENABLE_STATS", value)

    config = CacheConfig.from_env()

    assert config.enable_stats is expected
