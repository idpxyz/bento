from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from contract_governance.config.settings import Settings
from contract_governance.contexts.builders import (
    build_change_history,
    build_compatibility_matrix,
    build_dependency_graph,
    build_workflow,
)
from contract_governance.models import (
    Base,
    ContractApproval,
    ContractChange,
    ContractDependency,
    ContractVersion,
)
from contract_governance.schemas import (
    ContractApprovalCreate,
    ContractApprovalResponse,
    ContractChangeCreate,
    ContractChangeResponse,
    ContractDependencyCreate,
    ContractDependencyResponse,
    ContractVersionCreate,
    ContractVersionResponse,
)

settings = Settings()

engine = create_engine(settings.database_url, echo=settings.database_echo)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/api/v1", tags=["contract-governance"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _approval_to_mapping(approval: ContractApproval) -> dict:
    return {
        "status": approval.status,
        "approvers": approval.approvers or [],
        "comments": approval.comments or [],
    }


def _change_to_mapping(change: ContractChange) -> dict:
    return {
        "id": change.id,
        "contract_id": change.contract_id,
        "from_version": change.from_version,
        "to_version": change.to_version,
        "change_type": change.change_type,
        "changed_by": change.changed_by,
        "reason": change.reason or "",
        "created_at": change.created_at,
    }


def _dependency_to_mapping(dependency: ContractDependency) -> dict:
    return {
        "contract_id": dependency.contract_id,
        "service_id": dependency.service_id,
        "version": dependency.version,
        "dependency_type": dependency.dependency_type,
    }


@router.post("/contract-versions", response_model=ContractVersionResponse)
async def create_contract_version(data: ContractVersionCreate, db: Session = Depends(get_db)):
    version = ContractVersion(
        id=str(uuid4()),
        contract_id=data.contract_id,
        version=data.version,
        contract_schema=data.contract_schema,
        released_by=data.released_by,
        release_notes=data.release_notes,
        status="draft",
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/contract-versions/{contract_id}/{version}", response_model=ContractVersionResponse)
async def get_contract_version(contract_id: str, version: str, db: Session = Depends(get_db)):
    cv = (
        db.query(ContractVersion)
        .filter(
            ContractVersion.contract_id == contract_id,
            ContractVersion.version == version,
        )
        .first()
    )
    if not cv:
        raise HTTPException(status_code=404, detail="Contract version not found")
    return cv


@router.get("/contract-versions/{contract_id}", response_model=list[ContractVersionResponse])
async def list_contract_versions(contract_id: str, db: Session = Depends(get_db)):
    versions = (
        db.query(ContractVersion)
        .filter(ContractVersion.contract_id == contract_id)
        .order_by(ContractVersion.created_at.desc())
        .all()
    )
    return versions


@router.post("/contract-versions/{contract_id}/{version}/release")
async def release_contract_version(contract_id: str, version: str, db: Session = Depends(get_db)):
    cv = (
        db.query(ContractVersion)
        .filter(
            ContractVersion.contract_id == contract_id,
            ContractVersion.version == version,
        )
        .first()
    )
    if not cv:
        raise HTTPException(status_code=404, detail="Contract version not found")
    if cv.status == "released":
        raise HTTPException(status_code=400, detail="Version already released")

    cv.status = "released"
    db.commit()
    db.refresh(cv)
    return cv


@router.post("/contract-versions/{contract_id}/{version}/deprecate")
async def deprecate_contract_version(contract_id: str, version: str, db: Session = Depends(get_db)):
    cv = (
        db.query(ContractVersion)
        .filter(
            ContractVersion.contract_id == contract_id,
            ContractVersion.version == version,
        )
        .first()
    )
    if not cv:
        raise HTTPException(status_code=404, detail="Contract version not found")

    cv.status = "deprecated"
    db.commit()
    db.refresh(cv)
    return cv


@router.post("/approvals", response_model=ContractApprovalResponse)
async def create_approval(data: ContractApprovalCreate, db: Session = Depends(get_db)):
    approval = ContractApproval(
        id=str(uuid4()),
        contract_id=data.contract_id,
        version=data.version,
        approvers=data.approvers,
        status="pending",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


@router.get("/approvals/{approval_id}", response_model=ContractApprovalResponse)
async def get_approval(approval_id: str, db: Session = Depends(get_db)):
    approval = db.query(ContractApproval).filter(ContractApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.post("/approvals/{approval_id}/approve")
async def approve(approval_id: str, approver: str, db: Session = Depends(get_db)):
    approval = db.query(ContractApproval).filter(ContractApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approvals = approval.approvals or {}
    approvals[approver] = "approved"
    approval.approvals = approvals

    if len(approvals) == len(approval.approvers):
        approval.status = "approved"

    db.commit()
    db.refresh(approval)
    return approval


@router.post("/changes", response_model=ContractChangeResponse)
async def create_change(data: ContractChangeCreate, db: Session = Depends(get_db)):
    change = ContractChange(
        id=str(uuid4()),
        contract_id=data.contract_id,
        from_version=data.from_version,
        to_version=data.to_version,
        changed_by=data.changed_by,
        change_type=data.change_type,
        changes=data.changes,
        reason=data.reason,
    )
    db.add(change)
    db.commit()
    db.refresh(change)
    return change


@router.get("/changes/{contract_id}", response_model=list[ContractChangeResponse])
async def list_changes(contract_id: str, db: Session = Depends(get_db)):
    changes = (
        db.query(ContractChange)
        .filter(ContractChange.contract_id == contract_id)
        .order_by(ContractChange.created_at.desc())
        .all()
    )
    return changes


@router.post("/dependencies", response_model=ContractDependencyResponse)
async def create_dependency(data: ContractDependencyCreate, db: Session = Depends(get_db)):
    dependency = ContractDependency(
        id=str(uuid4()),
        contract_id=data.contract_id,
        service_id=data.service_id,
        version=data.version,
        dependency_type=data.dependency_type,
        status="active",
    )
    db.add(dependency)
    db.commit()
    db.refresh(dependency)
    return dependency


@router.get("/dependencies/{contract_id}", response_model=list[ContractDependencyResponse])
async def list_dependencies(contract_id: str, db: Session = Depends(get_db)):
    dependencies = (
        db.query(ContractDependency)
        .filter(
            ContractDependency.contract_id == contract_id,
            ContractDependency.status == "active",
        )
        .all()
    )
    return dependencies


@router.get("/dependencies/service/{service_id}", response_model=list[ContractDependencyResponse])
async def list_service_dependencies(service_id: str, db: Session = Depends(get_db)):
    dependencies = (
        db.query(ContractDependency)
        .filter(
            ContractDependency.service_id == service_id,
            ContractDependency.status == "active",
        )
        .all()
    )
    return dependencies


@router.get("/contract-versions/{contract_id}/{version}/insights")
async def get_contract_insights(contract_id: str, version: str, db: Session = Depends(get_db)):
    version_obj = (
        db.query(ContractVersion)
        .filter(
            ContractVersion.contract_id == contract_id,
            ContractVersion.version == version,
        )
        .first()
    )
    if not version_obj:
        raise HTTPException(status_code=404, detail="Contract version not found")

    approvals = (
        db.query(ContractApproval)
        .filter(
            ContractApproval.contract_id == contract_id,
            ContractApproval.version == version,
        )
        .order_by(ContractApproval.created_at.asc())
        .all()
    )
    approval_payloads = [_approval_to_mapping(approval) for approval in approvals]

    workflow_data = (
        build_workflow(contract_id, version, approval_payloads).as_dict()
        if approval_payloads
        else None
    )

    changes = (
        db.query(ContractChange)
        .filter(ContractChange.contract_id == contract_id)
        .order_by(ContractChange.created_at.asc())
        .all()
    )
    change_payloads = [_change_to_mapping(change) for change in changes]

    change_history = (
        build_change_history(contract_id, change_payloads).as_dict()
        if change_payloads
        else {"contract_id": contract_id, "changes": []}
    )

    compatibility = (
        build_compatibility_matrix(contract_id, change_payloads).as_dict()
        if change_payloads
        else {"rules": []}
    )

    dependencies = (
        db.query(ContractDependency)
        .filter(ContractDependency.contract_id == contract_id)
        .order_by(ContractDependency.added_at.asc())
        .all()
    )
    dependency_payloads = [_dependency_to_mapping(dep) for dep in dependencies]
    dependency_graph = build_dependency_graph(contract_id, dependency_payloads).as_dict()

    return {
        "contract_version": {
            "contract_id": version_obj.contract_id,
            "version": version_obj.version,
            "status": version_obj.status,
            "released_by": version_obj.released_by,
            "created_at": version_obj.created_at,
        },
        "workflow": workflow_data,
        "change_history": change_history,
        "compatibility": compatibility,
        "dependency_graph": dependency_graph,
    }
