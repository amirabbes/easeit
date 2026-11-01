from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_dependencies import get_current_user, require_hr_user
from db import get_db
from models import Approval, Draft, User

router = APIRouter(dependencies=[Depends(require_hr_user)])


@router.get('/approvals')
def list_approvals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in {'ADMIN', 'HR_MANAGER', 'RECRUITER'}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='HR role required')
    approvals = db.query(Approval).order_by(Approval.id.desc()).all()
    rows = []
    for approval in approvals:
        draft = db.query(Draft).filter(Draft.id == approval.draft_id).first() if approval.draft_id else None
        rows.append({
            'id': approval.id,
            'action': approval.action,
            'status': approval.status,
            'required_role': approval.required_role,
            'requested_by': approval.requested_by,
            'draft_id': approval.draft_id,
            'payload': approval.payload,
            'expires_at': approval.expires_at.isoformat() if approval.expires_at else None,
            'draft': {
                'recipient': draft.recipient,
                'subject': draft.subject,
                'body': draft.body,
                'status': draft.status,
            } if draft else None,
        })
    return rows


@router.post('/approvals/{approval_id}/approve')
def approve_approval(
    approval_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return decide_approval(approval_id, 'APPROVED', user, db)


@router.post('/approvals/{approval_id}/reject')
def reject_approval(
    approval_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return decide_approval(approval_id, 'REJECTED', user, db)


def decide_approval(
    approval_id: int,
    decision: Literal['APPROVED', 'REJECTED'],
    user: User,
    db: Session,
):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='approval not found')
    if approval.status != 'PENDING_APPROVAL':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='approval is no longer pending')
    if user.role != 'ADMIN' and user.role != approval.required_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='required role does not match approval')

    now = datetime.now(timezone.utc)
    if approval.expires_at:
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            approval.status = 'EXPIRED'
            draft = db.query(Draft).filter(Draft.id == approval.draft_id).first() if approval.draft_id else None
            if draft:
                draft.status = 'EXPIRED'
            db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='approval has expired')

    approval.status = decision
    approval.decided_by = user.email
    approval.decided_at = now
    draft = db.query(Draft).filter(Draft.id == approval.draft_id).first() if approval.draft_id else None
    if draft:
        draft.status = decision
    db.commit()
    return {'status': approval.status, 'approval_id': approval.id, 'decided_by': approval.decided_by}
