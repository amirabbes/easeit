from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth_dependencies import require_hr_user
from core.llm import build_digest_html
from db import get_db
from models import Digest

router = APIRouter(dependencies=[Depends(require_hr_user)])


@router.get('/digest')
def list_digest(db: Session = Depends(get_db)):
    rows = db.query(Digest).all()
    if not rows:
        html = build_digest_html([
            {'title': 'Recrutement', 'items': ['1 candidature requiert une réponse']},
            {'title': 'Employés', 'items': ['1 question RH ouverte']},
        ])
        return [{'period': 'Today', 'html': html}]
    return [{'period': row.period_start.strftime('%Y-%m-%d'), 'html': row.html} for row in rows]


@router.get('/digest/{digest_id}')
def get_digest(digest_id: int, db: Session = Depends(get_db)):
    row = db.query(Digest).filter(Digest.id == digest_id).first()
    if not row:
        raise HTTPException(status_code=404, detail='digest not found')
    return {'id': row.id, 'period': row.period_start.strftime('%Y-%m-%d'), 'html': row.html}
