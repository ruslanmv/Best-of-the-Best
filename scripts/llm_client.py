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
from crewai import LLM


def get_llm():
    """
    Instantiate a CrewAI LLM that can talk to:
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

    model = os.environ.get("NEWS_LLM_MODEL") or os.environ.get("LLM_MODEL") or "ollama/gemma:2b"
    temperature = float(os.environ.get("NEWS_LLM_TEMPERATURE", "0.7"))

    kwargs = {}

    # Local Ollama (used in CI)
    if model.startswith("ollama/"):
        base_url = os.environ.get("OLLAMA_API_BASE") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
        kwargs["base_url"] = base_url
        print(f"🤖 Using Ollama model '{model}' at {base_url}")

    # IBM watsonx.ai (remote)
    elif model.startswith("watsonx/"):
        base_url = os.environ.get("WATSONX_URL", "https://api.watsonx.ai/v1")
        kwargs["base_url"] = base_url
        print(f"🤖 Using Watsonx model '{model}' at {base_url}")

    else:
        # OpenAI / Anthropic / etc. handled by LiteLLM via CrewAI
        print(f"🤖 Using remote provider model '{model}' via LiteLLM defaults")

    llm = LLM(
        model=model,
        temperature=temperature,
        **kwargs,
    )
    return llm


# Singleton instance to import in other scripts
llm = get_llm()
