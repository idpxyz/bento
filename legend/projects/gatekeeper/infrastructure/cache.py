# infrastructure/cache.py
from cachetools import TTLCache


def get_cache(maxsize=5000, ttl=5):
    return TTLCache(maxsize=maxsize, ttl=ttl)
