from bento.domain.repository import Repository


class DomainService[T]:
    def __init__(self, repository: Repository[T]):
        self.repository = repository
