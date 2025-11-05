::: mermaid
sequenceDiagram
    participant API as FastAPI Router
    participant AppSvc as CommandHandler
    participant UoW as SqlAlchemyUoW
    participant Repo as RoutePlanRepositoryImpl
    participant DB as PostgreSQL

    API->>AppSvc: handle(CreateRoutePlanCmd)
    AppSvc->>UoW: __aenter__()
    AppSvc->>Repo: save(routePlan)
    Repo->>UoW: session.add(po)
    Note right of UoW: 聚合变更 & 域事件 收集
    AppSvc->>UoW: commit()
    UoW->>DB: BEGIN / INSERT / COMMIT
    UoW->>Pulsar: 发布 RoutePlanCreated
    UoW->>AppSvc: 返回
    API-->>Client: 201 Created
