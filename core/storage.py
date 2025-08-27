import os
import orjson
import json
from datetime import datetime

DATA_FILE = os.getenv("DATA_FILE", "data/candidates.jsonl")

def save_candidate(candidate_dict: dict) -> None:
    """Save candidate data to JSONL file"""
    try:
        # Ensure directory exists
        directory = os.path.dirname(DATA_FILE)
        if directory:  # Only create if there's actually a directory path
            os.makedirs(directory, exist_ok=True)
        
        # Add timestamp
        candidate_dict["submitted_at"] = datetime.now().isoformat()
        
        # Save to file
        with open(DATA_FILE, "ab") as f:
            f.write(orjson.dumps(candidate_dict) + b"\n")
        
        print(f"✅ Candidate data saved to: {os.path.abspath(DATA_FILE)}")
        
    except Exception as e:
        print(f"❌ Error saving candidate: {str(e)}")
        raise e

def load_candidates() -> list:
    """Load all candidates from JSONL file"""
    candidates = []
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as f:
                for line in f:
                    if line.strip():
                        candidate = orjson.loads(line)
                        candidates.append(candidate)
        return candidates
    except Exception as e:
        print(f"❌ Error loading candidates: {str(e)}")
        return []

def get_candidate_count() -> int:
    """Get total number of saved candidates"""
    return len(load_candidates())
