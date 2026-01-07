#!/usr/bin/env python3
"""
scripts/llm_client.py

Multi-provider LLM client for Best-of-the-Best blog generation.

Providers:
  - Local Ollama:      model="ollama/<model>"
  - OpenAI:            model="openai/<model>"
  - Anthropic:         model="anthropic/<model>"
  - IBM watsonx.ai:    model="watsonx/<model>"

Selection (in order):
  1) NEWS_LLM_MODEL  (recommended)  e.g. "watsonx/meta-llama/llama-3-3-70b-instruct"
  2) LLM_MODEL
  3) NEWS_LLM_PROVIDER + NEWS_LLM_MODEL (if you prefer splitting provider/model)
  4) default: "ollama/gemma:2b"

Environment variables:
  - NEWS_LLM_MODEL
  - NEWS_LLM_PROVIDER   (optional: ollama|openai|anthropic|watsonx)
  - NEWS_LLM_TEMPERATURE (optional, float)

Ollama:
  - OLLAMA_HOST or OLLAMA_API_BASE (default http://127.0.0.1:11434)

watsonx.ai:
  - WATSONX_APIKEY
  - WATSONX_URL (e.g. https://us-south.ml.cloud.ibm.com)
  - WATSONX_PROJECT_ID

Note:
CrewAI's LLM uses LiteLLM under the hood for most hosted providers.
For watsonx, LiteLLM commonly reads credentials from env vars, but we also pass
what we can as kwargs for robustness.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Optional, Tuple

from crewai import LLM


def _safe_float(env_name: str, default: float) -> float:
    raw = os.environ.get(env_name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        print(
            f"[llm_client] ⚠️  Invalid value for {env_name}={raw!r}; using {default}",
            file=sys.stderr,
        )
        return default


def _normalize_model(provider: Optional[str], model: str) -> str:
    """
    If user sets NEWS_LLM_PROVIDER=watsonx and NEWS_LLM_MODEL=meta-llama/...
    we normalize to watsonx/meta-llama/...
    If NEWS_LLM_MODEL already has a prefix (contains "<provider>/"), we keep it.
    """
    model = (model or "").strip()
    provider = (provider or "").strip().lower()

    if not model:
        return ""

    # already prefixed like "ollama/...", "openai/...", etc.
    if "/" in model and model.split("/", 1)[0] in {"ollama", "openai", "anthropic", "watsonx"}:
        return model

    if provider in {"ollama", "openai", "anthropic", "watsonx"}:
        return f"{provider}/{model}"

    return model


def _infer_provider(model: str) -> str:
    if "/" in model:
        return model.split("/", 1)[0].lower()
    return ""


def _watsonx_env() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Gather watsonx env vars from common spellings.
    We keep your existing names as primary:
      - WATSONX_APIKEY
      - WATSONX_URL
      - WATSONX_PROJECT_ID
    """
    api_key = os.environ.get("WATSONX_APIKEY") or os.environ.get("WATSONX_API_KEY")
    url = os.environ.get("WATSONX_URL")
    project_id = os.environ.get("WATSONX_PROJECT_ID") or os.environ.get("WATSONX_PROJECTID")
    return api_key, url, project_id


def get_llm() -> LLM:
    # Preferred: single variable with provider prefix
    raw_model = os.environ.get("NEWS_LLM_MODEL") or os.environ.get("LLM_MODEL") or ""

    # Optional: split provider + model (supported)
    provider = os.environ.get("NEWS_LLM_PROVIDER")

    model = _normalize_model(provider, raw_model) if (provider or raw_model) else ""
    if not model:
        model = "ollama/gemma:2b"

    temperature = _safe_float("NEWS_LLM_TEMPERATURE", 0.7)

    # Optional knobs for local / slow models
    # - NEWS_LLM_TIMEOUT: seconds (LiteLLM request timeout)
    # - NEWS_LLM_MAX_TOKENS: cap output tokens to avoid runaway generations
    timeout_raw = os.environ.get("NEWS_LLM_TIMEOUT")
    max_tokens_raw = os.environ.get("NEWS_LLM_MAX_TOKENS")

    kwargs: Dict[str, object] = {}
    inferred_provider = _infer_provider(model)

    # --- Ollama (local)
    if inferred_provider == "ollama":
        base_url = (
            os.environ.get("OLLAMA_API_BASE")
            or os.environ.get("OLLAMA_HOST")
            or "http://127.0.0.1:11434"
        )
        kwargs["base_url"] = base_url
        print(f"[llm_client] 🤖 Provider=Ollama  model={model!r}  base_url={base_url}")

    # --- IBM watsonx.ai (remote)
    elif inferred_provider == "watsonx":
        api_key, url, project_id = _watsonx_env()

        # Best default for your project: ML endpoint (region-specific)
        base_url = url or "https://us-south.ml.cloud.ibm.com"
        kwargs["base_url"] = base_url

        # Pass through if present (LiteLLM often reads env anyway)
        if api_key:
            kwargs["api_key"] = api_key
        if project_id:
            kwargs["project_id"] = project_id

        # Warn loudly if missing required bits
        missing = []
        if not api_key:
            missing.append("WATSONX_APIKEY")
        if not project_id:
            missing.append("WATSONX_PROJECT_ID")
        if missing:
            print(
                f"[llm_client] ⚠️  Provider=watsonx selected but missing: {', '.join(missing)}. "
                f"Set them in .env or environment.",
                file=sys.stderr,
            )

        print(f"[llm_client] 🤖 Provider=watsonx  model={model!r}  base_url={base_url}")

    # --- Hosted providers via LiteLLM (OpenAI, Anthropic, etc.)
    else:
        # For openai/*, anthropic/*, etc.
        print(f"[llm_client] 🤖 Provider={inferred_provider or 'auto'}  model={model!r} (LiteLLM)")

    if timeout_raw:
        try:
            kwargs["timeout"] = float(timeout_raw)
        except (TypeError, ValueError):
            print(f"[llm_client] ⚠️  Invalid NEWS_LLM_TIMEOUT={timeout_raw!r}; ignoring", file=sys.stderr)

    if max_tokens_raw:
        try:
            kwargs["max_tokens"] = int(max_tokens_raw)
        except (TypeError, ValueError):
            print(f"[llm_client] ⚠️  Invalid NEWS_LLM_MAX_TOKENS={max_tokens_raw!r}; ignoring", file=sys.stderr)

    return LLM(
        model=model,
        temperature=temperature,
        **kwargs,
    )


# Singleton instance to import in other scripts
llm: LLM = get_llm()
