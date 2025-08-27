import json
import asyncio
import uuid
from typing import Dict, List
from core.nlp import ollama_chat
from core.schemas import AnswerScore
from tenacity import retry, stop_after_attempt, wait_exponential

def _scoring_schema():
    return {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "minimum": 0, "maximum": 10},
            "reasoning": {"type": "string"},
            "strengths": {
                "type": "array",
                "items": {"type": "string"}
            },
            "improvements": {
                "type": "array", 
                "items": {"type": "string"}
            }
        },
        "required": ["score", "reasoning", "strengths", "improvements"]
    }

def _extract_json(text: str) -> dict:
    """Extract JSON from response"""
    try:
        return json.loads(text)
    except:
        # Try to find JSON within the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
    
    # Fallback parsing
    return {
        "score": 5,
        "reasoning": "Unable to parse detailed scoring.",
        "strengths": ["Answer provided"],
        "improvements": ["Could provide more detail"]
    }

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
async def score_answer(question: str, answer: str, topic: str, difficulty: str, experience_years: float) -> AnswerScore:
    """
    Score a candidate's answer using Ollama LLM
    """
    
    scoring_prompt = {
        "question": question,
        "candidate_answer": answer,
        "topic": topic,
        "difficulty": difficulty,
        "candidate_experience": f"{experience_years} years",
        "scoring_criteria": {
            "technical_accuracy": 30,  # % weight
            "completeness": 25,
            "clarity": 20,
            "practical_understanding": 15,
            "examples_usage": 10
        },
        "instructions": [
            "Score the answer from 0-10 based on technical accuracy, completeness, and clarity",
            "Consider the candidate's experience level when scoring",
            "Provide specific strengths and improvement suggestions",
            "Be fair but thorough in evaluation",
            f"For {difficulty} difficulty questions, adjust expectations accordingly"
        ]
    }
    
    messages = [
        {
            "role": "system", 
            "content": (
                "You are an expert technical interviewer and evaluator. "
                "Score candidate answers objectively and provide constructive feedback. "
                "Consider the difficulty level and candidate's experience when scoring. "
                "Use the full 0-10 scale appropriately."
            )
        },
        {
            "role": "user", 
            "content": json.dumps(scoring_prompt, indent=2)
        }
    ]
    
    try:
        response = await ollama_chat(messages, json_schema=_scoring_schema())
        score_data = _extract_json(response)
        
        return AnswerScore(
            score=max(0, min(10, score_data.get("score", 5))),  # Ensure 0-10 range
            reasoning=score_data.get("reasoning", "No detailed reasoning provided"),
            strengths=score_data.get("strengths", []),
            improvements=score_data.get("improvements", [])
        )
        
    except Exception as e:
        print(f"Error scoring answer: {e}")
        # Fallback scoring based on answer quality
        return simple_score_answer(answer, topic, difficulty)

def simple_score_answer(answer: str, topic: str = "technical", difficulty: str = "medium") -> AnswerScore:
    """Simple rule-based scoring for fallback"""
    answer_length = len(answer.strip())
    word_count = len(answer.split())
    
    # Basic scoring logic based on answer characteristics
    score = 5  # Default neutral score
    strengths = []
    improvements = []
    reasoning = ""
    
    if answer_length < 20:
        score = 3
        reasoning = "Answer is too brief for a technical question"
        improvements = ["Provide more detailed explanation", "Include examples or use cases"]
    elif answer_length < 50:
        score = 5
        reasoning = "Answer has basic content but lacks depth"
        improvements = ["Add more technical details", "Explain the reasoning behind your answer"]
        strengths = ["Clear and concise"]
    elif answer_length < 150:
        score = 7
        reasoning = "Good comprehensive answer with adequate detail"
        strengths = ["Well-structured response", "Good level of detail"]
        improvements = ["Could include more specific examples"]
    else:
        score = 8
        reasoning = "Comprehensive and detailed answer"
        strengths = ["Thorough explanation", "Good depth of knowledge"]
        improvements = ["Excellent detail level"]
    
    # Adjust for difficulty
    if difficulty == "easy" and score >= 6:
        score = min(10, score + 1)
    elif difficulty == "hard" and score <= 7:
        score = max(1, score - 1)
    
    return AnswerScore(
        score=score,
        reasoning=reasoning,
        strengths=strengths,
        improvements=improvements
    )

async def calculate_overall_score(scores: Dict[str, AnswerScore]) -> float:
    """Calculate overall candidate score"""
    if not scores:
        return 0.0
    
    total_score = sum(score.score for score in scores.values())
    return round(total_score / len(scores), 1)
