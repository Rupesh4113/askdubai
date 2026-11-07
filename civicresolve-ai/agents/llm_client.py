"""
CivicResolve AI - Unified LLM Client
Provides connectivity to local instruction-tuned models (Qwen2.5 / Llama3) via Ollama.
Includes fast connection checking, reachability caching, and deterministic fallbacks.
"""
import os
import json
import time
import httpx
from typing import Dict, Any, Optional

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "qwen2.5:7b-instruct")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "llama3.1:8b-instruct")

_OLLAMA_CHECK_CACHE = {"status": None, "last_check": 0.0}


def check_ollama_status(force_check: bool = False) -> Dict[str, Any]:
    """Checks if Ollama service is reachable and caches the result for 30 seconds."""
    now = time.time()
    if not force_check and _OLLAMA_CHECK_CACHE["status"] is not None:
        if now - _OLLAMA_CHECK_CACHE["last_check"] < 30.0:
            return _OLLAMA_CHECK_CACHE["status"]

    try:
        with httpx.Client(timeout=0.6) as client:
            resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                status_res = {
                    "available": True,
                    "url": OLLAMA_BASE_URL,
                    "models": models,
                    "active_model": PRIMARY_MODEL if any(PRIMARY_MODEL in m for m in models) else (models[0] if models else PRIMARY_MODEL)
                }
                _OLLAMA_CHECK_CACHE["status"] = status_res
                _OLLAMA_CHECK_CACHE["last_check"] = now
                return status_res
    except Exception:
        pass

    status_res = {
        "available": False,
        "url": OLLAMA_BASE_URL,
        "models": [],
        "active_model": "rule_based_precision_engine"
    }
    _OLLAMA_CHECK_CACHE["status"] = status_res
    _OLLAMA_CHECK_CACHE["last_check"] = now
    return status_res


def call_llm(prompt: str, system_prompt: str = "", model: Optional[str] = None) -> Optional[str]:
    """
    Calls local Ollama instance if available.
    Returns response string, or None if Ollama is unreachable.
    """
    status = check_ollama_status()
    if not status["available"]:
        return None

    model_to_use = model or status["active_model"]
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model_to_use,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9
        }
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
    except Exception:
        pass

    return None
