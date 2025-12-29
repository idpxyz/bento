"""Legacy startup smoke-test kept as a pytest-compatible unit test."""

from contract_governance.api.main import app
from contract_governance.api.router import router
from contract_governance.config.settings import Settings
from contract_governance.models import (
    ContractApproval,
    ContractChange,
    ContractDependency,
    ContractVersion,
)


def test_startup_imports():
    settings = Settings()

    assert app.title == settings.app_name
    assert len(router.routes) > 0

    # Basic attribute checks to ensure models are imported correctly
    assert ContractVersion.__tablename__ == "contract_versions"
    assert ContractApproval.__tablename__ == "contract_approvals"
    assert ContractChange.__tablename__ == "contract_changes"
    assert ContractDependency.__tablename__ == "contract_dependencies"
