EXIT_KEYWORDS = {"quit", "exit", "bye", "stop", "goodbye", "end", "finish", "done"}

INTAKE_ORDER = [
    "INTAKE_NAME",
    "INTAKE_EMAIL", 
    "INTAKE_PHONE",
    "INTAKE_YOE",
    "INTAKE_POSITION",
    "INTAKE_LOCATION",
    "INTAKE_TECH",
]

def detect_exit(text: str) -> bool:
    """Detect if user wants to exit the conversation"""
    if not text:
        return False
    
    t = text.strip().lower()
    
    # Check for exact matches
    if t in EXIT_KEYWORDS:
        return True
    
    # Check for phrases containing exit keywords
    return any(keyword in t for keyword in EXIT_KEYWORDS)

def next_step(candidate, state):
    """Determine the next step in the conversation flow"""
    
    # Always check consent first
    if not candidate.consent_given:
        return "CONSENT"
    
    # Check each required field in order
    for step in INTAKE_ORDER:
        field_mapping = {
            "INTAKE_NAME": "full_name",
            "INTAKE_EMAIL": "email", 
            "INTAKE_PHONE": "phone",
            "INTAKE_YOE": "years_experience",
            "INTAKE_POSITION": "desired_positions",
            "INTAKE_LOCATION": "current_location",
            "INTAKE_TECH": "tech_stack",
        }
        
        field = field_mapping[step]
        val = getattr(candidate, field)
        
        # Check if field is empty/None
        if val is None or (isinstance(val, list) and not val) or (isinstance(val, str) and not val.strip()):
            return step
    
    # All intake complete, generate questions
    return "GENERATE_QA"

def is_intake_complete(candidate) -> bool:
    """Check if all required intake fields are completed"""
    required_fields = [
        ("full_name", str),
        ("email", str), 
        ("phone", str),
        ("years_experience", (int, float)),
        ("desired_positions", list),
        ("current_location", str),
        ("tech_stack", list),
    ]
    
    for field_name, field_type in required_fields:
        val = getattr(candidate, field_name, None)
        
        if val is None:
            return False
        
        if field_type == str and not val.strip():
            return False
        
        if field_type == list and not val:
            return False
    
    return candidate.consent_given
