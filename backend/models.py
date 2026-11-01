from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from db import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='RECRUITER')
    department = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)


class Candidate(Base):
    __tablename__ = 'candidates'

    id = Column(String(50), primary_key=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    source = Column(String(100), default='email')
    created_at = Column(DateTime, default=datetime.utcnow)


class JobOffer(Base):
    __tablename__ = 'job_offers'

    id = Column(String(50), primary_key=True)
    title = Column(String(255), nullable=False)
    criteria = Column(JSON, nullable=False)
    weights = Column(JSON, nullable=False)
    scoring_version = Column(String(50), default='v1.0')
    status = Column(String(50), default='OPEN')


class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(50), ForeignKey('candidates.id'), nullable=False)
    job_id = Column(String(50), ForeignKey('job_offers.id'), nullable=False)
    status = Column(String(100), default='NEW')
    last_contact_at = Column(DateTime, default=datetime.utcnow)
    reminders_count = Column(Integer, default=0)


class Message(Base):
    __tablename__ = 'messages'

    id = Column(String(50), primary_key=True)
    source = Column(String(50), default='email')
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='NEW')
    external_ref = Column(String(255), nullable=True)
    thread_id = Column(String(100), nullable=True)
    security_flags = Column(JSON, default=list)


class Classification(Base):
    __tablename__ = 'classifications'

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(50), ForeignKey('messages.id'), nullable=False)
    category = Column(String(50), nullable=False)
    intent = Column(String(80), nullable=False)
    priority = Column(String(50), nullable=False)
    department = Column(String(50), nullable=True)
    destination = Column(String(80), nullable=False)
    confidence = Column(Integer, default=0)
    reason = Column(Text, nullable=True)
    source = Column(String(50), default='RULES')
    model = Column(String(50), default='llama3.2:3b')


class Evaluation(Base):
    __tablename__ = 'evaluations'

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False)
    score = Column(Integer, nullable=False)
    breakdown = Column(JSON, nullable=False)
    evidence = Column(JSON, nullable=False)
    missing = Column(JSON, nullable=False)
    scoring_version = Column(String(50), default='v1.0')
    model_version = Column(String(50), default='llama3.2:3b')
    reviewed_by = Column(String(100), nullable=True)


class Interview(Base):
    __tablename__ = 'interviews'

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False)
    recruiter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    status = Column(String(50), default='PROPOSED')


class CalendarSlot(Base):
    __tablename__ = 'calendar_slots'

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    kind = Column(String(20), default='FREE')


class Draft(Base):
    __tablename__ = 'drafts'

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(50), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    context_ref = Column(String(255), nullable=True)
    version = Column(Integer, default=1)
    status = Column(String(50), default='PENDING_APPROVAL')


class Approval(Base):
    __tablename__ = 'approvals'

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    draft_id = Column(Integer, ForeignKey('drafts.id'), nullable=True)
    status = Column(String(50), default='PENDING_APPROVAL')
    required_role = Column(String(50), default='RECRUITER')
    requested_by = Column(String(100), nullable=False)
    decided_by = Column(String(100), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), default='OPEN')
    assigned_to = Column(String(100), nullable=True)
    source_message_id = Column(String(50), nullable=True)


class PolicyDoc(Base):
    __tablename__ = 'policy_docs'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    audience = Column(String(50), default='employee')
    version = Column(String(50), default='v1')
    file_id = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)


class Digest(Base):
    __tablename__ = 'digests'

    id = Column(Integer, primary_key=True, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    html = Column(Text, nullable=False)
    created_by = Column(String(100), default='system')


class JobRun(Base):
    __tablename__ = 'job_runs'

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default='QUEUED')
    attempts = Column(Integer, default=0)
    run_at = Column(DateTime, default=datetime.utcnow)
    error = Column(Text, nullable=True)


class WorkflowRequest(Base):
    __tablename__ = 'workflow_requests'

    idempotency_key = Column(String(100), primary_key=True)
    request_hash = Column(String(64), nullable=False)
    status = Column(String(30), nullable=False, default='RUNNING')
    message_id = Column(String(50), nullable=True)
    execution_id = Column(String(100), nullable=True)
    response = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False)
    agent = Column(String(100), nullable=False)
    action = Column(String(150), nullable=False)
    entity = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    details = Column(JSON, nullable=False)
    prev_hash = Column(String(255), nullable=False, default='GENESIS')
    hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
