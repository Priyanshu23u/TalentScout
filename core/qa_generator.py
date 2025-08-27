import json
from typing import List
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential
from core.schemas import QASet, QAQuestion
from core.nlp import ollama_chat


def _schema_dict():
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "question": {"type": "string"},
                        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                    },
                    "required": ["topic", "question", "difficulty"],
                },
            }
        },
        "required": ["items"],
    }


def _best_effort_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
        return None


def _fallback_items(stack: List[str], k: int) -> List[QAQuestion]:
    base = stack or ["general software engineering"]
    out = []
    for t in base[:k]:
        out.append(
            QAQuestion(
                topic=t,
                question=f"Briefly explain core principles of {t}.",
                difficulty="medium",
            )
        )
    return out


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=False)
async def generate_stack_questions(stack: List[str], k: int = 5) -> QASet:
    stack = [s.strip() for s in stack if s and s.strip()]

    user_payload = {
        "technologies": stack,
        "context_snippets": [
            "Focus on practical, short screening questions.",
            "Prefer breadth when multiple technologies are listed.",
            "Avoid trick questions; use clear wording.",
        ],
        "count": k,
        "difficulty_mix": {"easy": 1, "medium": 3, "hard": 1},
        "format": {"type": "json", "schema": {"items": [{"topic": "str", "question": "str", "difficulty": "easy|medium|hard"}]}},
    }

    messages = [
        {"role": "system", "content": "Generate concise, focused technical screening questions tied to the provided technologies and context."},
        {"role": "user", "content": json.dumps(user_payload)},
    ]

    raw = await ollama_chat(messages, json_schema=_schema_dict())
    data = _best_effort_json(raw)

    items = []
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        for it in data["items"]:
            try:
                items.append(QAQuestion(**it))
            except ValidationError:
                continue

    if not items:
        items = _fallback_items(stack, k)

    return QASet(items=items[:k])
