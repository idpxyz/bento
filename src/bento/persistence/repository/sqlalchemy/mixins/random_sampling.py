"""Random Sampling Mixin for BaseRepository.

Provides random sampling operations:
- find_random_po: Find one random entity
- find_random_n_po: Find N random entities
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RandomSamplingMixin:
    """Mixin providing random sampling operations for repositories.

    This mixin assumes the class has:
    - self._po_type: The persistence object type
    - self._session: AsyncSession instance
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession

    async def find_random_po(self, spec: Any | None = None) -> Any | None:
        """Find one random entity.

        Args:
            spec: Optional specification to filter entities

        Returns:
            Random entity, or None if no matches

        Example:
            ```python
            # Get a random product
            random_product = await repo.find_random_po()

            # Get a random active user
            spec = UserSpec().is_active()
            random_user = await repo.find_random_po(spec)
            ```
        """
        stmt = (
            select(self._po_type)  # type: ignore
            .order_by(func.random())
            .limit(1)
        )

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        result = await self._session.execute(stmt)  # type: ignore
        return result.scalar_one_or_none()

    async def find_random_n_po(self, n: int, spec: Any | None = None) -> list[Any]:
        """Find N random entities.

        Args:
            n: Number of random entities to return
            spec: Optional specification to filter entities

        Returns:
            List of up to N random entities

        Example:
            ```python
            # Get 5 random products
            random_products = await repo.find_random_n_po(5)

            # Get 3 random active products
            spec = ProductSpec().is_active()
            random_active = await repo.find_random_n_po(3, spec)
            ```
        """
        if n <= 0:
            return []

        stmt = (
            select(self._po_type)  # type: ignore
            .order_by(func.random())
            .limit(n)
        )

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        result = await self._session.execute(stmt)  # type: ignore
        return list(result.scalars().all())

    async def sample_percentage_po(
        self,
        percentage: float,
        spec: Any | None = None,
        max_count: int | None = None,
    ) -> list[Any]:
        """Sample a percentage of entities randomly.

        Args:
            percentage: Percentage to sample (0.0 to 100.0)
            spec: Optional specification to filter entities
            max_count: Optional maximum number of entities to return

        Returns:
            List of randomly sampled entities

        Example:
            ```python
            # Sample 10% of all products
            sample = await repo.sample_percentage_po(10.0)

            # Sample 5% of active users, max 1000
            spec = UserSpec().is_active()
            sample = await repo.sample_percentage_po(
                5.0, spec, max_count=1000
            )
            ```
        """
        if percentage <= 0:
            return []
        if percentage > 100:
            percentage = 100.0

        # First get total count
        count_stmt = (
            select(func.count()).select_from(self._po_type)  # type: ignore
        )
        if spec:
            count_stmt = spec.apply(  # type: ignore
                count_stmt, self._po_type
            )

        count_result = await self._session.execute(  # type: ignore
            count_stmt
        )
        total_count = count_result.scalar() or 0

        if total_count == 0:
            return []

        # Calculate sample size
        sample_size = int(total_count * (percentage / 100.0))
        if max_count and sample_size > max_count:
            sample_size = max_count

        if sample_size <= 0:
            return []

        # Get random sample
        return await self.find_random_n_po(sample_size, spec)
