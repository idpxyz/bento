from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ContractVersion(Base):
    __tablename__ = "contract_versions"

    id = Column(String(36), primary_key=True)
    contract_id = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    contract_schema = Column("schema", JSON, nullable=False)
    released_by = Column(String(255), nullable=False)
    release_notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=False, default=[])
    status = Column(String(50), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<ContractVersion("
            f"contract_id={self.contract_id}, "
            f"version={self.version}, "
            f"status={self.status})>"
        )


class ContractApproval(Base):
    __tablename__ = "contract_approvals"

    id = Column(String(36), primary_key=True)
    contract_id = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    approvers = Column(JSON, nullable=False, default=[])
    approvals = Column(JSON, nullable=False, default={})
    comments = Column(JSON, nullable=False, default=[])
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<ContractApproval("
            f"contract_id={self.contract_id}, "
            f"version={self.version}, "
            f"status={self.status})>"
        )


class ContractChange(Base):
    __tablename__ = "contract_changes"

    id = Column(String(36), primary_key=True)
    contract_id = Column(String(255), nullable=False, index=True)
    from_version = Column(String(50), nullable=False)
    to_version = Column(String(50), nullable=False)
    changed_by = Column(String(255), nullable=False)
    change_type = Column(String(50), nullable=False)
    changes = Column(JSON, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<ContractChange("
            f"contract_id={self.contract_id}, "
            f"from_version={self.from_version}, "
            f"to_version={self.to_version})>"
        )


class ContractDependency(Base):
    __tablename__ = "contract_dependencies"

    id = Column(String(36), primary_key=True)
    contract_id = Column(String(255), nullable=False, index=True)
    service_id = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    dependency_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    removed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ContractDependency("
            f"contract_id={self.contract_id}, "
            f"service_id={self.service_id}, "
            f"status={self.status})>"
        )
