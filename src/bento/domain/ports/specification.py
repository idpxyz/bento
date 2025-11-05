"""Specification Port - Domain layer contract for query specifications.

This module defines the Specification protocol for building complex queries
in a type-safe and composable manner.

The Specification pattern allows you to:
1. Encapsulate query logic in reusable objects
2. Combine specifications using logical operators (AND, OR, NOT)
3. Separate query logic from data access implementation
"""

from typing import Any, Protocol, TypeVar

T = TypeVar("T", contravariant=True)


class Specification[T: Any](Protocol):
    """Specification protocol - defines the contract for query specifications.

    Specifications represent query criteria that can be:
    - Evaluated in-memory (is_satisfied_by)
    - Converted to database queries (to_query_params)
    - Combined using logical operators

    This is a Protocol (not ABC), enabling structural subtyping and better
    type checking without inheritance requirements.

    Type Parameters:
        T: The entity type this specification applies to (contravariant)

    Example:
        ```python
        # Define specifications
        class ActiveUserSpec:
            def is_satisfied_by(self, user: User) -> bool:
                return user.is_active

            def to_query_params(self) -> Dict[str, Any]:
                return {"filters": [{"field": "is_active", "op": "eq", "value": True}]}

        # Combine specifications
        spec = ActiveUserSpec().and_(EmailVerifiedSpec())
        users = await repo.find_by_spec(spec)
        ```
    """

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if a candidate object satisfies this specification.

        This method enables in-memory filtering and validation.

        Args:
            candidate: The object to check

        Returns:
            True if the candidate satisfies the specification, False otherwise

        Example:
            ```python
            spec = ActiveUserSpec()
            if spec.is_satisfied_by(user):
                print("User is active")
            ```
        """
        ...

    def to_query_params(self) -> dict[str, Any]:
        """Convert this specification to query parameters.

        Returns a dictionary that can be used by repositories to build
        database queries. The structure should include:
        - filters: List of filter conditions
        - sorts: List of sorting criteria (optional)
        - pagination: Page and limit (optional)

        Returns:
            Dictionary with query parameters

        Example:
            ```python
            params = spec.to_query_params()
            # {
            #     "filters": [
            #         {"field": "age", "op": "gt", "value": 18},
            #         {"field": "status", "op": "eq", "value": "active"}
            #     ],
            #     "sorts": [{"field": "created_at", "desc": True}],
            #     "page": 1,
            #     "limit": 20
            # }
            ```
        """
        ...

    def and_(self, other: "Specification[T]") -> "Specification[T]":
        """Combine this specification with another using AND logic.

        Args:
            other: Another specification to combine with

        Returns:
            A new specification that is satisfied only if both specifications
            are satisfied

        Example:
            ```python
            active_and_verified = ActiveSpec().and_(VerifiedSpec())
            users = await repo.find_by_spec(active_and_verified)
            ```
        """
        ...

    def or_(self, other: "Specification[T]") -> "Specification[T]":
        """Combine this specification with another using OR logic.

        Args:
            other: Another specification to combine with

        Returns:
            A new specification that is satisfied if either specification
            is satisfied

        Example:
            ```python
            admin_or_moderator = AdminSpec().or_(ModeratorSpec())
            users = await repo.find_by_spec(admin_or_moderator)
            ```
        """
        ...

    def not_(self) -> "Specification[T]":
        """Negate this specification.

        Returns:
            A new specification that is satisfied when this specification
            is NOT satisfied

        Example:
            ```python
            inactive_users = ActiveSpec().not_()
            users = await repo.find_by_spec(inactive_users)
            ```
        """
        ...
