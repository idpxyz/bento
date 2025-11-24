"""Application configuration package.

Centralizes all configuration modules including settings, warmup, etc.
"""

# Import and export settings from settings.py
from config.settings import settings

__all__ = ["settings"]
