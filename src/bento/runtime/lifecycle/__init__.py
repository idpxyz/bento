"""Runtime lifecycle management module.

Handles application startup, shutdown, and contract validation.
"""

from bento.runtime.lifecycle.manager import LifecycleManager
from bento.runtime.lifecycle.shutdown import cleanup_database, shutdown_modules
from bento.runtime.lifecycle.startup import (
    register_modules,
    run_gates,
    setup_database,
)

__all__ = [
    "LifecycleManager",
    "register_modules",
    "run_gates",
    "setup_database",
    "cleanup_database",
    "shutdown_modules",
]
