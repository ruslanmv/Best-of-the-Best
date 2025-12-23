#!/usr/bin/env python3
"""
tests/test_provider.py

Loads .env from project root and tests ALL configured LLM providers that are
"enabled" via environment variables.

It will test:
  - Ollama      (if OLLAMA_HOST is set OR NEWS_LLM_MODEL starts with "ollama/")
  - OpenAI      (if OPENAI_API_KEY is set)
  - Anthropic   (if ANTHROPIC_API_KEY is set)
  - watsonx.ai  (if WATSONX_APIKEY + WATSONX_URL + WATSONX_PROJECT_ID are set)

Prompt:
  "What is the capital of Italy? Reply with only the city name."

Usage:
  python tests/test_provider.py

Exit codes:
  0  -> all enabled providers passed
  1  -> at least one enabled provider failed
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import requests


PROMPT = "What is the capital of Italy? Reply with only the city name."
TIMEOUT = int(os.environ.get("LLM_TEST_TIMEOUT", "120"))


def load_env() -> None:
    """Load .env from project root (without overriding existing env vars)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        raise RuntimeError("python-dotenv is required: pip install python-dotenv")

    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    if not env_path.exists():
        raise RuntimeError(f"No .env found at {env_path}")

    load_dotenv(env_path, override=False)


def _strip_provider_prefix(model: str, provider: str) -> str:
    """
    Convert 'ollama/llama3:8b' -> 'llama3:8b'
    Keep other providers unchanged unless they also use prefixes.
    """
    prefix = provider + "/"
    return model.split("/", 1)[1] if model.startswith(prefix) else model


def _short(s: str, n: int = 220) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 3] + "..."


@dataclass
class TestResult:
    provider: str
    ok: bool
    model: str
    answer: str = ""
    error: str = ""


# ---------------------------
# OLLAMA
# ---------------------------
def is_ollama_enabled() -> bool:
    model = os.environ.get("NEWS_LLM_MODEL", "")
    return bool(os.environ.get("OLLAMA_HOST")) or model.startswith("ollama/")


def test_ollama() -> TestResult:
    base_url = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("NEWS_LLM_MODEL", "ollama/llama3:8b")

    if not model.startswith("ollama/"):
        # If user didn't set NEWS_LLM_MODEL to ollama/*, still allow Ollama test
        # by using a fallback model name (common default).
        model = "ollama/llama3:8b"

    ollama_model = _strip_provider_prefix(model, "ollama")
    url = f"{base_url}/api/generate"
    payload = {"model": ollama_model, "prompt": PROMPT, "stream": False}

    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        answer = (data.get("response") or "").strip()
        ok = bool(answer)
        return TestResult("ollama", ok=ok, model=ollama_model, answer=answer)
    except Exception as e:
        return TestResult("ollama", ok=False, model=ollama_model, error=str(e))


# ---------------------------
# OPENAI (Chat Completions API)
# ---------------------------
def is_openai_enabled() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def test_openai() -> TestResult:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    # Allow a dedicated test model override; otherwise pick a safe default
    model = (
        os.environ.get("OPENAI_TEST_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or "gpt-4o-mini"
    )

    url = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
    url = f"{url}/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": PROMPT},
        ],
        "temperature": float(os.environ.get("NEWS_LLM_TEMPERATURE", "0.2")),
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        answer = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        ok = bool(answer)
        return TestResult("openai", ok=ok, model=model, answer=answer)
    except Exception as e:
        return TestResult("openai", ok=False, model=model, error=str(e))


# ---------------------------
# ANTHROPIC (Messages API)
# ---------------------------
def is_anthropic_enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def test_anthropic() -> TestResult:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model = (
        os.environ.get("ANTHROPIC_TEST_MODEL")
        or os.environ.get("ANTHROPIC_MODEL")
        or "claude-3-5-sonnet-latest"
    )

    # Anthropic Messages API endpoint
    url = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
    url = f"{url}/v1/messages"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": os.environ.get("ANTHROPIC_VERSION", "2023-06-01"),
        "content-type": "application/json",
    }

    payload = {
        "model": model,
        "max_tokens": int(os.environ.get("ANTHROPIC_MAX_TOKENS", "64")),
        "temperature": float(os.environ.get("NEWS_LLM_TEMPERATURE", "0.2")),
        "messages": [{"role": "user", "content": PROMPT}],
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        # Response content is typically a list of blocks
        blocks = data.get("content", [])
        answer = ""
        for b in blocks:
            if isinstance(b, dict) and b.get("type") == "text":
                answer += b.get("text", "")
        answer = answer.strip()

        ok = bool(answer)
        return TestResult("anthropic", ok=ok, model=model, answer=answer)
    except Exception as e:
        return TestResult("anthropic", ok=False, model=model, error=str(e))


# ---------------------------
# WATSONX.AI (IBM Cloud IAM + text generation)
# ---------------------------
def is_watsonx_enabled() -> bool:
    return bool(
        os.environ.get("WATSONX_APIKEY")
        and os.environ.get("WATSONX_URL")
        and os.environ.get("WATSONX_PROJECT_ID")
    )


def _watsonx_get_iam_token(apikey: str) -> str:
    """
    Exchange IBM Cloud API key for an IAM access token.
    """
    token_url = os.environ.get("IBM_IAM_TOKEN_URL", "https://iam.cloud.ibm.com/identity/token")
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": apikey,
    }
    r = requests.post(token_url, headers=headers, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    j = r.json()
    token = j.get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in IAM response: {j}")
    return token


def test_watsonx() -> TestResult:
    apikey = os.environ.get("WATSONX_APIKEY", "")
    base_url = os.environ.get("WATSONX_URL", "").rstrip("/")
    project_id = os.environ.get("WATSONX_PROJECT_ID", "")

    # Watsonx model id (NOT prefixed with watsonx/ in the REST API call)
    model_id = (
        os.environ.get("WATSONX_TEST_MODEL_ID")
        or os.environ.get("WATSONX_MODEL_ID")
        or "ibm/granite-3-8b-instruct"
    )

    # Version is required by watsonx REST endpoints
    version = os.environ.get("WATSONX_VERSION", "2025-02-11")

    # Text generation endpoint (watsonx.ai SaaS)
    url = f"{base_url}/ml/v1/text/generation?version={version}"

    try:
        token = _watsonx_get_iam_token(apikey)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "input": PROMPT,
            "model_id": model_id,
            "project_id": project_id,
            "parameters": {
                "max_new_tokens": int(os.environ.get("WATSONX_MAX_NEW_TOKENS", "32")),
                "temperature": float(os.environ.get("NEWS_LLM_TEMPERATURE", "0.2")),
            },
        }

        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()

        # Typical response includes 'results': [{'generated_text': '...'}]
        results = data.get("results", [])
        answer = ""
        if results and isinstance(results, list) and isinstance(results[0], dict):
            answer = (results[0].get("generated_text") or "").strip()

        ok = bool(answer)
        return TestResult("watsonx", ok=ok, model=model_id, answer=answer)

    except Exception as e:
        return TestResult("watsonx", ok=False, model=model_id, error=str(e))


def main() -> None:
    load_env()

    tests = []
    if is_ollama_enabled():
        tests.append(test_ollama)
    if is_openai_enabled():
        tests.append(test_openai)
    if is_anthropic_enabled():
        tests.append(test_anthropic)
    if is_watsonx_enabled():
        tests.append(test_watsonx)

    if not tests:
        print("⚠️  No providers appear enabled from .env. Nothing to test.")
        print("   Enable at least one of: OLLAMA_HOST, OPENAI_API_KEY, ANTHROPIC_API_KEY, WATSONX_*")
        sys.exit(1)

    results: list[TestResult] = []
    for fn in tests:
        res = fn()
        results.append(res)

    print("\n==================== Provider Test Results ====================")
    failed = 0
    for r in results:
        if r.ok:
            print(f"✅ {r.provider:<9} OK   | model={r.model} | answer={_short(r.answer)}")
        else:
            failed += 1
            print(f"❌ {r.provider:<9} FAIL | model={r.model} | error={_short(r.error)}")

    print("==============================================================\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
