"""Initialize the database with tables."""

from sqlalchemy import create_engine

from contract_governance.config.settings import Settings
from contract_governance.models import Base

settings = Settings()


def init_db():
    """Create all tables in the database."""
    engine = create_engine(settings.database_url, echo=True)
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")


if __name__ == "__main__":
    init_db()
