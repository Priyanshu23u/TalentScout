from cryptography.fernet import Fernet
import os
import json
import re

def get_key():
    """Get encryption key from environment or generate new one"""
    key = os.getenv("APP_ENC_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        # In production, this should be properly stored
    return key

FERNET = Fernet(get_key().encode())

def encrypt(data: dict) -> bytes:
    """Encrypt dictionary data"""
    return FERNET.encrypt(json.dumps(data).encode())

def decrypt(token: bytes) -> dict:
    """Decrypt data back to dictionary"""
    return json.loads(FERNET.decrypt(token).decode())

def mask_email(email: str) -> str:
    """Mask email address for privacy"""
    if not email or "@" not in email:
        return email
    
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    
    return f"{masked_name}@{domain}"

def mask_phone(phone: str) -> str:
    """Mask phone number for privacy"""
    if not phone:
        return phone
    
    # Remove non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    if len(cleaned) <= 4:
        return "*" * len(cleaned)
    
    # Show country code if present and last 4 digits
    if cleaned.startswith('+'):
        if len(cleaned) <= 6:
            return cleaned[0:2] + "*" * (len(cleaned) - 4) + cleaned[-2:]
        return cleaned[0:2] + "*" * (len(cleaned) - 6) + cleaned[-4:]
    else:
        return "*" * (len(cleaned) - 4) + cleaned[-4:]

def sanitize_input(text: str) -> str:
    """Basic input sanitization"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove potentially harmful characters
    text = re.sub(r'[<>{}[\]\\]', '', text)
    
    return text[:1000]  # Limit length

def validate_phone_format(phone: str) -> bool:
    """Validate phone number format"""
    if not phone:
        return False
    
    # Clean the phone number
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Check basic format
    if len(cleaned) < 6 or len(cleaned) > 20:
        return False
    
    # Should start with + or digit
    if not (cleaned[0].isdigit() or cleaned[0] == '+'):
        return False
    
    return True

def validate_email_format(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.lower()))
