"""Router Registry - Configurable context registration.

This module implements a scalable plugin pattern for route registration,
allowing bounded contexts to register their routes independently.

For projects with 10+ contexts, this configuration-based approach
reduces code duplication and Git merge conflicts.

Architecture:
- REGISTERED_CONTEXTS: Configuration list of all bounded contexts
- create_api_router(): Dynamically imports and registers routes
- Each context must have: contexts/<name>/interfaces/__init__.py
- Each context must export: register_routes(parent_router: APIRouter)

Benefits:
✅ Scalable - supports 10+ contexts without code duplication
✅ Decoupled - contexts register routes independently
✅ Maintainable - single configuration point for all routes
✅ Extensible - add new contexts without modifying bootstrap
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
# List of all bounded contexts to register
# Each context must have a register_routes() function in its interfaces module
#
# To add a new context:
# 1. Add the context name to this list
# 2. Ensure the context has: contexts/<name>/interfaces/__init__.py
# 3. The interfaces module must export: register_routes(parent_router: APIRouter)
REGISTERED_CONTEXTS = [
    "catalog",  # Product catalog and categories
    "ordering",  # Order management
    "identity",  # User authentication and authorization
]


def create_api_router() -> APIRouter:
    """Create API router with all registered bounded contexts.

    Dynamically imports and registers routes from all contexts listed in
    REGISTERED_CONTEXTS. This approach scales well for 10+ contexts.

    Returns:
        APIRouter: Configured API router with all context routes

    Raises:
        ImportError: If a context's interfaces module is not found
        AttributeError: If a context doesn't have register_routes()
    """
    api_router = APIRouter()

    logger.info(f"Registering {len(REGISTERED_CONTEXTS)} bounded contexts: {', '.join(REGISTERED_CONTEXTS)}")

    for context_name in REGISTERED_CONTEXTS:
        # Dynamically import the context's interfaces module
        module_path = f"contexts.{context_name}.interfaces"

        try:
            module = __import__(module_path, fromlist=["register_routes"])
            register_fn = module.register_routes

            # Register the context's routes
            register_fn(api_router)
            logger.debug(f"✓ Registered routes for context: {context_name}")

        except ImportError as e:
            logger.error(f"✗ Failed to import {module_path}")
            raise ImportError(
                f"Failed to import {module_path}. "
                f"Ensure the context exists and has an interfaces module."
            ) from e
        except AttributeError as e:
            logger.error(f"✗ Context '{context_name}' missing register_routes() function")
            raise AttributeError(
                f"Context '{context_name}' interfaces module must export "
                f"'register_routes(parent_router: APIRouter)' function."
            ) from e

    logger.info(f"✓ Successfully registered all {len(REGISTERED_CONTEXTS)} bounded contexts")

    return api_router
