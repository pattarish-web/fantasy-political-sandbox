import os
import json
import random
import time
from groq import Groq
import google.generativeai as genai
from openai import OpenAI
from app import config
from pydantic import BaseModel


def _gemini_response_schema(response_schema: type[BaseModel]) -> dict:
    """Return a JSON Schema safe to include in a Gemini prompt.

    The legacy Gemini SDK rejects Pydantic's ``default`` keyword when it is
    passed through its structured-output ``response_schema`` conversion.
    """
    def strip_defaults(value):
        if isinstance(value, dict):
            return {
                key: strip_defaults(child)
                for key, child in value.items()
                if key != "default"
            }
        if isinstance(value, list):
            return [strip_defaults(child) for child in value]
        return value

    return strip_defaults(response_schema.model_json_schema())


def _call_groq(prompt: str, key: str, response_schema: type[BaseModel] | None = None) -> str:
    client = Groq(api_key=key)
    model = config.MODEL_NAME

    messages = []
    
    if response_schema:
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2, ensure_ascii=False)
        sys_msg = f"You are a helpful assistant. You MUST return ONLY valid JSON that matches the following JSON Schema:\n{schema_json}"
        messages.append({"role": "system", "content": sys_msg})
    else:
        messages.append({"role": "system", "content": "You are a helpful assistant. Output ONLY valid JSON."})
        
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=8000,
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Groq returned None content")
    return content

def _call_gemini(prompt: str, key: str, response_schema: type[BaseModel] | None = None) -> str:
    genai.configure(api_key=key)
    
    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 8000,
        "response_mime_type": "application/json",
    }
    
    if response_schema:
        # Do not pass Pydantic models to the deprecated Gemini SDK's
        # response_schema adapter: it rejects fields such as `default`.
        # JSON MIME mode plus an explicit prompt retains the existing output
        # contract without invoking that broken adapter.
        schema_json = json.dumps(
            _gemini_response_schema(response_schema), ensure_ascii=False
        )
        prompt = (
            "Return ONLY valid JSON matching this JSON Schema:\n"
            f"{schema_json}\n\n{prompt}"
        )
        
    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL_NAME,
        generation_config=generation_config,
    )
    
    response = model.generate_content(prompt)
    content = response.text
    if content is None:
        raise ValueError("Gemini returned None content")
    return content


def _call_openai(prompt: str, key: str, response_schema: type[BaseModel] | None = None) -> str:
    messages = [{"role": "system", "content": "You are a helpful assistant. Output ONLY valid JSON."}]
    if response_schema:
        schema_json = json.dumps(response_schema.model_json_schema(), ensure_ascii=False)
        messages[0]["content"] += f" Match this JSON Schema:\n{schema_json}"
    messages.append({"role": "user", "content": prompt})

    response = OpenAI(api_key=key).chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        max_completion_tokens=8000,
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("OpenAI returned None content")
    return content


def call_llm(prompt: str, response_schema: type[BaseModel] | None = None) -> str:
    """
    Call LLM with Fallback Logic:
    1. Try all available Groq keys.
    2. If all Groq keys fail (e.g. rate limit), fallback to try all Gemini keys.
    3. If Gemini fails, fallback to OpenAI.
    """
    if os.getenv("LLM_PROVIDER", "").lower() == "openai":
        openai_key = config.get_openai_api_key()
        if not openai_key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is unavailable")
        print("[LLM] OpenAI-only mode")
        return _call_openai(prompt, openai_key, response_schema)

    groq_keys = config.get_api_keys()
    gemini_keys = config.get_gemini_api_keys()
    
    # Try Groq keys first
    random.shuffle(groq_keys)
    for key in groq_keys:
        try:
            print("[LLM] Trying Groq...")
            return _call_groq(prompt, key, response_schema)
        except Exception as e:
            print(f"[LLM] Groq Error: {e}")
            err_str = str(e).lower()
            if any(term in err_str for term in ("authentication", "invalid api key", "unauthorized", "401")):
                print(f"[LLM] Fatal auth error for Groq key, skipping: {e}")
                continue
            time.sleep(1)
            
    # Fallback to Gemini keys
    random.shuffle(gemini_keys)
    for key in gemini_keys:
        try:
            print("[LLM] Falling back to Gemini...")
            return _call_gemini(prompt, key, response_schema)
        except Exception as e:
            print(f"[LLM] Gemini Error: {e}")
            err_str = str(e).lower()
            if any(term in err_str for term in ("authentication", "invalid api key", "unauthorized", "401")):
                print(f"[LLM] Fatal auth error for Gemini key, skipping: {e}")
                continue
            time.sleep(1)

    openai_key = config.get_openai_api_key()
    if openai_key:
        try:
            print("[LLM] Falling back to OpenAI...")
            return _call_openai(prompt, openai_key, response_schema)
        except Exception as e:
            print(f"[LLM] OpenAI Error: {e}")

    raise RuntimeError("All LLM API keys (Groq, Gemini, and OpenAI) have failed or are unavailable.")

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
