from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, EmailStr, Field
from pydantic import field_validator, model_validator

class AnswerScore(BaseModel):
    score: int = Field(ge=0, le=10)  # Score out of 10
    reasoning: str  # Why this score was given
    strengths: List[str] = []  # What was good
    improvements: List[str] = []  # What could be better

class Candidate(BaseModel):
    full_name: str | None = Field(default=None)
    email: EmailStr | None = None
    phone: str | None = None
    years_experience: float | None = None
    desired_positions: List[str] = []
    current_location: str | None = None
    tech_stack: List[str] = []
    consent_given: bool = False
    
    # NEW: Store technical question answers with scoring
    technical_questions: List[Dict] = Field(default_factory=list)
    technical_answers: Dict[str, str] = Field(default_factory=dict)  # question_id -> answer
    answer_scores: Dict[str, AnswerScore] = Field(default_factory=dict)  # question_id -> score
    overall_score: float | None = None  # Average of all scores
    additional_comments: str | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        if v is None:
            return v
        return "".join(ch for ch in str(v) if ch.isdigit() or ch == "+")[:20]

    @field_validator("desired_positions", mode="before")
    @classmethod
    def norm_positions(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            v = [s.strip() for s in v.split(",")]
        return [s for s in (x.strip() for x in v) if s]

    @field_validator("tech_stack", mode="before")
    @classmethod
    def norm_stack(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            v = [s.strip() for s in v.split(",")]
        return [s for s in (x.strip() for x in v) if s]

    @model_validator(mode="after")
    def non_negative_years(self):
        if self.years_experience is not None and self.years_experience < 0:
            raise ValueError("years_experience must be non-negative")
        return self

class QAQuestion(BaseModel):
    topic: str
    question: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_id: str | None = None  # Unique identifier for tracking answers

class QASet(BaseModel):
    items: List[QAQuestion]

class ConversationState(BaseModel):
    step: Literal[
        "GREETING",
        "CONSENT",
        "INTAKE_NAME",
        "INTAKE_EMAIL",
        "INTAKE_PHONE",
        "INTAKE_YOE",
        "INTAKE_POSITION",
        "INTAKE_LOCATION",
        "INTAKE_TECH",
        "GENERATE_QA",
        "TECHNICAL_QA",  # State for collecting technical answers
        "FOLLOWUP",
        "END",
    ] = "GREETING"
    exit_detected: bool = False
    current_question_index: int = 0  # Track which question we're asking
    questions_asked: bool = False  # Track if questions have been displayed
