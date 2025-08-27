import os
import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


async def ollama_chat(messages, model: str = "llama3.1:8b", json_schema: dict | None = None) -> str:
    """
    Call Ollama chat API. If json_schema provided, leverage structured outputs by
    passing a JSON schema dict to 'format'. Returns the content string.
    """
    payload = {"model": model, "messages": messages, "stream": False}
    if json_schema is not None:
        payload["format"] = json_schema

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
