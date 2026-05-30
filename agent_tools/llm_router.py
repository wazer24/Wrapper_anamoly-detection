"""Dual-LLM router: Nemotron (primary, self-hosted) or Gemini Flash (fallback).
Controlled by LLM_PROVIDER env var: 'nemotron' or 'gemini' (default).
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class LLMResponse:
    def __init__(self, text: str, model_used: str, success: bool) -> None:
        self.text = text
        self.model_used = model_used
        self.success = success


def _call_nemotron(prompt: str, response_mime_type: Optional[str] = None) -> LLMResponse:
    api_key = os.environ.get("FALLBACK_API_KEY", "")
    endpoint = os.environ.get("FALLBACK_ENDPOINT", "https://api.groq.com/openai/v1")
    model = os.environ.get("FALLBACK_MODEL", "llama-3.3-70b-versatile")
    if not api_key:
        return LLMResponse(text="", model_used="fallback", success=False)
    try:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url=endpoint)
        kwargs: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        if response_mime_type == "application/json":
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        return LLMResponse(text=text, model_used=f"fallback/{model}", success=True)
    except Exception as e:
        logger.warning("[LLMRouter] Fallback call failed: %s", e)
        return LLMResponse(text="", model_used="fallback", success=False)


def _call_gemini(prompt: str, response_mime_type: Optional[str] = None) -> LLMResponse:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return LLMResponse(text="", model_used="gemini", success=False)
    try:
        import google.genai as genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(temperature=0.2)
        if response_mime_type == "application/json":
            config.response_mime_type = "application/json"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )
        text = response.text
        return LLMResponse(text=text or "", model_used="gemini/gemini-2.5-flash", success=True)
    except Exception as e:
        logger.warning("[LLMRouter] Gemini call failed: %s", e)
        return LLMResponse(text="", model_used="gemini", success=False)


def generate(prompt: str, response_mime_type: Optional[str] = None) -> LLMResponse:
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider == "nemotron":
        result = _call_nemotron(prompt, response_mime_type)
        if result.success:
            return result
        logger.info("[LLMRouter] Nemotron failed, falling back to Gemini")
        result = _call_gemini(prompt, response_mime_type)
        if result.success:
            return result
    else:
        result = _call_gemini(prompt, response_mime_type)
        if result.success:
            return result
        logger.info("[LLMRouter] Gemini failed, falling back to Nemotron")
        result = _call_nemotron(prompt, response_mime_type)
        if result.success:
            return result
    return LLMResponse(
        text=json.dumps({
            "diagnosis": {
                "root_cause_category": "unknown",
                "is_database_index_problem": False,
                "required_fix_layer": "unknown",
                "estimated_baseline_execution_time_ms": 0.0,
                "primary_bottleneck": "LLM unavailable",
            },
            "hypotheses": [],
            "winning_hypothesis": {},
        }),
        model_used="fallback",
        success=False,
    )
