from pydantic import BaseModel
from typing import Optional, List


class Video(BaseModel):
    id: str
    desc: Optional[str] = None
    height: int
    width: int
    ratio: Optional[str] = None
    coverUrl: str
    originCoverUrl: str
    dynamicCoverUrl: str
    playAddr: str
    playCount: int
    url: Optional[str] = None
    privateItem: bool
    warnInfoList: list


class userInfo(BaseModel):
    id: str
    avatarThumbUrl: Optional[str] = None
    uniqueId: str
    verified: bool
    followingCount: int
    followerCount: int
    heartCount: int
    signature: Optional[str] = None
    privateAccount: bool
    nickname: Optional[str] = None
    code: Optional[int] = None
    customErrorCode: Optional[int] = None


class TikTokRawUser(BaseModel):
    user: userInfo
    videos: Optional[List[Video]] = None
