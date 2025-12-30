# app/bc/shipment/infrastructure/adapters/http/handlers.py
@inject
async def create_shipment(
    request: Request,
    command_bus: CommandBus = Depends(provide_command_bus)
) -> JSONResponse:
    try:
        # 1. 请求验证（自动由FastAPI处理）
        command = CreateShipmentCommand(**await request.json())
        
        # 2. 设置追踪上下文
        command.metadata.correlation_id = request.headers.get("x-request-id")
        command.metadata.tenant_id = request.state.tenant_id
        
        # 3. 发送命令
        result = await command_bus.execute(command)
        return JSONResponse(
            status_code=201,
            content=result,
            headers={"Location": f"/v1/shipments/{result['id']}"}
        )
    except DomainError as e:
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
