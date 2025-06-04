from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class Channel(BaseModel):
    id: str
    login: str
    display_name: Optional[str] = None
    type: Optional[str] = None
    broadcaster_type: Optional[str] = None
    description: Optional[str] = None
    profile_image_url: Optional[str] = None
    offline_image_url: Optional[str] = None
    view_count: Optional[int] = 0
    created_at: datetime


class ChannelResponse(BaseModel):
    data: Optional[List[Channel]] = None

    @property
    def channel(self) -> Channel:
        if self.data:
            return self.data[0] if len(self.data) > 0 else None
        return None
