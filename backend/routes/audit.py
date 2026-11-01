import hashlib
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth_dependencies import require_hr_user
from db import get_db
from models import AuditLog

router = APIRouter(dependencies=[Depends(require_hr_user)])


@router.get('/audit/verify')
def verify_audit_chain(db: Session = Depends(get_db)):
    prev_hash = 'GENESIS'
    rows = db.query(AuditLog).order_by(AuditLog.id).all()
    for row in rows:
        payload = json.dumps({
            'user_id': row.user_id,
            'agent': row.agent,
            'action': row.action,
            'entity': row.entity,
            'entity_id': row.entity_id,
            'details': row.details,
        }, sort_keys=True)
        recomputed = hashlib.sha256((prev_hash + payload).encode()).hexdigest()
        if row.prev_hash != prev_hash or row.hash != recomputed:
            return {'valid': False, 'broken_at': row.id, 'count': len(rows)}
        prev_hash = row.hash
    return {'valid': True, 'count': len(rows)}
