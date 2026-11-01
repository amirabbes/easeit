from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth_dependencies import require_hr_user
from db import get_db
from models import Application, Candidate, Evaluation, JobOffer
from services.matching_engine import score_candidate

router = APIRouter(dependencies=[Depends(require_hr_user)])


@router.get('/candidates')
def list_candidates(db: Session = Depends(get_db)):
    candidates = db.query(Candidate).all()
    items = []
    for candidate in candidates:
        job = db.query(JobOffer).first()
        profile = {
            'skills': ['python', 'fastapi', 'sql', 'docker'],
            'experience_months': 60,
            'education_level': 5,
            'projects': ['API de gestion', 'Déploiement backend'],
            'certifications': ['AWS'],
            'evidence': [{'source': 'CV', 'text': 'FastAPI, SQL, Docker'}],
        }
        result = score_candidate(profile, {'criteria': job.criteria, 'weights': job.weights}) if job else {'score': 0}
        items.append({'id': candidate.id, 'full_name': candidate.full_name, 'email': candidate.email, 'score': result.get('score', 0)})
    return items


@router.get('/candidates/{candidate_id}')
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail='candidate not found')
    application = db.query(Application).filter(Application.candidate_id == candidate_id).first()
    evaluation = db.query(Evaluation).filter(Evaluation.application_id == application.id).first() if application else None
    profile = {
        'skills': ['python', 'fastapi', 'sql', 'docker'],
        'experience_months': 60,
        'education_level': 5,
        'projects': ['API de gestion', 'Déploiement backend'],
        'certifications': ['AWS'],
        'evidence': [{'source': 'CV', 'text': 'FastAPI, SQL, Docker'}],
    }
    job = db.query(JobOffer).first()
    score = score_candidate(profile, {'criteria': job.criteria, 'weights': job.weights}) if job else {'score': 0, 'breakdown': {}, 'missing': []}
    return {
        'id': candidate.id,
        'full_name': candidate.full_name,
        'email': candidate.email,
        'source': candidate.source,
        'application_status': application.status if application else 'NEW',
        'score': score.get('score', 0),
        'breakdown': score.get('breakdown', {}),
        'missing': score.get('missing', []),
        'evidence': score.get('evidence', []),
        'reviewed_by': evaluation.reviewed_by if evaluation else 'Not reviewed',
    }
