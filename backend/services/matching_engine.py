from __future__ import annotations

from typing import Any


def normalize_skill(name: str) -> str:
    cleaned = name.lower().strip()
    aliases = {
        'postgres': 'postgresql',
        'postgresql': 'postgresql',
        'js': 'javascript',
        'node': 'nodejs',
        'python': 'python',
        'fastapi': 'fastapi',
        'docker': 'docker',
        'kubernetes': 'kubernetes',
    }
    return aliases.get(cleaned, cleaned)


def score_candidate(candidate: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    skills = job.get('criteria', {}).get('must_have_skills', []) + job.get('criteria', {}).get('nice_to_have_skills', [])
    candidate_skills = [normalize_skill(s) for s in candidate.get('skills', [])]
    norm_skills = {normalize_skill(s) for s in skills}
    mandatory = [s for s in job.get('criteria', {}).get('must_have_skills', [])]
    optional = job.get('criteria', {}).get('nice_to_have_skills', [])
    found_mandatory = sum(1 for s in mandatory if normalize_skill(s) in candidate_skills)
    found_optional = sum(1 for s in optional if normalize_skill(s) in candidate_skills)

    skill_score = 0.75 * (found_mandatory / max(len(mandatory), 1)) + 0.25 * (found_optional / max(len(optional), 1) if optional else 0)

    exp_months = float(candidate.get('experience_months', 0))
    required_exp = float(job.get('criteria', {}).get('min_experience_months', 0))
    experience_score = min(exp_months / required_exp, 1.0) if required_exp else 1.0

    education_level = int(candidate.get('education_level', 0))
    required_edu = int(job.get('criteria', {}).get('min_education_level', 0))
    if education_level >= required_edu:
        education_score = 1.0
    elif education_level == required_edu - 1:
        education_score = 0.5
    else:
        education_score = 0.0

    project_keywords = [p.lower() for p in job.get('criteria', {}).get('project_keywords', [])]
    matching_projects = sum(1 for project in candidate.get('projects', []) if any(word in project.lower() for word in project_keywords))
    projects_score = min(matching_projects / 2, 1.0)

    certs = job.get('criteria', {}).get('required_certifications', [])
    cert_score = 0.0
    if certs:
        found = sum(1 for cert in certs if cert.lower() in [c.lower() for c in candidate.get('certifications', [])])
        cert_score = found / len(certs)

    weights = job.get('weights', {'skills': 35, 'experience': 25, 'education': 15, 'projects': 15, 'certifications': 10})
    parts = {
        'skills': skill_score,
        'experience': experience_score,
        'education': education_score,
        'projects': projects_score,
        'certifications': cert_score,
    }
    if not certs:
        parts.pop('certifications', None)
    if not mandatory:
        parts['skills'] = 0.0
    weighted = sum(weights.get(k, 0) * v for k, v in parts.items())
    total_weight = sum(weights.get(k, 0) for k in parts)
    total_score = round((100 * weighted / total_weight), 1) if total_weight else 0.0

    return {
        'score': total_score,
        'breakdown': {k: round(float(v), 3) for k, v in parts.items()},
        'missing': [
            item for item in mandatory if normalize_skill(item) not in candidate_skills
        ],
        'evidence': candidate.get('evidence', []),
    }
