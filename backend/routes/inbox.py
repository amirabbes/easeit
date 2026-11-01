from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth_dependencies import require_hr_user
from core.llm import classify_message
from db import get_db
from models import Classification, Message

router = APIRouter(dependencies=[Depends(require_hr_user)])


@router.get('/messages')
def list_messages(db: Session = Depends(get_db)):
    messages = db.query(Message).all()
    rows = []
    for message in messages:
        classification = db.query(Classification).filter(Classification.message_id == message.id).first()
        if classification is None:
            result = classify_message(message.body)
            classification = Classification(
                message_id=message.id,
                category=result['category'],
                intent=result['intent'],
                priority=result['priority'],
                destination=result['destination'],
                confidence=int(result['confidence'] * 100),
                reason=result['reason'],
                source='RULES',
                model='llama3.2:3b',
            )
            db.add(classification)
        rows.append({
            'id': message.id,
            'sender': message.sender,
            'subject': message.subject,
            'body': message.body,
            'priority': classification.priority,
            'category': classification.category,
            'department': classification.department,
            'intent': classification.intent,
            'destination': classification.destination,
            'confidence': classification.confidence / 100,
            'received_at': message.received_at.isoformat(),
        })
    db.commit()
    return rows


@router.get('/messages/{message_id}')
def get_message(message_id: str, db: Session = Depends(get_db)):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail='message not found')
    classification = db.query(Classification).filter(Classification.message_id == message.id).first()
    return {
        'id': message.id,
        'sender': message.sender,
        'subject': message.subject,
        'body': message.body,
        'priority': classification.priority if classification else 'MEDIUM',
        'category': classification.category if classification else 'OTHER',
        'department': classification.department if classification else None,
        'intent': classification.intent if classification else 'OTHER',
        'destination': classification.destination if classification else 'HUMAN_REVIEW',
    }
