"""Data models for blog generation"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Topic:
    """Topic metadata for blog generation"""
    kind: str
    id: str
    title: str
    url: Optional[str]
    summary: Optional[str]
    tags: List[str]
    version: int


@dataclass
class ResearchStrategy:
    """Research strategy decision"""
    strategy: str  # 'readme', 'package_health', 'web_search', 'hybrid'
    confidence: str  # 'high', 'medium', 'low'
    tools_to_use: List[str]
    fallback_needed: bool
    reasoning: str