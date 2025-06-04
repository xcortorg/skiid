from typing import Optional, List
from pydantic import BaseModel


class DuckDuckGoResult(BaseModel):
    title: str
    href: str
    body: str


class DuckDuckGoSearchResponse(BaseModel):
    results: Optional[List[DuckDuckGoResult]] = None
