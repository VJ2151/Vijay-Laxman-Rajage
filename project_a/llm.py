"""Gemini API client with disk caching, retry backoff, and JSON logging."""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from project_a.config import CACHE_DIR, MODEL_ID, RESULTS_DIR


def get_cache_key(model: str, prompt: str, user_input: str) -> str:
    """Generate SHA256 cache key from model, prompt, and input."""
    payload = f"{model}::{prompt}::{user_input}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def call_gemini(
    prompt: str,
    user_input: str = "",
    model: str = MODEL_ID,
    bypass_cache: bool = False,
    max_retries: int = 3,
) -> dict:
    """Call Gemini API with temperature 0, JSON output, caching, and logging."""
    cache_key = get_cache_key(model, prompt, user_input)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    log_file = RESULTS_DIR / "llm_log.jsonl"
    full_prompt = f"{prompt}\n\nInput:\n{user_input}" if user_input else prompt

    # Check cache if bypass_cache is False
    if not bypass_cache and cache_file.exists():
        t0 = time.perf_counter()
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        _append_log(log_file, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "cache_hit": True,
            "latency_ms": round(latency_ms, 3),
            "input_tokens": cached_data.get("input_tokens", 0),
            "output_tokens": cached_data.get("output_tokens", 0),
        })
        return cached_data.get("response", {})

    # Live call required
    if os.environ.get("GEMINI_OFFLINE_ONLY") == "1":
        raise RuntimeError(
            f"Offline cache miss for key {cache_key}. Live API calls are explicitly disabled in offline mode."
        )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment or .env file.")

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
    )

    backoff = 2.0
    for attempt in range(max_retries):
        try:
            t0 = time.perf_counter()
            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=config,
            )
            latency_ms = (time.perf_counter() - t0) * 1000.0
            break
        except APIError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff)
            backoff *= 2.0

    raw_text = response.text or "{}"
    try:
        parsed_json = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed_json = {"raw_text": raw_text}

    usage = getattr(response, "usage_metadata", None)
    input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
    output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

    # Write to disk cache (contains no secrets or API keys)
    cache_payload = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "response": parsed_json,
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_payload, f, indent=2)

    _append_log(log_file, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "cache_hit": False,
        "latency_ms": round(latency_ms, 3),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    })

    return parsed_json


def _append_log(log_file: Path, entry: dict) -> None:
    """Safely append a single JSON log line."""
    log_file.parent.mkdir(exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
