from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ApprovalDecisionType,
    ApprovalStatus,
    PolicyActionType,
    SensitiveActionApproval,
    SensitiveActionApprovalDecision,
)
from app.services.authorization_policy_service import PolicyDecision


@dataclass
class ApprovalResolution:
    approval: SensitiveActionApproval
    completed: bool
    rejected: bool


class ApprovalWorkflowService:
    async def create_request(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        action_type: PolicyActionType,
        entity_type: str,
        entity_id: str,
        requested_by_sub: str,
        request_reason: str,
        required_approvals: int,
        policy_decision: PolicyDecision,
        requested_payload: dict,
        device_id: UUID | None = None,
        incident_id: UUID | None = None,
    ) -> SensitiveActionApproval:
        now = datetime.now(timezone.utc)
        approval = SensitiveActionApproval(
            org_id=org_id,
            action_type=action_type,
            status=ApprovalStatus.PENDING,
            entity_type=entity_type,
            entity_id=entity_id,
            device_id=device_id,
            incident_id=incident_id,
            requested_by_sub=requested_by_sub,
            request_reason=request_reason,
            required_approvals=max(required_approvals, 1),
            policy_context_json={
                'reason_code': policy_decision.reason_code,
                'reason': policy_decision.reason,
                'owner_subject': policy_decision.owner_subject,
                'incident_state': policy_decision.incident_state.value if policy_decision.incident_state else None,
                **policy_decision.context,
            },
            requested_payload_json=requested_payload,
            approved_at=None,
            rejected_at=None,
            expires_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(approval)
        await session.flush()
        await session.refresh(approval)
        return approval

    async def list_approvals(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        status: ApprovalStatus | None = None,
        action_type: PolicyActionType | None = None,
    ) -> list[SensitiveActionApproval]:
        stmt = (
            select(SensitiveActionApproval)
            .where(SensitiveActionApproval.org_id == org_id)
            .options(selectinload(SensitiveActionApproval.decisions))
            .order_by(desc(SensitiveActionApproval.created_at))
        )
        if status is not None:
            stmt = stmt.where(SensitiveActionApproval.status == status)
        if action_type is not None:
            stmt = stmt.where(SensitiveActionApproval.action_type == action_type)
        return list((await session.execute(stmt)).scalars().all())

    async def get_approval(self, session: AsyncSession, approval_id: UUID) -> SensitiveActionApproval:
        approval = (
            await session.execute(
                select(SensitiveActionApproval)
                .where(SensitiveActionApproval.id == approval_id)
                .options(selectinload(SensitiveActionApproval.decisions))
            )
        ).scalar_one_or_none()
        if approval is None:
            raise ValueError('Unknown approval_id')
        return approval

    async def find_by_entity(
        self,
        session: AsyncSession,
        *,
        entity_type: str,
        entity_id: str,
    ) -> SensitiveActionApproval | None:
        return (
            await session.execute(
                select(SensitiveActionApproval)
                .where(
                    SensitiveActionApproval.entity_type == entity_type,
                    SensitiveActionApproval.entity_id == entity_id,
                )
                .options(selectinload(SensitiveActionApproval.decisions))
                .order_by(desc(SensitiveActionApproval.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def record_decision(
        self,
        session: AsyncSession,
        *,
        approval_id: UUID,
        actor_sub: str,
        approve: bool,
        reason: str,
    ) -> ApprovalResolution:
        approval = await self.get_approval(session, approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError('Approval is no longer pending.')
        if approval.requested_by_sub == actor_sub:
            raise ValueError('Requester cannot approve or reject their own sensitive action request.')
        if any(existing.actor_sub == actor_sub for existing in approval.decisions):
            raise ValueError('Actor has already decided this approval request.')

        now = datetime.now(timezone.utc)
        decision = SensitiveActionApprovalDecision(
            approval_id=approval.id,
            actor_sub=actor_sub,
            decision=ApprovalDecisionType.APPROVE if approve else ApprovalDecisionType.REJECT,
            reason=reason.strip(),
            created_at=now,
        )
        session.add(decision)
        await session.flush()

        if not approve:
            approval.status = ApprovalStatus.REJECTED
            approval.rejected_at = now
            approval.updated_at = now
            await session.flush()
            await session.refresh(approval)
            return ApprovalResolution(approval=approval, completed=False, rejected=True)

        approval_count = sum(1 for item in [*approval.decisions, decision] if item.decision == ApprovalDecisionType.APPROVE)
        if approval_count >= approval.required_approvals:
            approval.status = ApprovalStatus.APPROVED
            approval.approved_at = now
            approval.updated_at = now
            await session.flush()
            await session.refresh(approval)
            return ApprovalResolution(approval=approval, completed=True, rejected=False)

        approval.updated_at = now
        await session.flush()
        await session.refresh(approval)
        return ApprovalResolution(approval=approval, completed=False, rejected=False)
