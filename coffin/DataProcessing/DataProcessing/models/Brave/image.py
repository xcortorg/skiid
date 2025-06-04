from typing import List, Optional, Union

from pydantic import BaseModel


class ImageResult(BaseModel):
    domain: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    color: Optional[str] = None


class BraveImageSearchResponse(BaseModel):
    query_time: Optional[Union[float, str]] = None
    status: Optional[str] = "current"
    query: Optional[str] = None
    safe: Optional[str] = None
    results: List[ImageResult] = None
    cached: Optional[bool] = False
