from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class Stream(BaseModel):
    id: str
    user_id: str
    user_login: str
    user_name: str
    game_id: Optional[str] = None
    game_name: Optional[str] = None
    type: Optional[str] = None
    title: Optional[str] = None
    viewer_count: Optional[int] = 0
    started_at: datetime
    language: Optional[str] = None
    thumbnail_url: Optional[str] = None
    tag_ids: Optional[List[Any]] = None
    tags: Optional[List[str]] = None
    is_mature: Optional[bool] = False


class Pagination(BaseModel):
    cursor: Optional[str] = None


class StreamResponse(BaseModel):
    data: Optional[List[Stream]] = []
    pagination: Optional[Pagination] = None

    @property
    def stream(self) -> Stream:
        return self.data[0] if len(self.data) > 0 else None
