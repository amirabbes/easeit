from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from db import SessionLocal, init_db
from models import Application, Approval, AuditLog, Candidate, Classification, Digest, Draft, Evaluation, JobOffer, JobRun, Message, PolicyDoc, Ticket, User
from security import hash_password


def seed_if_empty() -> None:
    init_db()
    db = SessionLocal()
    if db.query(User).count() > 0:
        db.close()
        return

    users = [
        User(email='recruiter@easeit.local', password_hash=hash_password('recruiter123'), role='RECRUITER', department='HR', full_name='Alice Bens'),
        User(email='hrmanager@easeit.local', password_hash=hash_password('hrmanager123'), role='HR_MANAGER', department='HR', full_name='Nina Morel'),
        User(email='employee@easeit.local', password_hash=hash_password('employee123'), role='EMPLOYEE', department='Engineering', full_name='Samir Haddad'),
        User(email='admin@easeit.local', password_hash=hash_password('admin123'), role='ADMIN', department='Operations', full_name='Admin Easeit'),
    ]
    db.add_all(users)
    db.flush()

    job = JobOffer(
        id='JOB-001',
        title='Développeur Backend Python',
        criteria={
            'must_have_skills': ['python', 'fastapi', 'sql'],
            'nice_to_have_skills': ['docker', 'redis', 'ci/cd'],
            'min_experience_months': 36,
            'domain_keywords': ['backend', 'api', 'microservices', 'python'],
            'min_education_level': 5,
            'required_certifications': [],
            'project_keywords': ['api', 'base de données', 'déploiement'],
        },
        weights={'skills': 35, 'experience': 25, 'education': 15, 'projects': 15, 'certifications': 10},
        scoring_version='v1.0',
        status='OPEN',
    )
    db.add(job)

    candidate = Candidate(
        id='CAND-021',
        full_name='Sofia Martin',
        email='sofia.martin@email.com',
        phone='+33612345678',
        source='email',
    )
    db.add(candidate)
    db.flush()

    application = Application(
        candidate_id=candidate.id,
        job_id=job.id,
        status='AWAITING_CANDIDATE',
        last_contact_at=datetime.utcnow() - timedelta(days=2),
        reminders_count=1,
    )
    db.add(application)
    db.flush()

    message = Message(
        id='MSG-001',
        source='email',
        sender='sofia.martin@email.com',
        recipient='recruiter@easeit.local',
        subject='Candidature pour développeur backend Python',
        body='Bonjour, je souhaite candidater au poste de développeur backend Python. J’ai 5 ans d’expérience avec FastAPI, SQL et les APIs. J’ai réalisé un service de gestion de données et j’ai déployé des services avec Docker. Merci.',
        status='NEW',
        security_flags=[],
    )
    db.add(message)

    classification = Classification(
        message_id=message.id,
        category='RECRUITMENT',
        intent='NEW_APPLICATION',
        priority='MEDIUM',
        destination='ATS_AGENT',
        confidence=86,
        reason='CV et candidature détectés.',
        source='RULES',
        model='llama3.2:3b',
    )
    db.add(classification)

    evaluation = Evaluation(
        application_id=application.id,
        score=82,
        breakdown={
            'skills': 0.95,
            'experience': 0.9,
            'education': 1.0,
            'projects': 0.8,
            'certifications': 0.0,
        },
        evidence=[
            {'source': 'CV', 'text': 'FastAPI et SQL', 'position': 'Expérience 1'},
            {'source': 'CV', 'text': 'Docker', 'position': 'Expérience 2'},
        ],
        missing=['None'],
        scoring_version='v1.0',
        model_version='llama3.2:3b',
        reviewed_by='Alice Bens'
    )
    db.add(evaluation)

    draft = Draft(
        kind='INTERVIEW_INVITE',
        recipient='sofia.martin@email.com',
        subject='Invitation à interview',
        body='Bonjour Sofia, nous souhaitons vous inviter à un entretien pour le poste de développeur backend Python. Nous vous proposerons trois créneaux dans les prochains jours.',
        context_ref='application:1',
        version=1,
        status='PENDING_APPROVAL',
    )
    db.add(draft)
    db.flush()

    approval = Approval(
        action='SEND_INTERVIEW_INVITE',
        payload={'draft_id': draft.id, 'recipient': 'sofia.martin@email.com'},
        draft_id=draft.id,
        status='PENDING_APPROVAL',
        required_role='RECRUITER',
        requested_by='system',
        expires_at=datetime.utcnow() + timedelta(hours=48),
    )
    db.add(approval)

    ticket = Ticket(
        employee_id=users[2].id,
        subject='Question sur les congés',
        body='Je voudrais savoir combien de jours de congés il me reste.',
        status='OPEN',
        assigned_to='HR',
        source_message_id='MSG-002',
    )
    db.add(ticket)

    policy_doc = PolicyDoc(
        title='Politique congés',
        audience='employee',
        version='v1',
        file_id='POL-001',
        content='Les employés ont droit à 25 jours de congés par an. Le solde est calculé sur l’année civile. Le manager approuve les demandes de congés selon les besoins opérationnels.'
    )
    db.add(policy_doc)

    digest = Digest(
        period_start=datetime.utcnow() - timedelta(days=1),
        period_end=datetime.utcnow(),
        html='''<h2>Digest RH</h2><ul><li>1 candidature a été reçue</li><li>2 demandes d’entretien en attente</li><li>1 question employé</li></ul>''',
        created_by='Digest Agent',
    )
    db.add(digest)

    job_run = JobRun(
        kind='FOLLOW_UP',
        payload={'days': 3},
        status='QUEUED',
        attempts=0,
        run_at=datetime.utcnow(),
    )
    db.add(job_run)

    prev_hash = 'GENESIS'
    events = [
        {'user_id': 'system', 'agent': 'Planner', 'action': 'CLASSIFY_MESSAGE', 'entity': 'messages', 'entity_id': message.id, 'details': {'priority': 'MEDIUM', 'intent': 'NEW_APPLICATION'}},
        {'user_id': 'alice', 'agent': 'ATS', 'action': 'EVALUATE_CANDIDATE', 'entity': 'evaluations', 'entity_id': str(evaluation.id or 1), 'details': {'score': 82}},
        {'user_id': 'alice', 'agent': 'ApprovalEngine', 'action': 'CREATE_APPROVAL', 'entity': 'approvals', 'entity_id': str(approval.id or 1), 'details': {'status': 'PENDING_APPROVAL'}}
    ]
    for item in events:
        payload = json.dumps(item, sort_keys=True)
        current_hash = hashlib.sha256((prev_hash + payload).encode()).hexdigest()
        db.add(AuditLog(
            user_id=str(item['user_id']),
            agent=item['agent'],
            action=item['action'],
            entity=item['entity'],
            entity_id=item['entity_id'],
            details=item['details'],
            prev_hash=prev_hash,
            hash=current_hash,
        ))
        prev_hash = current_hash

    db.commit()
    db.close()
