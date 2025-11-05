class Container:
    def __init__(self):
        self._container = {}

    def register_repository(self, interface, implementation):
        self._container[interface] = implementation

    def register_query_service(self, service_class, dependencies):
        self._container[service_class] = service_class(**dependencies)


# def configure_option_category_services(container: Container, session: AsyncSession):
#     # 注册仓储
#     repository = OptionCategoryRepository(session)
#     container.register_repository(IOptionCategoryRepository, repository)

#     # 注册查询服务
#     spec_factory = OptionCategorySpecificationFactory()
#     query_service = OptionCategoryQueryService(repository, spec_factory)
#     container.register_query_service(OptionCategoryQueryService, {
#         'repository': repository,
#         'spec_factory': spec_factory
#     })
