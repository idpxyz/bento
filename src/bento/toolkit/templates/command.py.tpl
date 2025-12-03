"""{{Action}}{{Name}} Command Handler - CQRS Write Operation"""
from dataclasses import dataclass

from bento.application import ApplicationService, ApplicationServiceResult
from bento.application.ports.uow import UnitOfWork


@dataclass
class {{Action}}{{Name}}Command:
    """{{Action}}{{Name}} Command

    Command represents user intent and contains all data needed for the operation.
    Commands modify system state and trigger domain events.
    """
    # TODO: Add command fields
    # Example:
    # name: str
    # email: str
    # price: float
    pass


class {{Action}}{{Name}}Handler(ApplicationService):
    """{{Action}}{{Name}} Command Handler

    Responsibilities:
    1. Validate command
    2. Load domain objects
    3. Execute business logic
    4. Persist changes
    5. Publish domain events (automatic)

    Follows CQRS pattern - Commands write, Queries read.
    """

    def __init__(self, uow: UnitOfWork):
        """Initialize handler

        Args:
            uow: UnitOfWork for transaction management
        """
        super().__init__(uow)

    async def handle(self, command: {{Action}}{{Name}}Command) -> ApplicationServiceResult[str]:
        """Handle the command

        Args:
            command: The command to execute

        Returns:
            ApplicationServiceResult with entity ID on success

        Raises:
            DomainException: If business rules are violated
        """
        # Get repository
        {{name_lower}}_repo = self.uow.repository({{Name}})

        # TODO: Implement business logic
        # Example for Create operation:
        # from contexts.{{context}}.domain.model.{{name_lower}} import {{Name}}
        #
        # # Create aggregate
        # {{name_lower}} = {{Name}}.create(
        #     name=command.name,
        #     email=command.email,
        # )
        #
        # # Save aggregate
        # await {{name_lower}}_repo.save({{name_lower}})
        #
        # # Return entity ID (framework auto-commits and publishes events)
        # return self.success(str({{name_lower}}.id))

        raise NotImplementedError("Please implement business logic")


# ============================================================================
# Usage Example
# ============================================================================
#
# # In API endpoint (interfaces/api/router.py)
# @router.post("/{{name_lower}}s", status_code=201)
# async def {{action_lower}}_{{name_lower}}(
#     command: {{Action}}{{Name}}Command,
#     handler: {{Action}}{{Name}}Handler = Depends(get_handler)
# ):
#     result = await handler.execute(command)
#     if result.is_success:
#         return {"id": result.value}
#     else:
#         raise HTTPException(status_code=400, detail=result.error)
#
