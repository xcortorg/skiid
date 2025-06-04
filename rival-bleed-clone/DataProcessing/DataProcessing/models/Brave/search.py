from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel


class MainResult(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    subtitle: Optional[str] = None
    extra_subtitle: Optional[str] = None
    snippet: Optional[str] = None
    full_info: Optional[Dict[str, Any]] = None


class Result(BaseModel):
    domain: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    favicon: Optional[str] = None
    breadcrumb: str = None
    url: Optional[str] = None


class BraveSearchResponse(BaseModel):
    query_time: Optional[Union[float, str]] = None
    query: Optional[str] = None
    safe: Optional[str] = None
    main_result: Optional[MainResult] = None
    results: List[Result] = None
    cached: Optional[bool] = False
