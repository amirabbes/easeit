import hashlib
import json
import logging
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from auth_dependencies import require_hr_user
from db import get_db
from models import AuditLog, Classification, Message, User, WorkflowRequest
from schemas import WorkflowIntakeRequest, WorkflowIntakeResponse
from services.cv_extractor import MAX_CV_UPLOAD_BYTES, extract_pdf_text
from services.n8n_client import N8nIntegrationError, submit_workflow

router = APIRouter()
logger = logging.getLogger(__name__)
_IDEMPOTENCY_KEY = re.compile(r'^[A-Za-z0-9._:-]{1,100}$')


@router.post('/workflows/intake', response_model=WorkflowIntakeResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_hr_workflow(
    payload: WorkflowIntakeRequest,
    user: User = Depends(require_hr_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
) -> WorkflowIntakeResponse:
    key = idempotency_key or str(uuid4())
    if not _IDEMPOTENCY_KEY.fullmatch(key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='invalid Idempotency-Key')

    normalized = payload.model_dump()
    if not payload.subject.strip() or (not payload.body.strip() and not payload.cv_text.strip()):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='subject and request content are required')
    request_hash = hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode('utf-8')
    ).hexdigest()
    record = db.query(WorkflowRequest).filter(WorkflowRequest.idempotency_key == key).first()
    if record:
        if record.request_hash != request_hash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Idempotency-Key already used for another request')
        if record.status == 'SUCCEEDED' and record.response:
            return WorkflowIntakeResponse(**record.response).model_copy(update={'duplicate': True})
        if record.status == 'RUNNING':
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='workflow request is already being processed')
        record.status = 'RUNNING'
        record.error = None
        db.commit()
    else:
        record = WorkflowRequest(
            idempotency_key=key,
            request_hash=request_hash,
            status='RUNNING',
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            record = db.query(WorkflowRequest).filter(WorkflowRequest.idempotency_key == key).first()
            if record and record.request_hash != request_hash:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Idempotency-Key already used for another request')
            if record and record.status == 'SUCCEEDED' and record.response:
                return WorkflowIntakeResponse(**record.response).model_copy(update={'duplicate': True})
            if record:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='workflow request is already being processed')
            raise
    request_id = str(uuid4())
    workflow_payload = {
        **normalized,
        'source': 'dashboard',
        'sender': user.email,
        'request_id': request_id,
        'actor': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
        },
    }

    try:
        result = submit_workflow(workflow_payload)
        classification = result.get('classification')
        message_id = result.get('message_id')
        if not isinstance(classification, dict) or not isinstance(message_id, str) or not message_id:
            raise N8nIntegrationError('La réponse n8n ne contient pas de classification exploitable.')
        classification = dict(classification)
        if classification.get('category') == 'EMPLOYEE':
            classification['category'] = 'EMPLOYEE_SUPPORT'
        if classification.get('priority') == 'INFORMATION':
            classification['priority'] = 'LOW'
        response = WorkflowIntakeResponse(
            request_id=request_id,
            execution_id=str(result['execution_id']) if result.get('execution_id') is not None else None,
            message_id=message_id,
            status=str(result.get('status') or 'accepted'),
            classification=classification,
        )
    except N8nIntegrationError as error:
        record.status = 'FAILED'
        record.error = str(error)
        db.commit()
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    except ValidationError as error:
        logger.warning('n8n workflow returned an invalid classification: %s', error.error_count())
        record.status = 'FAILED'
        record.error = 'invalid workflow classification'
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='La classification reçue de n8n est invalide.',
        ) from error

    existing_message = db.query(Message).filter(Message.id == response.message_id).first()
    if existing_message:
        record.status = 'FAILED'
        record.error = 'n8n returned a duplicate message id'
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='n8n returned an existing message id')

    classification_data = response.classification
    message = Message(
        id=response.message_id,
        source='dashboard',
        sender=user.email,
        recipient='easeit',
        subject=payload.subject.strip(),
        body='\n\n'.join(part for part in (payload.body.strip(), payload.cv_text.strip()) if part),
        status='NEW',
        external_ref=key,
        security_flags=[],
    )
    db.add(message)
    db.flush()
    db.add(Classification(
        message_id=message.id,
        category=classification_data.category,
        intent=classification_data.intent,
        priority=classification_data.priority,
        department=classification_data.department,
        destination=classification_data.destination,
        confidence=round(classification_data.confidence * 100),
        reason=classification_data.reason,
        source=classification_data.source,
        model='llama3.2:3b',
    ))

    previous = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    event = {
        'user_id': str(user.id),
        'agent': 'n8n',
        'action': 'CLASSIFY_MESSAGE',
        'entity': 'messages',
        'entity_id': message.id,
        'details': {
            'category': classification_data.category,
            'destination': classification_data.destination,
            'priority': classification_data.priority,
            'workflow_execution_id': response.execution_id,
        },
    }
    previous_hash = previous.hash if previous else 'GENESIS'
    event_json = json.dumps(event, sort_keys=True)
    db.add(AuditLog(
        **event,
        prev_hash=previous_hash,
        hash=hashlib.sha256((previous_hash + event_json).encode()).hexdigest(),
    ))

    response_data = response.model_dump()
    record.status = 'SUCCEEDED'
    record.message_id = response.message_id
    record.execution_id = response.execution_id
    record.response = response_data
    record.error = None
    db.commit()
    return response


@router.post('/workflows/intake/cv', response_model=WorkflowIntakeResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_cv_workflow(
    subject: str = Form(min_length=1, max_length=200),
    body: str = Form(default='', max_length=20000),
    candidate_name: str | None = Form(default=None, max_length=60),
    candidate_id: str | None = Form(default=None, max_length=20),
    job_id: str = Form(default='JOB-001', min_length=1, max_length=20),
    cv_file: UploadFile = File(...),
    user: User = Depends(require_hr_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
) -> WorkflowIntakeResponse:
    if not cv_file.filename or not cv_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail='Seuls les fichiers PDF sont acceptés.')

    contents = await cv_file.read(MAX_CV_UPLOAD_BYTES + 1)
    await cv_file.close()
    try:
        cv_text = await run_in_threadpool(extract_pdf_text, contents)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    payload = WorkflowIntakeRequest(
        subject=subject,
        body=body.strip() or 'Candidature reçue avec CV.',
        cv_text=cv_text,
        candidate_name=candidate_name,
        candidate_id=candidate_id,
        job_id=job_id,
    )
    return await run_in_threadpool(submit_hr_workflow, payload, user, db, idempotency_key)
