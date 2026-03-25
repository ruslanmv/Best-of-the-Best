---
title: "LangChain - A Framework for Building LLM-Powered Applications"
date: 2026-02-15T09:00:00+00:00
last_modified_at: 2026-02-15T09:00:00+00:00
topic_kind: "repo"
topic_id: "langchain-ai/langchain"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - langchain
  - llm
  - agents
  - rag
  - chains
  - python
  - lcel
excerpt: "A deep dive into the langchain-ai/langchain repository, exploring its modular architecture, LCEL composition model, agents, retrieval-augmented generation, and integration ecosystem."
header:
  overlay_image: /assets/images/2026-02-15-repo-langchain/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-02-15-repo-langchain/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

[LangChain](https://github.com/langchain-ai/langchain) is one of the most widely adopted open-source frameworks for building applications powered by large language models. The `langchain-ai/langchain` repository provides the tools to connect LLMs to external data sources, compose multi-step reasoning chains, build autonomous agents, and implement retrieval-augmented generation (RAG) pipelines. It has become a central piece of the LLM application development ecosystem.

## Overview

The LangChain repository is organized as a Python monorepo with several distinct packages:

- **`langchain-core`** - Base abstractions and the LangChain Expression Language (LCEL) runtime. This package has minimal dependencies and defines the interfaces that all other packages build on.
- **`langchain`** - Higher-level chains, agents, and retrieval strategies that compose the core abstractions.
- **`langchain-community`** - Third-party integrations contributed by the community (vector stores, document loaders, tools, etc.).
- **`langchain-openai`**, **`langchain-anthropic`**, **`langchain-google-genai`**, etc. - Provider-specific packages for individual LLM and embedding providers.

This modular structure allows developers to install only the dependencies they need.

## Getting Started

### Installation

Install the core package and a provider:

```bash
pip install langchain langchain-openai
```

Set your API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

### A Minimal Example

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")
response = llm.invoke("What is LangChain?")
print(response.content)
```

## Core Concepts

### LangChain Expression Language (LCEL)

LCEL is the declarative composition model at the heart of LangChain. It uses the pipe (`|`) operator to chain components together, with built-in support for streaming, batching, and async execution:

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template(
    "Explain {topic} in one paragraph for a beginner."
)
model = ChatOpenAI(model="gpt-4o")
parser = StrOutputParser()

chain = prompt | model | parser

result = chain.invoke({"topic": "neural networks"})
print(result)
```

Every component in an LCEL chain implements the `Runnable` interface, which provides `.invoke()`, `.stream()`, `.batch()`, and their async counterparts.

### Retrieval-Augmented Generation (RAG)

LangChain provides building blocks for RAG pipelines that ground LLM responses in your own documents:

```python
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load and split documents
loader = TextLoader("docs.txt")
documents = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = splitter.split_documents(documents)

# Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever()

# Build RAG chain
prompt = ChatPromptTemplate.from_template(
    "Answer the question based on the context.\n\n"
    "Context: {context}\n\n"
    "Question: {question}"
)

chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | ChatOpenAI(model="gpt-4o")
    | StrOutputParser()
)

answer = chain.invoke("What does the document say about deployment?")
print(answer)
```

### Agents

LangChain agents use an LLM to decide which tools to call and in what order. The framework provides pre-built agent types and supports custom tool definitions:

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b

@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

llm = ChatOpenAI(model="gpt-4o")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful math assistant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, [multiply, add], prompt)
executor = AgentExecutor(agent=agent, tools=[multiply, add])

result = executor.invoke({"input": "What is 7 times 8, plus 3?"})
print(result["output"])
```

## Repository Architecture

The monorepo structure under `langchain-ai/langchain` includes:

```
libs/
  core/              # langchain-core (base abstractions, LCEL)
  langchain/         # langchain (chains, agents, retrieval)
  community/         # langchain-community (third-party integrations)
  partners/          # Provider-specific packages
    openai/
    anthropic/
    google-genai/
    ...
```

This layout allows each package to be versioned and released independently, and developers can contribute integrations without modifying the core framework.

## Best Practices

- **Use LCEL for new projects.** The pipe-based composition model is the recommended way to build chains, replacing the older `LLMChain` and `SequentialChain` classes.
- **Install only what you need.** Use provider-specific packages like `langchain-openai` rather than pulling in all of `langchain-community`.
- **Leverage LangSmith for debugging.** LangChain integrates with LangSmith for tracing, evaluation, and monitoring of LLM application runs.
- **Keep retrieval chunks small and focused** when building RAG pipelines. Smaller, well-scoped chunks generally produce better results than large passages.

## Conclusion

The `langchain-ai/langchain` repository provides a comprehensive, modular framework for building LLM-powered applications. Its LCEL composition model, extensive integration ecosystem, and support for agents and RAG make it a strong foundation for projects ranging from simple chatbots to complex autonomous workflows.

For more details, visit the [LangChain GitHub repository](https://github.com/langchain-ai/langchain) and the [LangChain documentation](https://python.langchain.com/).

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
