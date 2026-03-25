---
title: "LlamaIndex: Connect Your Custom Data to Large Language Models"
date: 2025-12-24T09:00:00+00:00
last_modified_at: 2025-12-24T09:00:00+00:00
topic_kind: "package"
topic_id: "llama-index"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - llamaindex
  - llm
  - retrieval-augmented-generation
  - vector-search
  - python
  - data-indexing
  - rag
excerpt: "A practical guide to LlamaIndex, the data framework for building retrieval-augmented generation (RAG) applications that connect custom data sources to LLMs."
header:
  overlay_image: /assets/images/2025-12-24-package-llama-index/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2025-12-24-package-llama-index/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

LlamaIndex (formerly GPT Index) is a data framework for building retrieval-augmented generation (RAG) applications. It provides the tools to ingest, structure, and query your own data using large language models. Rather than relying solely on an LLM's training data, LlamaIndex lets you connect private documents, databases, and APIs to an LLM so it can answer questions grounded in your specific data. In this post, you will learn how to install LlamaIndex, load documents, build vector indexes, and query them effectively.

## Overview

LlamaIndex solves a core problem: LLMs have fixed training data and cannot access your private or up-to-date information. LlamaIndex bridges this gap with:

- **Data connectors** -- ingest data from files, databases, APIs, and web sources using `SimpleDirectoryReader` and other loaders
- **Indexes** -- structure your data into queryable indexes such as `VectorStoreIndex`, `SummaryIndex`, and `TreeIndex`
- **Query engines** -- natural language interfaces over your indexed data that combine retrieval with LLM synthesis
- **Node and document abstractions** -- documents are parsed into nodes (chunks) that can be indexed and retrieved independently
- **Composability** -- combine multiple indexes and query engines into complex pipelines
- **Integration with vector stores** -- plug in Pinecone, Weaviate, Chroma, Qdrant, and many others

Common use cases include question-answering over private documents, chatbots grounded in company knowledge bases, and document summarization pipelines.

## Getting Started

Install the core package:

```bash
pip install llama-index-core llama-index-llms-openai llama-index-embeddings-openai
```

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key"
```

Here is a minimal RAG example that loads text files from a directory, builds a vector index, and answers a question:

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# Load documents from a directory
documents = SimpleDirectoryReader("./data").load_data()

# Build a vector index from the documents
index = VectorStoreIndex.from_documents(documents)

# Create a query engine and ask a question
query_engine = index.as_query_engine()
response = query_engine.query("What are the main topics covered in these documents?")
print(response)
```

This code reads all files in the `./data` directory, chunks them into nodes, generates embeddings, stores them in an in-memory vector index, and uses the LLM to synthesize an answer from the most relevant chunks.

## Core Concepts

### Documents and Nodes

LlamaIndex represents data at two levels. A `Document` is a container for a source (a file, a web page, a database row). Documents are parsed into `Node` objects, which are smaller chunks suitable for embedding and retrieval:

```python
from llama_index.core import Document

# Create documents manually
doc = Document(text="LlamaIndex is a data framework for LLM applications.")
print(doc.doc_id)
print(doc.text)
```

### Indexes

The most common index type is `VectorStoreIndex`, which stores node embeddings and retrieves them via similarity search. Other index types include:

- `SummaryIndex` -- summarizes all nodes to answer a query
- `TreeIndex` -- builds a tree structure for hierarchical summarization
- `KeywordTableIndex` -- uses keyword extraction for retrieval

### Query Engines and Chat Engines

A query engine handles single question-answer interactions. A chat engine maintains conversation history:

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)

# Single-turn query engine
query_engine = index.as_query_engine(similarity_top_k=3)
response = query_engine.query("Summarize the key findings.")
print(response)

# Multi-turn chat engine
chat_engine = index.as_chat_engine(chat_mode="context")
response = chat_engine.chat("What is the document about?")
print(response)
follow_up = chat_engine.chat("Can you elaborate on the second point?")
print(follow_up)
```

## Practical Examples

### Example 1: Customizing the LLM and Embedding Model

You can configure which LLM and embedding model LlamaIndex uses via the `Settings` object:

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Configure the LLM and embedding model
Settings.llm = OpenAI(model="gpt-4o", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# Build index and query
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("What are the key takeaways?")
print(response)
```

### Example 2: Persisting and Loading an Index

You can save an index to disk and reload it later to avoid re-embedding documents:

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage

# Build and persist
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
index.storage_context.persist(persist_dir="./storage")

# Load from disk later
storage_context = StorageContext.from_defaults(persist_dir="./storage")
loaded_index = load_index_from_storage(storage_context)
query_engine = loaded_index.as_query_engine()
response = query_engine.query("What did we discuss previously?")
print(response)
```

## Best Practices

- **Chunk size matters** -- experiment with `Settings.chunk_size` (default is 1024 tokens). Smaller chunks improve precision; larger chunks provide more context.
- **Use `similarity_top_k`** -- adjust the number of retrieved nodes to balance relevance and context window usage.
- **Persist your index** -- avoid re-embedding large document collections by saving the index to disk with `storage_context.persist()`.
- **Set `temperature=0` for factual queries** -- reduces hallucination when the goal is accurate retrieval-based answers.
- **Use metadata filters** -- attach metadata to documents and filter at query time to narrow retrieval scope.

## Conclusion

LlamaIndex provides a straightforward framework for building RAG applications that connect your own data to large language models. Its abstractions for loading, indexing, and querying data make it possible to go from raw documents to a working question-answering system in a few lines of code. For more advanced use cases, explore custom retrievers, agent-based query pipelines, and integrations with external vector stores.

Resources:

- [LlamaIndex Official Documentation](https://docs.llamaindex.ai/)
- [LlamaIndex GitHub Repository](https://github.com/run-llama/llama_index)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
