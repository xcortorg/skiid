from typing import List, Optional

from pydantic import BaseModel


class DuckDuckGoImageResult(BaseModel):
    title: str
    image: str
    thumbnail: str
    url: str
    height: str
    width: str
    source: str


class DuckDuckGoImageResponse(BaseModel):
    results: Optional[List[DuckDuckGoImageResult]] = None
