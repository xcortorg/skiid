"""
  Author: cop-discord
  Email: cop@catgir.ls
  Discord: aiohttp
"""

from typing import Any, Dict, List, Optional

from discord import Color, Embed
from pydantic import BaseModel


class Resolution(BaseModel):
    height: Optional[Any] = None
    width: Optional[Any] = None


class ImageResult(BaseModel):
    url: str
    thumbnail: str
    image: str
    content: Optional[str] = None
    source: str
    resolution: Resolution


class BingImageResponse(BaseModel):
    results: List[ImageResult]
    cached: Optional[bool] = False
    safe: Optional[bool] = False
    pages: int
    query: str

    @property
    def total(self: "BingImageResponse") -> int:
        return len(self.results)
