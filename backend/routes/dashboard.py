from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_dependencies import get_current_user
from db import get_db
from models import Approval, Candidate, Message, Ticket, User

router = APIRouter()


@router.get('/overview')
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == 'EMPLOYEE':
        tickets = db.query(Ticket).filter(
            Ticket.employee_id == user.id,
            Ticket.status != 'RESOLVED',
        ).count()
        return {
            'summary': {
                'candidates': 0,
                'messages': 0,
                'pending_approvals': 0,
                'open_tickets': tickets,
            },
            'top_cards': [],
        }

    if user.role not in {'ADMIN', 'HR_MANAGER', 'RECRUITER'}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='HR role required')
    candidates = db.query(Candidate).count()
    messages = db.query(Message).count()
    approvals = db.query(Approval).filter(Approval.status == 'PENDING_APPROVAL').count()
    tickets = db.query(Ticket).filter(Ticket.status != 'RESOLVED').count()
    return {
        'summary': {
            'candidates': candidates,
            'messages': messages,
            'pending_approvals': approvals,
            'open_tickets': tickets,
        },
        'top_cards': [
            {'title': 'Applications', 'value': str(candidates), 'trend': '+12%'},
            {'title': 'Urgent', 'value': '3', 'trend': '+1'},
            {'title': 'Approvals', 'value': str(approvals), 'trend': '2 due today'},
            {'title': 'Digest', 'value': '1', 'trend': 'fresh'},
        ],
    }
