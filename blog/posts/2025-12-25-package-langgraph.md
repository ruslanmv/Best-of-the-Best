---
title: "LangGraph: Build Stateful Multi-Actor LLM Applications with Graphs"
date: 2025-12-25T09:00:00+00:00
last_modified_at: 2025-12-25T09:00:00+00:00
topic_kind: "package"
topic_id: "langgraph"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - langgraph
  - llm
  - agents
  - graph-workflows
  - python
  - langchain
  - state-machines
excerpt: "A practical guide to LangGraph, the library for building stateful, multi-actor LLM applications using graph-based workflows with cycles, branching, and persistence."
header:
  overlay_image: /assets/images/2025-12-25-package-langgraph/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2025-12-25-package-langgraph/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

LangGraph is a library for building stateful, multi-actor applications with large language models. Built on top of the LangChain ecosystem, it models workflows as directed graphs where nodes represent computation steps and edges define the flow between them. Unlike simple linear chains, LangGraph supports cycles, conditional branching, and persistent state, making it well suited for building complex agent architectures, multi-step reasoning pipelines, and human-in-the-loop workflows. In this post, you will learn how to install LangGraph, define state graphs, add nodes and edges, and build practical agent workflows.

## Overview

LangGraph provides the building blocks for orchestrating LLM-powered applications as graphs:

- **StateGraph** -- the core abstraction for defining a workflow as a graph with typed state
- **Nodes** -- functions that receive the current state, perform computation, and return state updates
- **Edges** -- connections between nodes that define execution flow, including conditional edges for branching
- **Persistent state** -- state is maintained across graph execution steps and can be checkpointed
- **Cycles** -- unlike DAG-based frameworks, LangGraph supports loops, enabling iterative agent behavior
- **Human-in-the-loop** -- pause execution to wait for human input before continuing

Common use cases include ReAct-style agents, multi-agent collaboration systems, planning and execution workflows, and any application that requires iterative LLM reasoning with state management.

## Getting Started

Install LangGraph using pip:

```bash
pip install langgraph langchain-openai
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

Here is a minimal example that builds a simple two-step graph:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# Define the state schema
class State(TypedDict):
    message: str
    processed: bool

# Define node functions
def greet(state: State) -> dict:
    return {"message": f"Hello! You said: {state['message']}"}

def finalize(state: State) -> dict:
    return {"processed": True}

# Build the graph
graph = StateGraph(State)
graph.add_node("greet", greet)
graph.add_node("finalize", finalize)

graph.add_edge(START, "greet")
graph.add_edge("greet", "finalize")
graph.add_edge("finalize", END)

# Compile and run
app = graph.compile()
result = app.invoke({"message": "LangGraph is great", "processed": False})
print(result)
```

## Core Concepts

### StateGraph and Typed State

Every LangGraph workflow starts with a `StateGraph` parameterized by a state schema. The state is a dictionary-like object that flows through the graph, and each node can read from and write to it:

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
import operator

class AgentState(TypedDict):
    messages: Annotated[list[str], operator.add]
    step_count: int

def step_one(state: AgentState) -> dict:
    return {"messages": ["Completed step one"], "step_count": 1}

def step_two(state: AgentState) -> dict:
    return {"messages": ["Completed step two"], "step_count": state["step_count"] + 1}

graph = StateGraph(AgentState)
graph.add_node("step_one", step_one)
graph.add_node("step_two", step_two)
graph.add_edge(START, "step_one")
graph.add_edge("step_one", "step_two")
graph.add_edge("step_two", END)

app = graph.compile()
result = app.invoke({"messages": [], "step_count": 0})
print(result["messages"])
print(f"Total steps: {result['step_count']}")
```

The `Annotated[list[str], operator.add]` syntax tells LangGraph to append new messages to the existing list rather than replacing it.

### Conditional Edges

LangGraph supports conditional branching, where the next node is chosen based on the current state:

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class ReviewState(TypedDict):
    text: str
    word_count: int
    decision: str

def count_words(state: ReviewState) -> dict:
    count = len(state["text"].split())
    return {"word_count": count}

def route(state: ReviewState) -> Literal["approve", "reject"]:
    if state["word_count"] >= 10:
        return "approve"
    return "reject"

def approve(state: ReviewState) -> dict:
    return {"decision": "approved"}

def reject(state: ReviewState) -> dict:
    return {"decision": "rejected - too short"}

graph = StateGraph(ReviewState)
graph.add_node("count_words", count_words)
graph.add_node("approve", approve)
graph.add_node("reject", reject)

graph.add_edge(START, "count_words")
graph.add_conditional_edges("count_words", route)
graph.add_edge("approve", END)
graph.add_edge("reject", END)

app = graph.compile()
result = app.invoke({"text": "This is a sufficiently long piece of text for review purposes.", "word_count": 0, "decision": ""})
print(result["decision"])
```

## Practical Examples

### Example 1: ReAct Agent with Tool Calling

This example builds a ReAct-style agent that can call tools and loop until it reaches a final answer:

```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def call_llm(state: AgentState) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["call_llm", "__end__"]:
    last_message = state["messages"][-1]
    # If the LLM made tool calls, continue the loop
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "call_llm"
    return "__end__"

graph = StateGraph(AgentState)
graph.add_node("call_llm", call_llm)

graph.add_edge(START, "call_llm")
graph.add_conditional_edges("call_llm", should_continue)

app = graph.compile()
result = app.invoke({"messages": [HumanMessage(content="What is 2 + 2?")]})
print(result["messages"][-1].content)
```

### Example 2: Multi-Step Processing Pipeline

This example shows a document processing pipeline with sequential steps:

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
import operator

class PipelineState(TypedDict):
    raw_text: str
    cleaned_text: str
    word_count: int
    summary: str
    log: Annotated[list[str], operator.add]

def clean_text(state: PipelineState) -> dict:
    cleaned = state["raw_text"].strip().lower()
    return {"cleaned_text": cleaned, "log": ["Text cleaned"]}

def analyze(state: PipelineState) -> dict:
    count = len(state["cleaned_text"].split())
    return {"word_count": count, "log": [f"Word count: {count}"]}

def summarize(state: PipelineState) -> dict:
    text = state["cleaned_text"]
    summary = text[:100] + "..." if len(text) > 100 else text
    return {"summary": summary, "log": ["Summary generated"]}

graph = StateGraph(PipelineState)
graph.add_node("clean", clean_text)
graph.add_node("analyze", analyze)
graph.add_node("summarize", summarize)

graph.add_edge(START, "clean")
graph.add_edge("clean", "analyze")
graph.add_edge("analyze", "summarize")
graph.add_edge("summarize", END)

app = graph.compile()
result = app.invoke({
    "raw_text": "  LangGraph enables building complex LLM workflows as graphs.  ",
    "cleaned_text": "",
    "word_count": 0,
    "summary": "",
    "log": [],
})

print(f"Summary: {result['summary']}")
print(f"Word count: {result['word_count']}")
print(f"Log: {result['log']}")
```

## Best Practices

- **Define clear state schemas** -- use `TypedDict` to make your state structure explicit and type-safe.
- **Keep nodes focused** -- each node should perform a single responsibility. Break complex logic into multiple nodes.
- **Use `Annotated` with reducers for lists** -- when multiple nodes append to the same list field, use `Annotated[list, operator.add]` to merge rather than replace.
- **Add conditional edges for branching** -- use `add_conditional_edges` with a routing function rather than embedding branching logic inside nodes.
- **Use checkpointing for long-running workflows** -- LangGraph supports memory checkpointers for persistence and recovery.
- **Test graphs incrementally** -- compile and run subgraphs before assembling the full workflow.

## Conclusion

LangGraph provides a powerful graph-based abstraction for building stateful LLM applications. By modeling workflows as nodes and edges with typed state, it enables complex patterns like agent loops, conditional branching, and multi-actor collaboration that are difficult to express with linear chains. Whether you are building a simple processing pipeline or a sophisticated multi-agent system, LangGraph gives you fine-grained control over execution flow and state management.

Resources:

- [LangGraph Official Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub Repository](https://github.com/langchain-ai/langgraph)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
