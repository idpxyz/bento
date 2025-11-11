"""Integration tests for Specification with SQLAlchemy."""

import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

from bento.infrastructure.database import (
    DatabaseConfig,
    create_async_engine_from_config,
    create_async_session_factory,
)
from bento.persistence.specification import (
    AggregateSpecificationBuilder,
    EntitySpecificationBuilder,
    FilterOperator,
    SortDirection,
    SpecificationBuilder,
)
from bento.persistence.specification.criteria import (
    And,
    BetweenCriterion,
    ContainsCriterion,
    EqualsCriterion,
    GreaterEqualCriterion,
    InCriterion,
    IsNullCriterion,
    LikeCriterion,
    Or,
    StartsWithCriterion,
    TodayCriterion,
)

pytestmark = pytest.mark.asyncio

Base = declarative_base()


class SampleEntity(Base):
    """Sample entity for integration tests."""

    __tablename__ = "sample_entity"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    age: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[date] = mapped_column()
    deleted_at: Mapped[date | None] = mapped_column(nullable=True)


class SampleAggregate(Base):
    """Sample aggregate for integration tests."""

    __tablename__ = "sample_aggregate"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column()


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session."""
    # Create a temporary database file
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = db_file.name
    db_file.close()

    try:
        config = DatabaseConfig(
            url=f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )

        engine = create_async_engine_from_config(config)
        session_factory = create_async_session_factory(engine)

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create session
        async with session_factory() as session:
            yield session

        # Cleanup
        await engine.dispose()
    finally:
        # Remove temp file
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def populated_db(db_session: AsyncSession):
    """Populate database with test data."""
    # Add entities
    today = date.today()
    yesterday = today - timedelta(days=1)

    entities = [
        SampleEntity(
            id=1, name="Alice", status="active", age=25, created_at=today, deleted_at=None
        ),
        SampleEntity(
            id=2, name="Bob", status="inactive", age=30, created_at=yesterday, deleted_at=None
        ),
        SampleEntity(
            id=3, name="Charlie", status="active", age=35, created_at=yesterday, deleted_at=None
        ),
        SampleEntity(
            id=4, name="David", status="pending", age=None, created_at=today, deleted_at=today
        ),
        SampleEntity(
            id=5, name="Alice Smith", status="active", age=28, created_at=today, deleted_at=None
        ),
    ]

    for entity in entities:
        db_session.add(entity)

    # Add aggregates
    now = datetime.now()
    aggregates = [
        SampleAggregate(id=1, name="Aggregate1", version=1, created_at=now),
        SampleAggregate(id=2, name="Aggregate2", version=2, created_at=now - timedelta(hours=1)),
        SampleAggregate(id=3, name="Aggregate3", version=1, created_at=now - timedelta(days=1)),
    ]

    for aggregate in aggregates:
        db_session.add(aggregate)

    await db_session.commit()
    return db_session


class TestSpecificationBuilderIntegration:
    """Integration tests for SpecificationBuilder with SQLAlchemy."""

    async def test_simple_filter(self, populated_db: AsyncSession):
        """Test simple filter with SQLAlchemy."""
        spec = SpecificationBuilder().where("status", "=", "active").build()

        # In real implementation, spec would be applied to the query
        # For now, just test that spec was built correctly
        assert len(spec.filters) == 1
        assert spec.filters[0].field == "status"
        assert spec.filters[0].operator == FilterOperator.EQUALS
        assert spec.filters[0].value == "active"

    async def test_multiple_filters(self, populated_db: AsyncSession):
        """Test multiple filters."""
        spec = SpecificationBuilder().where("status", "=", "active").where("age", ">=", 25).build()

        assert len(spec.filters) == 2

    async def test_sorting(self, populated_db: AsyncSession):
        """Test sorting."""
        spec = (
            SpecificationBuilder()
            .order_by("name", SortDirection.ASC)
            .order_by("age", SortDirection.DESC)
            .build()
        )

        assert len(spec.sorts) == 2
        assert spec.sorts[0].field == "name"
        assert spec.sorts[0].direction == SortDirection.ASC

    async def test_pagination(self, populated_db: AsyncSession):
        """Test pagination."""
        spec = SpecificationBuilder().paginate(page=2, size=10).build()

        assert spec.page is not None
        # Note: PageParams might not be created if not used properly
        # The builder should create PageParams internally

    async def test_limit_offset(self, populated_db: AsyncSession):
        """Test limit and offset."""
        spec = SpecificationBuilder().paginate(page=1, size=5).build()

        assert spec.page is not None
        # Note: The builder should handle limit/offset internally


class TestEntitySpecificationIntegration:
    """Integration tests for EntitySpecificationBuilder."""

    async def test_default_excludes_deleted(self, populated_db: AsyncSession):
        """Test that EntitySpecificationBuilder excludes soft-deleted by default."""
        spec = EntitySpecificationBuilder().build()

        # Default behavior: exclude soft-deleted entities (deleted_at IS NULL)
        assert len(spec.filters) == 1
        assert spec.filters[0].field == "deleted_at"
        assert spec.filters[0].operator == FilterOperator.IS_NULL

    async def test_only_deleted(self, populated_db: AsyncSession):
        """Test querying only soft-deleted entities."""
        spec = EntitySpecificationBuilder().include_deleted().only_deleted().build()

        # Should filter only soft-deleted entities using deleted_at timestamp
        # NOT NULL = has been deleted
        assert len(spec.filters) == 1
        assert spec.filters[0].field == "deleted_at"
        assert spec.filters[0].operator == FilterOperator.IS_NOT_NULL

    async def test_created_after(self, populated_db: AsyncSession):
        """Test created_after filter."""
        cutoff = datetime.now() - timedelta(hours=2)
        spec = EntitySpecificationBuilder().created_after(cutoff).build()

        # Has default deleted_at filter + created_after
        assert len(spec.filters) == 2
        assert spec.filters[0].field == "deleted_at"  # Default filter
        assert spec.filters[1].field == "created_at"
        assert spec.filters[1].operator == FilterOperator.GREATER_EQUAL

    async def test_created_before(self, populated_db: AsyncSession):
        """Test created_before filter."""
        cutoff = datetime.now()
        spec = EntitySpecificationBuilder().created_before(cutoff).build()

        # Has default deleted_at filter + created_before
        assert len(spec.filters) == 2
        assert spec.filters[0].field == "deleted_at"  # Default filter
        assert spec.filters[1].field == "created_at"
        assert spec.filters[1].operator == FilterOperator.LESS_EQUAL


class TestAggregateSpecificationIntegration:
    """Integration tests for AggregateSpecificationBuilder."""

    async def test_with_version(self, populated_db: AsyncSession):
        """Test with_version filter."""
        spec = AggregateSpecificationBuilder().with_version(2).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "version"
        assert spec.filters[0].operator == FilterOperator.EQUALS
        assert spec.filters[0].value == 2

    async def test_with_minimum_version(self, populated_db: AsyncSession):
        """Test with_minimum_version filter."""
        spec = AggregateSpecificationBuilder().with_minimum_version(1).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "version"
        assert spec.filters[0].operator == FilterOperator.GREATER_EQUAL

    async def test_by_aggregate_id(self, populated_db: AsyncSession):
        """Test by_aggregate_id filter."""
        spec = AggregateSpecificationBuilder().by_aggregate_id(123).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "id"
        assert spec.filters[0].operator == FilterOperator.EQUALS


class TestCriteriaIntegration:
    """Integration tests for Criteria with SQLAlchemy."""

    async def test_equals_criterion(self, populated_db: AsyncSession):
        """Test EqualsCriterion."""
        criterion = EqualsCriterion("status", "active")

        # Build a basic spec
        spec = SpecificationBuilder()
        spec._criteria.append(criterion)
        built_spec = spec.build()

        assert len(built_spec.filters) == 1
        assert built_spec.filters[0].value == "active"

    async def test_between_criterion(self, populated_db: AsyncSession):
        """Test BetweenCriterion."""
        criterion = BetweenCriterion("age", 25, 35)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.BETWEEN
        assert filter.value["start"] == 25
        assert filter.value["end"] == 35

    async def test_in_criterion(self, populated_db: AsyncSession):
        """Test InCriterion."""
        criterion = InCriterion("status", ["active", "pending"])
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.IN
        assert filter.value == ["active", "pending"]

    async def test_like_criterion(self, populated_db: AsyncSession):
        """Test LikeCriterion."""
        criterion = LikeCriterion("name", "Alice%")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.LIKE
        assert filter.value == "Alice%"

    async def test_contains_criterion(self, populated_db: AsyncSession):
        """Test ContainsCriterion."""
        criterion = ContainsCriterion("name", "Smith")
        filter = criterion.to_filter()

        # ContainsCriterion wraps with %
        assert filter.operator == FilterOperator.LIKE
        assert filter.value == "%Smith%"

    async def test_starts_with_criterion(self, populated_db: AsyncSession):
        """Test StartsWithCriterion."""
        criterion = StartsWithCriterion("name", "Ali")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.LIKE
        assert filter.value == "Ali%"

    async def test_is_null_criterion(self, populated_db: AsyncSession):
        """Test IsNullCriterion."""
        criterion = IsNullCriterion("deleted_at")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.IS_NULL
        assert filter.value is None

    async def test_today_criterion(self, populated_db: AsyncSession):
        """Test TodayCriterion."""
        criterion = TodayCriterion("created_at")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.EQUALS
        assert filter.value == date.today()


class TestLogicalCombinators:
    """Integration tests for logical combinators (AND, OR)."""

    async def test_and_combinator(self, populated_db: AsyncSession):
        """Test And combinator."""
        c1 = EqualsCriterion("status", "active")
        c2 = GreaterEqualCriterion("age", 25)
        combined = And(c1, c2)

        # And should combine multiple criteria
        assert combined is not None

    async def test_or_combinator(self, populated_db: AsyncSession):
        """Test Or combinator."""
        c1 = EqualsCriterion("status", "active")
        c2 = EqualsCriterion("status", "pending")
        combined = Or(c1, c2)

        filter_group = combined.to_filter_group()
        assert len(filter_group.filters) == 2

    async def test_complex_and_or(self, populated_db: AsyncSession):
        """Test complex AND/OR combination."""
        # (status = active OR status = pending) AND age >= 25
        status_filter = Or(
            EqualsCriterion("status", "active"), EqualsCriterion("status", "pending")
        )
        age_filter = GreaterEqualCriterion("age", 25)

        combined = And(status_filter, age_filter)
        assert combined is not None


class TestComplexQueries:
    """Integration tests for complex query scenarios."""

    async def test_active_users_with_pagination(self, populated_db: AsyncSession):
        """Test active users query with pagination."""
        spec = (
            EntitySpecificationBuilder()
            .where("status", "=", "active")
            # Default behavior already excludes soft-deleted entities
            .order_by("name", SortDirection.ASC)
            .paginate(page=1, size=10)
            .build()
        )

        assert len(spec.filters) == 2  # status + not_deleted
        assert len(spec.sorts) == 1
        assert spec.page is not None

    async def test_age_range_with_sorting(self, populated_db: AsyncSession):
        """Test age range query with sorting."""
        spec = (
            SpecificationBuilder()
            .where("age", ">=", 25)
            .where("age", "<", 40)
            .order_by("age", SortDirection.DESC)
            .order_by("name", SortDirection.ASC)
            .build()
        )

        assert len(spec.filters) == 2
        assert len(spec.sorts) == 2

    async def test_search_with_multiple_conditions(self, populated_db: AsyncSession):
        """Test search with multiple conditions."""
        spec = (
            EntitySpecificationBuilder()
            .where("status", "in", ["active", "pending"])
            # Default behavior already excludes soft-deleted entities
            .created_after(datetime.now() - timedelta(days=7))
            .order_by("created_at", SortDirection.DESC)
            .paginate(page=1, size=20)
            .build()
        )

        assert len(spec.filters) >= 3  # status IN, not_deleted, created_after
        assert len(spec.sorts) == 1
        assert spec.page is not None


class TestEdgeCases:
    """Integration tests for edge cases."""

    async def test_empty_specification(self, populated_db: AsyncSession):
        """Test empty specification (no filters)."""
        spec = SpecificationBuilder().build()

        assert len(spec.filters) == 0
        assert len(spec.sorts) == 0
        assert spec.page is None

    async def test_null_value_handling(self, populated_db: AsyncSession):
        """Test handling of null values."""
        # Use space-separated operator (as defined in operator_map)
        spec = SpecificationBuilder().where("age", "is null", None).build()

        # Should handle null checks
        assert len(spec.filters) == 1

    async def test_large_in_list(self, populated_db: AsyncSession):
        """Test IN operator with large list."""
        large_list = list(range(1000))
        spec = SpecificationBuilder().where("id", "in", large_list).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].operator == FilterOperator.IN
        assert len(spec.filters[0].value) == 1000

    async def test_chaining_same_field(self, populated_db: AsyncSession):
        """Test multiple filters on the same field."""
        spec = SpecificationBuilder().where("age", ">=", 25).where("age", "<", 65).build()

        # Both filters should be present
        assert len(spec.filters) == 2
        assert all(f.field == "age" for f in spec.filters)
