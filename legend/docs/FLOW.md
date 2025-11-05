::: mermaid
flowchart TD
    subgraph Presentation["Presentation<br/>(api)"]
        APIRouters[/"routers"/]
        APISchemas[/"schemas"/]
        APIDeps[/"dependencies"/]
    end

    subgraph Application["Application<br/>(use-case orchestration)"]
        Commands(["commands.py"])
        CommandHandlers(["command_handlers.py"])
        Queries(["queries.py"])
        QueryHandlers(["query_handlers.py"])
        UoW["Unit-of-Work<br/>uow.py"]
    end

    subgraph Domain["Domain<br/>(business model)"]
        Model["model/↙<br/>• RoutePlan<br/>• Driver"]
        RepoIntf["repository/↙<br/>• RoutePlanRepository"]
        Events["event/↙<br/>• events.py<br/>• handlers.py"]
        Policy["policy/"]
        DExceptions["exception.py"]
    end

    subgraph Infrastructure["Infrastructure<br/>(technical glue)"]
        subgraph Persistence
            ORMPO["po/ (SQLAlchemy PO)"]
            Mappings["mappings.py"]
            BaseRepo["repositories/base_repo.py"]
            RepoImpl["repositories/route_plan_repo.py"]
            UoWImpl["uow_impl.py"]
            Migrations["migrations/ (Alembic)"]
        end
        Messaging["messaging/↙<br/>• pulsar_producer.py<br/>• pulsar_consumer.py"]
        Cache["cache/↙<br/>• redis_client.py"]
        Config["config/"]
        Logging["logging/"]
        Interceptors["interceptors/↙<br/>• soft_delete.py<br/>• tenant_filter.py"]
    end

    subgraph Shared["Shared Kernel"]
        VOs["value_objects.py"]
        Typing["typing.py"]
        Utils["utils/"]
    end

    Tests["tests/↙ unit • integration • e2e"]

    %% Dependency arrows (one-way)
    APIRouters -->|DTO→Cmd/Query| Commands
    APIRouters --> Queries
    CommandHandlers --> UoW
    QueryHandlers --> RepoIntf
    UoW -->RepoIntf
    RepoIntf --> RepoImpl
    RepoImpl --> ORMPO
    RepoImpl --> UoWImpl
    UoWImpl --> ORMPO
    Model --> Events
    CommandHandlers --> Model
    Interceptors --> BaseRepo
    BaseRepo --> RepoImpl
    Shared --> Domain
    Shared --> Application
    Shared --> Infrastructure
    Application --> Domain
    Presentation --> Application
    Infrastructure --> Application
    Tests --covers--> Presentation
    Tests --covers--> Application
    Tests --covers--> Domain
```