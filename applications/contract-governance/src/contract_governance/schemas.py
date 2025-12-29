from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ContractVersionCreate(BaseModel):
    contract_id: str
    version: str
    contract_schema: dict[str, Any]
    released_by: str
    release_notes: str = ""


class ContractVersionUpdate(BaseModel):
    release_notes: str | None = None
    tags: list[str] | None = None


class ContractVersionResponse(BaseModel):
    id: str
    contract_id: str
    version: str
    contract_schema: dict[str, Any]
    released_by: str
    release_notes: str
    tags: list[str]
    status: str
    created_at: datetime
    released_at: datetime | None

    class Config:
        from_attributes = True


class ContractApprovalCreate(BaseModel):
    contract_id: str
    version: str
    approvers: list[str]


class ContractApprovalResponse(BaseModel):
    id: str
    contract_id: str
    version: str
    status: str
    approvers: list[str]
    approvals: dict[str, Any]
    comments: list[str]
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class ContractChangeCreate(BaseModel):
    contract_id: str
    from_version: str
    to_version: str
    changed_by: str
    change_type: str
    changes: dict[str, Any]
    reason: str = ""


class ContractChangeResponse(BaseModel):
    id: str
    contract_id: str
    from_version: str
    to_version: str
    changed_by: str
    change_type: str
    changes: dict[str, Any]
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContractDependencyCreate(BaseModel):
    contract_id: str
    service_id: str
    version: str
    dependency_type: str


class ContractDependencyResponse(BaseModel):
    id: str
    contract_id: str
    service_id: str
    version: str
    dependency_type: str
    status: str
    added_at: datetime
    removed_at: datetime | None

    class Config:
        from_attributes = True
