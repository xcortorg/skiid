"""
  Author: cop-discord
  Email: cop@catgir.ls
  Discord: aiohttp
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class FAQ(BaseModel):
    query: Optional[str] = None
    answer: Optional[str] = None
    title: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None


class Keywords(BaseModel):
    FAQs: Optional[List[FAQ]] = None
    related_keywords: Optional[List[Any]] = None


class Result(BaseModel):
    position: Optional[int] = None
    title: Optional[str] = None
    url: Optional[str] = None
    origin: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None


class KnowledgePanel(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class BingResponse(BaseModel):
    keywords: Optional[Keywords] = None
    results: Optional[List[Result]] = None
    knowledge_panel: Optional[KnowledgePanel] = None
    cached: Optional[bool] = False

    def sort(self: "BingResponse") -> None:
        self.results = sorted(self.results, key=lambda result: result.page)
