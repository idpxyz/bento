"""Bento Framework - Default Bootstrap Module.

This module provides a minimal FastAPI application template for the Bento framework.

Applications should either:
1. Use this as a starting point for quick prototyping, or
2. Create their own runtime/bootstrap.py in their application directory
   (e.g., applications/{app_name}/runtime/bootstrap.py)

Example:
    ```python
    from runtime.bootstrap import create_app
    
    app = create_app()
    
    # Customize your application
    app.include_router(your_router, prefix="/api")
    ```
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create a minimal Bento Framework application.
    
    This is a framework-level template providing basic FastAPI setup.
    Applications can extend this or create their own bootstrap.
    
    Returns:
        FastAPI: Configured FastAPI application instance
        
    Example:
        ```python
        from runtime.bootstrap import create_app
        
        app = create_app()
        
        @app.on_event("startup")
        async def startup():
            # Your startup logic
            pass
        ```
    """
    app = FastAPI(
        title="Bento Framework",
        description="A minimal DDD framework with hexagonal architecture",
        version="0.1.0",
    )
    
    @app.get("/health", tags=["system"])
    async def health_check():
        """Health check endpoint.
        
        Returns:
            dict: Health status information
        """
        return {
            "status": "healthy",
            "framework": "bento",
            "version": "0.1.0",
        }
    
    @app.get("/", tags=["system"])
    async def root():
        """Root endpoint with framework information.
        
        Returns:
            dict: Framework information
        """
        return {
            "framework": "Bento Framework",
            "description": "Domain-Driven Design with Hexagonal Architecture",
            "docs": "/docs",
            "health": "/health",
        }
    
    return app
