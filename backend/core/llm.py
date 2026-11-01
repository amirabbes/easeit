import json
import re
import unicodedata
from typing import Any

INJECTION_PATTERNS = [
    r'ignore (all )?(previous|prior) instructions',
    r'system prompt',
    r'you are now',
    r'send (an )?email',
    r'give (me|this candidate) the highest score',
    r'ignorez? (toutes? )?les instructions',
    r'note maximale',
    r'envoie[rz]? (un )?(mail|email)'
]
ZERO_WIDTH = {ord(ch): None for ch in '\u200b\u200c\u200d\u2060\ufeff'}


def sanitize_text(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    cleaned = unicodedata.normalize('NFKC', text).translate(ZERO_WIDTH)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', cleaned)
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned, re.I):
            flags.append('PROMPT_INJECTION_SUSPECTED')
            break
    return cleaned, flags


def classify_message(body: str, sender: str | None = None) -> dict[str, Any]:
    text = sanitize_text(body)[0].lower()

    if 'candidature' in text or 'cv' in text or 'application' in text:
        return {
            'category': 'RECRUITMENT',
            'intent': 'NEW_APPLICATION',
            'priority': 'MEDIUM',
            'destination': 'ATS_AGENT',
            'confidence': 0.84,
            'reason': 'Nouveau message candidat ou CV reçu.'
        }

    if ('interview' in text or 'entretien' in text) and ('report' in text or 'deplacer' in text or 'déplacer' in text or 'reporter' in text or 'reschedule' in text):
        priority = 'URGENT' if 'demain' in text or 'tomorrow' in text or 'today' in text else 'MEDIUM'
        return {
            'category': 'RECRUITMENT',
            'intent': 'INTERVIEW_CHANGE',
            'priority': priority,
            'destination': 'URGENT_AGENT',
            'confidence': 0.91,
            'reason': 'Demande de replanification d’entretien détectée.'
        }

    if any(k in text for k in ['conge', 'congé', 'vacation', 'leave', 'absence', 'days off', 'rtte', 'rtt']):
        return {
            'category': 'EMPLOYEE',
            'intent': 'POLICY_QUESTION',
            'priority': 'MEDIUM',
            'destination': 'EMPLOYEE_AGENT',
            'confidence': 0.8,
            'reason': 'Question RH ou congés identifiée.'
        }

    if 'salary' in text or 'salaire' in text or 'pay' in text:
        return {
            'category': 'EMPLOYEE',
            'intent': 'OTHER',
            'priority': 'MEDIUM',
            'destination': 'HUMAN_REVIEW',
            'confidence': 0.52,
            'reason': 'Demande sensible hors périmètre du MVP.'
        }

    return {
        'category': 'OTHER',
        'intent': 'OTHER',
        'priority': 'INFORMATION',
        'destination': 'HUMAN_REVIEW',
        'confidence': 0.55,
        'reason': 'Message non classé automatiquement.'
    }


def build_digest_html(groups: list[dict[str, Any]]) -> str:
    rows = []
    for group in groups:
        rows.append(f"<div class='group'><h3>{group['title']}</h3><ul>{''.join(f'<li>{item}</li>' for item in group['items'])}</ul></div>")
    return '<div class="digest">' + ''.join(rows) + '</div>'


def employee_support_answer(question: str, user_role: str, user_name: str) -> dict[str, Any]:
    q = ''.join(
        character
        for character in unicodedata.normalize('NFKD', question.lower())
        if not unicodedata.combining(character)
    )
    if any(term in q for term in ('conge', 'leave', 'vacation')):
        return {
            'answer': (
                f"Bonjour {user_name}, la politique prévoit 25 jours de congés par an. "
                "Je ne peux pas consulter votre solde personnel ici ; contactez votre responsable "
                "ou le service RH pour le confirmer."
            ),
            'sources': ['Politique congés'],
            'answerable': True,
            'escalated': False,
        }

    return {
        'answer': 'Je ne peux pas répondre avec certitude à partir des informations RH disponibles. Votre demande a été transmise à l’équipe RH.',
        'sources': [],
        'answerable': False,
        'escalated': True,
    }
