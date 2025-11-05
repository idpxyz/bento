"""Bento Framework - Background Jobs.

This module provides background job management for the framework.
Applications should create their own jobs.py with specific tasks.

Example:
    ```python
    # In your application
    from runtime.jobs import run_background_jobs
    
    async def main():
        await run_background_jobs()
    ```
"""

import asyncio


async def run() -> None:
    """Run background jobs (placeholder).
    
    This is a framework-level placeholder. Applications should implement
    their own background jobs in:
    applications/{app_name}/runtime/jobs.py
    
    Example:
        ```python
        async def run():
            # Start outbox publisher
            publisher = OutboxPublisher(...)
            await publisher.start()
            
            # Start other background tasks
            tasks = [
                asyncio.create_task(publish_events()),
                asyncio.create_task(cleanup_expired_data()),
            ]
            await asyncio.gather(*tasks)
        ```
    """
    pass


async def run_background_jobs() -> None:
    """Run all background jobs.
    
    This is a convenience function for running background jobs.
    Applications can override this with their own implementation.
    """
    await run()
