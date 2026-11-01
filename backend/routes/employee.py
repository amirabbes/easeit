from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_dependencies import get_current_user
from config import settings
from core.llm import employee_support_answer
from db import get_db
from models import PolicyDoc, Ticket, User
from schemas import SupportAnswer, SupportQuestion, TicketStatusUpdate
from services.n8n_client import N8nIntegrationError, submit_workflow

router = APIRouter()


@router.post('/support')
def employee_support(
    payload: SupportQuestion,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportAnswer:
    if user.role != 'EMPLOYEE':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='employee role required')

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail='question required')

    if settings.n8n_webhook_url or settings.n8n_webhook_token:
        documents = db.query(PolicyDoc).filter(PolicyDoc.audience.in_(['employee', 'all'])).all()
        context_docs = [
            {
                'id': document.file_id or f'POLICY-{document.id}',
                'title': document.title,
                'text': document.content[:5000],
                'audience': 'employee',
            }
            for document in documents
        ]
        try:
            result = submit_workflow({
                'source': 'employee_portal',
                'sender': user.email,
                'subject': 'Question RH',
                'body': question,
                'context_docs': context_docs,
                'actor': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'employee_id': str(user.id),
                },
            })
        except N8nIntegrationError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error

        response = result.get('response')
        if not isinstance(response, dict):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='La réponse du support n8n est invalide.')
        if response.get('status') == 'DENIED':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='La demande a été refusée par le workflow.')
        if response.get('status') not in {'ANSWERED', 'ESCALATED'}:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Le workflow n8n a renvoyé un statut inconnu.')

        allowed_sources = {document['id'] for document in context_docs}
        sources = [
            source for source in response.get('sources', [])
            if isinstance(source, str) and source in allowed_sources
        ] if isinstance(response.get('sources'), list) else []
        answer = response.get('answer')
        answerable = response.get('status') == 'ANSWERED' and isinstance(answer, str) and bool(answer.strip()) and bool(sources)
        ticket_id = None
        if not answerable:
            ticket = Ticket(
                employee_id=user.id,
                subject='Escalade RH',
                body=question,
                status='OPEN',
                assigned_to='HR_MANAGER',
            )
            db.add(ticket)
            db.flush()
            ticket_id = ticket.id
            db.commit()
        return SupportAnswer(
            answer=answer.strip()[:2000] if answerable else 'Je ne peux pas répondre à partir des documents RH autorisés. Votre demande a été transmise à l’équipe RH.',
            sources=sources,
            answerable=answerable,
            escalated=not answerable,
            ticket_id=ticket_id,
        )

    result = employee_support_answer(question, user.role, user.full_name.split()[0])
    ticket_id = None
    if result['escalated']:
        ticket = Ticket(
            employee_id=user.id,
            subject='Escalade RH',
            body=question,
            status='OPEN',
            assigned_to='HR_MANAGER',
        )
        db.add(ticket)
        db.flush()
        ticket_id = ticket.id
        db.commit()
    return SupportAnswer(
        answer=result['answer'],
        sources=result['sources'],
        answerable=result['answerable'],
        escalated=result['escalated'],
        ticket_id=ticket_id,
    )


@router.get('/tickets')
def list_tickets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Ticket, User).join(User, Ticket.employee_id == User.id)
    if user.role not in {'ADMIN', 'HR_MANAGER', 'RECRUITER'}:
        query = query.filter(Ticket.employee_id == user.id)
    rows = query.order_by(Ticket.id.desc()).all()
    return [
        {
            'id': ticket.id,
            'subject': ticket.subject,
            'body': ticket.body,
            'status': ticket.status,
            'assigned_to': ticket.assigned_to,
            'employee_id': employee.id,
            'employee_name': employee.full_name,
            'employee_email': employee.email,
        }
        for ticket, employee in rows
    ]


@router.patch('/tickets/{ticket_id}')
def update_ticket(
    ticket_id: int,
    payload: TicketStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in {'ADMIN', 'HR_MANAGER', 'RECRUITER'}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='HR role required')
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='ticket not found')
    if ticket.status == 'RESOLVED':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='ticket is already resolved')
    ticket.status = payload.status
    db.commit()
    return {'id': ticket.id, 'status': ticket.status}
