#!/usr/bin/env python3
"""
scripts/llm_client.py

Multi-provider LLM client for Best-of-the-Best blog generation.
Supports:
  - Local Ollama (for CI and local runs)
  - OpenAI (gpt-4o, gpt-4o-mini, etc.)
  - Anthropic Claude
  - IBM watsonx.ai

Selection is controlled via:
  - NEWS_LLM_MODEL (preferred)
  - or LLM_MODEL

Examples:
  - "ollama/gemma:2b"
  - "ollama/llama3:8b"
  - "openai/gpt-4o-mini"
  - "anthropic/claude-3-5-sonnet-latest"
  - "watsonx/meta-llama/llama-3-1-70b-instruct"
"""

import os
import sys
from crewai import LLM


def _safe_float(env_name: str, default: float) -> float:
    """Convert env var to float with a safe fallback."""
    raw = os.environ.get(env_name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        print(
            f"[llm_client] ⚠️  Invalid value for {env_name!r}={raw!r}, "
            f"falling back to {default}",
            file=sys.stderr,
        )
        return default


def get_llm() -> LLM:
    """
    Instantiate a CrewAI LLM that can talk to:
      - Local Ollama (for CI and local runs)
      - OpenAI (gpt-4o, gpt-4o-mini, etc.)
      - Anthropic Claude
      - IBM watsonx.ai

    Model selection:
      - NEWS_LLM_MODEL (preferred)
      - or LLM_MODEL
    """
    model = (
        os.environ.get("NEWS_LLM_MODEL")
        or os.environ.get("LLM_MODEL")
        or "ollama/gemma:2b"
    )

    temperature = _safe_float("NEWS_LLM_TEMPERATURE", 0.7)
    kwargs = {}

    # Local Ollama (used in CI)
    if model.startswith("ollama/"):
        base_url = (
            os.environ.get("OLLAMA_API_BASE")
            or os.environ.get("OLLAMA_HOST")
            or "http://127.0.0.1:11434"
        )
        kwargs["base_url"] = base_url
        print(f"[llm_client] 🤖 Using Ollama model '{model}' at {base_url}")

    # IBM watsonx.ai (remote)
    elif model.startswith("watsonx/"):
        base_url = os.environ.get("WATSONX_URL", "https://api.watsonx.ai/v1")
        kwargs["base_url"] = base_url
        print(f"[llm_client] 🤖 Using Watsonx model '{model}' at {base_url}")
        # API key & project id are picked up from env by LiteLLM / provider SDK.

    else:
        # OpenAI / Anthropic / etc. handled by LiteLLM via CrewAI
        print(f"[llm_client] 🤖 Using remote provider model '{model}' via LiteLLM defaults")

    llm = LLM(
        model=model,
        temperature=temperature,
        **kwargs,
    )
    return llm


# Singleton instance to import in other scripts
llm: LLM = get_llm()
