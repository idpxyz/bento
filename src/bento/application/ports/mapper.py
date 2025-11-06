"""Mapper protocols for object transformation.

This module defines the port (interface) for mapping between different object types,
following the Dependency Inversion Principle.

Key Protocols:
- Mapper: One-way mapping
- BidirectionalMapper: Two-way mapping
- CollectionMapper: Collection mapping optimization
"""

from typing import Protocol, TypeVar

# Type variables
S = TypeVar("S")  # Source type
T = TypeVar("T")  # Target type


class Mapper[S, T](Protocol):
    """Protocol for one-way object mapping.

    Defines the interface for transforming objects from source type S to target type T.

    Example:
        ```python
        class UserDTOMapper(Mapper[User, UserDTO]):
            def map(self, user: User) -> UserDTO:
                return UserDTO(
                    id=user.id,
                    name=user.name,
                    email=user.email
                )
        ```
    """

    def map(self, source: S) -> T:
        """Map source object to target object.

        Args:
            source: Source object to map from

        Returns:
            Target object mapped from source
        """
        ...


class BidirectionalMapper(Protocol[S, T]):
    """Protocol for two-way object mapping.

    Defines the interface for transforming objects in both directions:
    - S → T (map)
    - T → S (map_reverse)

    This is particularly useful for Domain ↔ Infrastructure mappings,
    such as AggregateRoot ↔ PersistenceObject.

    Example:
        ```python
        class UserPOMapper(BidirectionalMapper[User, UserPO]):
            def map(self, user: User) -> UserPO:
                return UserPO(id=user.id, name=user.name)

            def map_reverse(self, po: UserPO) -> User:
                return User(id=po.id, name=po.name)
        ```
    """

    def map(self, source: S) -> T:
        """Map source to target (S → T).

        Args:
            source: Source object to map from

        Returns:
            Target object mapped from source
        """
        ...

    def map_reverse(self, target: T) -> S:
        """Map target back to source (T → S).

        Args:
            target: Target object to map back

        Returns:
            Source object mapped from target
        """
        ...


class CollectionMapper(Protocol[S, T]):
    """Protocol for optimized collection mapping.

    Extends basic mapping with batch operations for performance optimization.

    Example:
        ```python
        class UserCollectionMapper(CollectionMapper[User, UserDTO]):
            def map(self, user: User) -> UserDTO:
                return UserDTO(id=user.id, name=user.name)

            def map_list(self, users: list[User]) -> list[UserDTO]:
                # Optimized batch mapping
                return [self.map(u) for u in users]
        ```
    """

    def map(self, source: S) -> T:
        """Map single source to target.

        Args:
            source: Source object to map from

        Returns:
            Target object mapped from source
        """
        ...

    def map_list(self, sources: list[S]) -> list[T]:
        """Map list of sources to targets (batch operation).

        Args:
            sources: List of source objects to map

        Returns:
            List of target objects mapped from sources

        Note:
            Implementations can optimize this for batch processing
            rather than simply iterating over individual maps.
        """
        ...


class BidirectionalCollectionMapper(
    BidirectionalMapper[S, T], CollectionMapper[S, T], Protocol[S, T]
):
    """Protocol combining bidirectional and collection mapping.

    Provides both:
    - Bidirectional mapping (S ↔ T)
    - Batch operations (list[S] ↔ list[T])

    This is the most complete mapping protocol, suitable for repository adapters.

    Example:
        ```python
        class UserPOMapper(BidirectionalCollectionMapper[User, UserPO]):
            def map(self, user: User) -> UserPO:
                return UserPO(id=user.id, name=user.name)

            def map_reverse(self, po: UserPO) -> User:
                return User(id=po.id, name=po.name)

            def map_list(self, users: list[User]) -> list[UserPO]:
                return [self.map(u) for u in users]

            def map_reverse_list(self, pos: list[UserPO]) -> list[User]:
                return [self.map_reverse(p) for p in pos]
        ```
    """

    def map_reverse_list(self, targets: list[T]) -> list[S]:
        """Map list of targets back to sources (batch operation).

        Args:
            targets: List of target objects to map back

        Returns:
            List of source objects mapped from targets
        """
        ...
