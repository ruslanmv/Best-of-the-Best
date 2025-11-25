"""
LLM Client configuration for CrewAI with Ollama support.
Properly configured to work with LiteLLM.
"""

from langchain_openai import ChatOpenAI


def get_llm(model_name: str = "llama3.2", base_url: str = "http://localhost:11434"):
    """
    Get properly configured LLM for CrewAI.

    CrewAI uses LiteLLM internally, which requires the Ollama provider prefix.

    Args:
        model_name: Ollama model name (default: llama3.2)
        base_url: Ollama server URL (default: http://localhost:11434)

    Returns:
        ChatOpenAI: Configured LLM client compatible with CrewAI
    """
    # For Ollama with LiteLLM (used by CrewAI), we need to prefix with 'ollama/'
    # This tells LiteLLM to use the Ollama provider
    full_model_name = f"ollama/{model_name}"

    return ChatOpenAI(
        model=full_model_name,
        base_url=f"{base_url}/v1",  # Ollama's OpenAI-compatible endpoint
        api_key="ollama",  # Dummy key, not used by Ollama
        temperature=0.7,
    )


# For backward compatibility
llm = get_llm()
