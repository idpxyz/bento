from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StageDecision(str, Enum):
    """Possible decisions for an approval stage."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkflowStatus(str, Enum):
    """Overall workflow status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ApprovalStage:
    """Single approval stage with basic state tracking."""

    name: str
    approvers: list[str]
    quorum: int = 1
    decision: StageDecision = StageDecision.PENDING
    decided_by: str | None = None
    decided_at: datetime | None = None
    notes: str | None = None

    def approve(self, approver: str, notes: str | None = None) -> None:
        self._ensure_pending()
        self._ensure_authorized(approver)
        self.decision = StageDecision.APPROVED
        self._stamp(approver, notes)

    def reject(self, approver: str, notes: str | None = None) -> None:
        self._ensure_pending()
        self._ensure_authorized(approver)
        self.decision = StageDecision.REJECTED
        self._stamp(approver, notes)

    def _ensure_pending(self) -> None:
        if self.decision is not StageDecision.PENDING:
            raise ValueError(f"Stage '{self.name}' already decided")

    def _ensure_authorized(self, approver: str) -> None:
        if approver not in self.approvers:
            raise ValueError(f"{approver} cannot act on stage '{self.name}'")

    def _stamp(self, approver: str, notes: str | None) -> None:
        self.decided_by = approver
        self.decided_at = datetime.utcnow()
        self.notes = notes


@dataclass
class ApprovalWorkflow:
    """Aggregate representing a multi-stage approval workflow."""

    workflow_id: str
    contract_id: str
    version: str
    stages: list[ApprovalStage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: WorkflowStatus = WorkflowStatus.PENDING

    def __post_init__(self) -> None:
        if not self.stages:
            raise ValueError("Workflow requires at least one stage")
        names = [stage.name for stage in self.stages]
        if len(names) != len(set(names)):
            raise ValueError("Workflow stages must be unique")

    def current_stage(self) -> ApprovalStage:
        """Return the first pending stage (or the last one if all decided)."""
        for stage in self.stages:
            if stage.decision is StageDecision.PENDING:
                return stage
        return self.stages[-1]

    def pending_stages(self) -> list[str]:
        return [stage.name for stage in self.stages if stage.decision is StageDecision.PENDING]

    def decide_stage(
        self,
        stage_name: str,
        approver: str,
        *,
        approved: bool,
        notes: str | None = None,
    ) -> StageDecision:
        stage = self._get_stage(stage_name)
        if approved:
            stage.approve(approver, notes)
        else:
            stage.reject(approver, notes)

        self._recalculate_status()
        return stage.decision

    def _get_stage(self, stage_name: str) -> ApprovalStage:
        for stage in self.stages:
            if stage.name == stage_name:
                return stage
        raise ValueError(f"Stage '{stage_name}' not part of this workflow")

    def _recalculate_status(self) -> None:
        if any(stage.decision is StageDecision.REJECTED for stage in self.stages):
            self.status = WorkflowStatus.REJECTED
            return
        if all(stage.decision is StageDecision.APPROVED for stage in self.stages):
            self.status = WorkflowStatus.APPROVED
            return
        self.status = WorkflowStatus.PENDING

    def is_complete(self) -> bool:
        return self.status in {WorkflowStatus.REJECTED, WorkflowStatus.APPROVED}

    def as_dict(self) -> dict[str, object]:
        """Serialize the workflow for simple projections or logging."""
        return {
            "workflow_id": self.workflow_id,
            "contract_id": self.contract_id,
            "version": self.version,
            "status": self.status.value,
            "stages": [
                {
                    "name": stage.name,
                    "decision": stage.decision.value,
                    "decided_by": stage.decided_by,
                    "decided_at": stage.decided_at.isoformat() if stage.decided_at else None,
                }
                for stage in self.stages
            ],
        }
