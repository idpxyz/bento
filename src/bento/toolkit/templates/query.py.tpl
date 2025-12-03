"""{{Action}}{{Name}} Query Handler - CQRS Read Operation"""
from dataclasses import dataclass

from bento.application.ports.uow import UnitOfWork


@dataclass
class {{Action}}{{Name}}Query:
    """{{Action}}{{Name}} Query

    Query represents a request for data.
    Queries do not modify system state.
    """
    # TODO: Add query parameters
    # Example:
    # {{name_lower}}_id: str
    # filters: dict | None = None
    pass


@dataclass
class {{Name}}Response:
    """{{Name}} Response DTO

    Response Data Transfer Object for API/UI layer.
    """
    # TODO: Add response fields
    # Example:
    # id: str
    # name: str
    # email: str
    # created_at: str

    @classmethod
    def from_domain(cls, {{name_lower}}):
        """Convert domain object to response DTO

        Args:
            {{name_lower}}: Domain aggregate root

        Returns:
            Response DTO
        """
        return cls(
            # TODO: Map fields
            # id=str({{name_lower}}.id),
            # name={{name_lower}}.name,
        )


class {{Action}}{{Name}}Handler:
    """{{Action}}{{Name}} Query Handler

    Responsibilities:
    1. Validate query parameters
    2. Fetch data (read-only)
    3. Convert to DTO
    4. Return response

    Follows CQRS pattern - Queries read, Commands write.
    No state changes, no domain events.
    """

    def __init__(self, uow: UnitOfWork):
        """Initialize handler

        Args:
            uow: UnitOfWork for data access
        """
        self.uow = uow

    async def handle(self, query: {{Action}}{{Name}}Query) -> {{Name}}Response:
        """Handle the query

        Args:
            query: The query parameters

        Returns:
            Response DTO

        Raises:
            EntityNotFoundError: If entity not found
        """
        # Get repository (read-only)
        {{name_lower}}_repo = self.uow.repository({{Name}})

        # TODO: Implement query logic
        # Example for Get operation:
        # from contexts.{{context}}.domain.model.{{name_lower}} import {{Name}}
        # from bento.core.ids import ID
        #
        # # Fetch aggregate
        # {{name_lower}} = await {{name_lower}}_repo.get(ID(query.{{name_lower}}_id))
        #
        # if not {{name_lower}}:
        #     raise EntityNotFoundError(f"{{Name}} {query.{{name_lower}}_id} not found")
        #
        # # Convert to DTO
        # return {{Name}}Response.from_domain({{name_lower}})

        # Example for List operation:
        # from contexts.{{context}}.domain.specification import {{Name}}Specification
        #
        # # Build specification
        # spec = {{Name}}Specification.active()
        #
        # # Fetch list
        # {{name_lower}}s = await {{name_lower}}_repo.find_all(spec)
        #
        # # Convert to DTOs
        # return [{{Name}}Response.from_domain({{name_lower}}) for {{name_lower}} in {{name_lower}}s]

        raise NotImplementedError("Please implement query logic")


# ============================================================================
# Usage Example
# ============================================================================
#
# # In API endpoint (interfaces/api/router.py)
# @router.get("/{{name_lower}}s/{{{name_lower}}_id}")
# async def get_{{name_lower}}(
#     {{name_lower}}_id: str,
#     handler: {{Action}}{{Name}}Handler = Depends(get_handler)
# ):
#     query = {{Action}}{{Name}}Query({{name_lower}}_id={{name_lower}}_id)
#     try:
#         return await handler.handle(query)
#     except EntityNotFoundError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#
