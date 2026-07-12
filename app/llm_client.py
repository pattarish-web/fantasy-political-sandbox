import os
import json
import random
import time
from groq import Groq
from app import config
from pydantic import BaseModel

def _get_groq_client() -> Groq:
    keys = config.get_api_keys()
    if not keys:
        raise ValueError("GROQ_API_KEY environment variable is missing.")
    # Simple random round-robin if multiple keys
    key = random.choice(keys)
    return Groq(api_key=key)

def call_llm(prompt: str, response_schema: type[BaseModel] | None = None) -> str:
    """
    Call Groq LLM and optionally enforce JSON schema.
    """
    client = _get_groq_client()
    model = config.MODEL_NAME

    messages = []
    
    if response_schema:
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2, ensure_ascii=False)
        sys_msg = f"You are a helpful assistant. You MUST return ONLY valid JSON that matches the following JSON Schema:\n{schema_json}"
        messages.append({"role": "system", "content": sys_msg})
    else:
        messages.append({"role": "system", "content": "You are a helpful assistant. Output ONLY valid JSON."})
        
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=8000,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        time.sleep(2)
        raise e

def clean_json_response(text: str) -> dict:
    """
    Fallback JSON cleaner.
    """
    if not text:
        return {}
    
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        
    try:
        return json.loads(text)
    except Exception as e:
        print(f"Error parsing fallback JSON: {e}")
        return {}
