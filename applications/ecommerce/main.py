"""E-commerce application entry point.

Run this to start the e-commerce API server.

Example:
    ```bash
    # Development mode
    uvicorn applications.ecommerce.main:app --reload --port 8000

    # Production mode
    uvicorn applications.ecommerce.main:app --host 0.0.0.0 --port 8000
    ```
"""

from applications.ecommerce.runtime.bootstrap import create_app

# Create FastAPI application
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # Run application
    uvicorn.run(
        "applications.ecommerce.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload in development
    )
