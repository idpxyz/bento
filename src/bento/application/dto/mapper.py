"""DTO Mapper Protocol - Clean Architecture for Domain to DTO conversion.

This module provides the foundation for SOLID and DDD-compliant DTO conversion.
Separates data definition (DTO) from conversion logic (Mapper).
"""

from abc import ABC, abstractmethod
from typing import Generic, Protocol, TypeVar

Domain = TypeVar("Domain")  # Domain object (AggregateRoot/Entity)
DTO = TypeVar("DTO")  # Data Transfer Object


class DTOMapper(Protocol[Domain, DTO]):
    """Protocol for Domain → DTO conversion (Port in Hexagonal Architecture).

    Follows SOLID principles:
    - SRP: Single responsibility - only conversion
    - OCP: Open for extension (new mappers), closed for modification
    - LSP: Subtypes can replace base mapper
    - ISP: Only conversion interface, no data definition
    - DIP: Depends on abstraction (Protocol), not concrete classes

    DDD Compliance:
    - Clear separation of concerns
    - Application layer converts Domain to DTO
    - No business logic in conversion
    """

    def to_dto(self, domain: Domain) -> DTO:
        """Convert single domain object to DTO.

        Args:
            domain: Domain object (AggregateRoot or Entity)

        Returns:
            DTO with validated data
        """
        ...

    def to_dto_list(self, domains: list[Domain]) -> list[DTO]:
        """Convert list of domain objects to DTOs.

        Args:
            domains: List of domain objects

        Returns:
            List of DTOs
        """
        ...

    def to_dto_optional(self, domain: Domain | None) -> DTO | None:
        """Convert optional domain object to DTO.

        Args:
            domain: Optional domain object

        Returns:
            DTO if domain exists, None otherwise
        """
        ...


class BaseDTOMapper(Generic[Domain, DTO], ABC):
    """Base implementation for DTO Mappers (Adapter in Hexagonal Architecture).

    Provides default implementations for list and optional conversions.
    Concrete mappers only need to implement to_dto() method.

    Example:
        ```python
        class ProductDTOMapper(BaseDTOMapper[Product, ProductDTO]):
            def to_dto(self, product: Product) -> ProductDTO:
                return ProductDTO(
                    id=str(product.id),
                    name=product.name,
                    price=product.price,
                    # Only conversion logic here - clean separation!
                )
        ```
    """

    @abstractmethod
    def to_dto(self, domain: Domain) -> DTO:
        """Convert single domain object to DTO.

        Must be implemented by concrete mappers.
        """
        pass

    def to_dto_list(self, domains: list[Domain]) -> list[DTO]:
        """Default implementation for list conversion."""
        return [self.to_dto(domain) for domain in domains]

    def to_dto_optional(self, domain: Domain | None) -> DTO | None:
        """Default implementation for optional conversion."""
        return self.to_dto(domain) if domain is not None else None


# Type aliases for convenience
DomainToDTOMapper = DTOMapper
QueryResultMapper = DTOMapper  # For query results

__all__ = [
    "DTOMapper",
    "BaseDTOMapper",
    "DomainToDTOMapper",
    "QueryResultMapper",
    "Domain",
    "DTO",
]
