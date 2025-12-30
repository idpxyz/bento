from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from .approval_workflow.workflow import (
    ApprovalStage,
    ApprovalWorkflow,
    StageDecision,
)
from .change_tracking.tracker import ChangeHistory, ChangeRecord
from .compatibility_matrix.matrix import (
    CompatibilityLevel,
    CompatibilityMatrix,
    CompatibilityRule,
)
from .dependency_graph.graph import DependencyGraph, DependencyLink

ApprovalInput = Mapping[str, Any]
ChangeInput = Mapping[str, Any]
DependencyInput = Mapping[str, Any]

_STATUS_TO_DECISION: dict[str, StageDecision] = {
    "pending": StageDecision.PENDING,
    "approved": StageDecision.APPROVED,
    "rejected": StageDecision.REJECTED,
}

_CHANGE_TYPE_TO_COMPAT: dict[str, CompatibilityLevel] = {
    "compatible": CompatibilityLevel.COMPATIBLE,
    "non-breaking": CompatibilityLevel.COMPATIBLE,
    "warning": CompatibilityLevel.WARNING,
    "breaking": CompatibilityLevel.BREAKING,
}


def build_workflow(contract_id: str, version: str, approvals: Sequence[ApprovalInput]) -> ApprovalWorkflow:
    stages: list[ApprovalStage] = []
    for index, approval in enumerate(approvals, start=1):
        status = str(approval.get("status", "pending")).lower()
        decision = _STATUS_TO_DECISION.get(status, StageDecision.PENDING)
        approvers = list(approval.get("approvers", []) or [])
        comments = list(approval.get("comments", []) or [])

        stage = ApprovalStage(
            name=f"Stage {index}",
            approvers=approvers,
            quorum=max(1, len(approvers)) if approvers else 1,
            decision=decision,
            notes="; ".join(comments) if comments else None,
        )
        stages.append(stage)

    if not stages:
        raise ValueError("No approval stages defined for workflow")

    return ApprovalWorkflow(
        workflow_id=f"{contract_id}:{version}",
        contract_id=contract_id,
        version=version,
        stages=stages,
    )


def build_change_history(contract_id: str, changes: Iterable[ChangeInput]) -> ChangeHistory:
    history = ChangeHistory(contract_id=contract_id)
    for change in changes:
        created_at = change.get("created_at")
        if created_at is None:
            created_at = datetime.utcnow()
        history.append(
            ChangeRecord(
                change_id=str(change.get("id")),
                contract_id=str(change.get("contract_id", contract_id)),
                from_version=str(change.get("from_version")),
                to_version=str(change.get("to_version")),
                change_type=str(change.get("change_type", "")),
                author=str(change.get("changed_by", "")),
                summary=str(change.get("reason", "")),
                created_at=created_at,
            )
        )
    return history


def build_compatibility_matrix(contract_id: str, changes: Iterable[ChangeInput]) -> CompatibilityMatrix:
    matrix = CompatibilityMatrix()
    for change in changes:
        change_type = str(change.get("change_type", "")).lower()
        level = _CHANGE_TYPE_TO_COMPAT.get(change_type, CompatibilityLevel.WARNING)
        rule = CompatibilityRule(
            from_version=str(change.get("from_version")),
            to_version=str(change.get("to_version")),
            level=level,
            notes=str(change.get("reason", "")),
        )
        try:
            matrix.register(rule)
        except ValueError:
            matrix.update(rule)
    return matrix


def build_dependency_graph(contract_id: str, dependencies: Iterable[DependencyInput]) -> DependencyGraph:
    graph = DependencyGraph(contract_id=contract_id)
    for dep in dependencies:
        graph.add_link(
            DependencyLink(
                source_service=str(dep.get("contract_id")),
                target_service=str(dep.get("service_id")),
                contract_id=contract_id,
                version=str(dep.get("version")),
                dependency_type=str(dep.get("dependency_type", "consumer")),
            )
        )
    return graph
