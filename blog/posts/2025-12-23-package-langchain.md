---
title: "LangChain: Build LLM-Powered Applications with Modern Composable Chains"
date: 2025-12-23T09:00:00+00:00
last_modified_at: 2025-12-23T09:00:00+00:00
topic_kind: "package"
topic_id: "langchain"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - langchain
  - llm
  - agents
  - prompt-engineering
  - python
  - rag
  - lcel
excerpt: "A practical guide to LangChain, the framework for building LLM-powered applications using composable chains, prompt templates, and the LangChain Expression Language."
header:
  overlay_image: /assets/images/2025-12-23-package-langchain/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2025-12-23-package-langchain/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

LangChain is a framework for developing applications powered by large language models. It provides composable building blocks for working with LLMs, including prompt templates, output parsers, retrieval integrations, and agent architectures. The modern LangChain ecosystem is organized around `langchain-core` for base abstractions, provider-specific packages like `langchain-openai`, and the LangChain Expression Language (LCEL) for building chains declaratively using the pipe operator. In this post, you will learn how to install LangChain, build chains with LCEL, use prompt templates and output parsers, and create retrieval-augmented generation pipelines.

## Overview

LangChain provides a modular framework for LLM application development:

- **LangChain Expression Language (LCEL)** -- compose chains declaratively using the `|` pipe operator with streaming, batching, and async support built in
- **ChatPromptTemplate** -- structured prompt templates with system, human, and AI message roles
- **Chat models** -- unified interface to OpenAI, Anthropic, Google, and dozens of other LLM providers
- **Output parsers** -- parse LLM output into structured formats like JSON, Pydantic models, or lists
- **Retrievers** -- connect to vector stores and other data sources for retrieval-augmented generation
- **Agents and tools** -- LLM-driven agents that can call external tools and APIs
- **Memory** -- conversation history management for multi-turn interactions

Common use cases include chatbots, question-answering over documents, text summarization, data extraction, and autonomous agent workflows.

## Getting Started

Install the core packages:

```bash
pip install langchain-core langchain-openai
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

Here is a minimal example using LCEL to build a prompt-model-output chain:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# Define a prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that explains concepts simply."),
    ("human", "{question}"),
])

# Create the model and output parser
model = ChatOpenAI(model="gpt-4o", temperature=0)
parser = StrOutputParser()

# Build the chain using LCEL pipe syntax
chain = prompt | model | parser

# Run the chain
result = chain.invoke({"question": "What is a neural network?"})
print(result)
```

## Core Concepts

### LangChain Expression Language (LCEL)

LCEL is the recommended way to compose chains in modern LangChain. Each component implements the `Runnable` interface with `invoke`, `stream`, `batch`, and `ainvoke` methods. Components are composed using the `|` operator:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_template(
    "Translate the following text to {language}: {text}"
)
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

chain = prompt | model | parser

# Invoke
result = chain.invoke({"language": "French", "text": "Hello, how are you?"})
print(result)

# Stream tokens
for chunk in chain.stream({"language": "Spanish", "text": "Good morning"}):
    print(chunk, end="", flush=True)
print()

# Batch multiple inputs
results = chain.batch([
    {"language": "German", "text": "Thank you"},
    {"language": "Japanese", "text": "Goodbye"},
])
for r in results:
    print(r)
```

### Structured Output with Pydantic

LangChain integrates with Pydantic to parse LLM output into typed Python objects:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class MovieReview(BaseModel):
    title: str = Field(description="The movie title")
    rating: int = Field(description="Rating from 1 to 10")
    summary: str = Field(description="One-sentence summary of the review")

prompt = ChatPromptTemplate.from_messages([
    ("system", "Extract structured information from the movie review."),
    ("human", "{review}"),
])

model = ChatOpenAI(model="gpt-4o", temperature=0)
structured_model = model.with_structured_output(MovieReview)

chain = prompt | structured_model

result = chain.invoke({
    "review": "Inception is a mind-bending thriller by Christopher Nolan. The visual effects are stunning and the plot keeps you guessing. I'd give it a 9 out of 10."
})
print(f"Title: {result.title}")
print(f"Rating: {result.rating}")
print(f"Summary: {result.summary}")
```

## Practical Examples

### Example 1: Retrieval-Augmented Generation (RAG)

This example builds a RAG pipeline that answers questions using a set of documents:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Create sample documents
docs = [
    Document(page_content="LangChain is a framework for building LLM applications."),
    Document(page_content="LCEL uses the pipe operator to compose chains."),
    Document(page_content="Retrievers connect vector stores to LLM chains."),
]

# Build a vector store and retriever
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = FAISS.from_documents(docs, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# Define the RAG prompt
prompt = ChatPromptTemplate.from_template(
    "Answer the question based on the context below.\n\n"
    "Context: {context}\n\n"
    "Question: {question}"
)

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Build the RAG chain
def format_docs(docs):
    return "\n".join(doc.page_content for doc in docs)

chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)

result = chain.invoke("How does LCEL work?")
print(result)
```

### Example 2: Multi-Step Chain with RunnableParallel

This example runs multiple chains in parallel and combines their results:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

# Define two parallel analysis chains
pros_chain = (
    ChatPromptTemplate.from_template("List 3 pros of {topic}. Be concise.")
    | model
    | parser
)

cons_chain = (
    ChatPromptTemplate.from_template("List 3 cons of {topic}. Be concise.")
    | model
    | parser
)

# Run both in parallel
parallel = RunnableParallel(pros=pros_chain, cons=cons_chain)

# Combine results with a summary chain
summary_prompt = ChatPromptTemplate.from_template(
    "Given these pros:\n{pros}\n\nAnd these cons:\n{cons}\n\n"
    "Write a balanced one-paragraph summary."
)
summary_chain = summary_prompt | model | parser

# Full pipeline
full_chain = parallel | summary_chain

result = full_chain.invoke({"topic": "remote work"})
print(result)
```

## Best Practices

- **Use LCEL over legacy chains** -- the `LLMChain` and `SequentialChain` classes are deprecated. Use the `|` pipe operator with LCEL instead.
- **Install provider packages separately** -- use `langchain-openai`, `langchain-anthropic`, etc. rather than importing from the monolithic `langchain` package.
- **Stream for interactive applications** -- LCEL chains support `.stream()` natively, sending tokens to the user as they are generated.
- **Use `with_structured_output` for data extraction** -- this is more reliable than manually prompting for JSON and parsing the output.
- **Keep prompts in templates** -- use `ChatPromptTemplate` to separate prompt logic from application code, making prompts easier to test and iterate on.
- **Add fallbacks for resilience** -- use `.with_fallbacks([fallback_model])` to gracefully handle provider failures.

## Conclusion

LangChain provides a composable, modular framework for building LLM-powered applications. The LangChain Expression Language makes it straightforward to chain together prompts, models, retrievers, and output parsers with a clean declarative syntax. Whether you are building a simple chatbot, a RAG pipeline, or a multi-step agent workflow, LangChain gives you the abstractions to develop, test, and deploy LLM applications efficiently.

Resources:

- [LangChain Official Documentation](https://python.langchain.com/)
- [LangChain GitHub Repository](https://github.com/langchain-ai/langchain)
- [LCEL Documentation](https://python.langchain.com/docs/concepts/lcel/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
