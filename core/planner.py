from typing import Optional, List
from rapidfuzz import fuzz
from core.schemas import Candidate

FIELD_QUESTION_BANK = {
    "full_name": ["May the full name be provided as on professional documents?"],
    "email": ["Could an email address be provided for follow-up?"],
    "phone": ["What is the best phone number for contact, including country code?"],
    "years_experience": ["How many years of professional experience are there (e.g., 3.5)?"],
    "desired_positions": ["Which position titles are currently targeted (e.g., Backend Engineer, Data Scientist)?"],
    "current_location": ["Which current city and country are preferred for work location?"],
    "tech_stack": ["Please list primary technologies: languages, frameworks, databases, tools (comma-separated)."],
}


def _select_best_question(field: str, history: List[str]) -> str:
    candidates = FIELD_QUESTION_BANK[field]
    if not history:
        return candidates
    last = history[-1]
    scored = sorted(candidates, key=lambda q: fuzz.partial_ratio(q, last))
    return scored


def next_intake_question(candidate: Candidate, asked_history: List[str]) -> Optional[str]:
    if not candidate.consent_given:
        return "Before proceeding, please confirm consent to process details strictly for screening purposes. Reply 'I agree' to continue."
    fields = [
        ("full_name", candidate.full_name),
        ("email", candidate.email),
        ("phone", candidate.phone),
        ("years_experience", candidate.years_experience),
        ("desired_positions", candidate.desired_positions),
        ("current_location", candidate.current_location),
        ("tech_stack", candidate.tech_stack),
    ]
    for fname, val in fields:
        if (val is None) or (isinstance(val, list) and not val):
            return _select_best_question(fname, asked_history)
    return None
