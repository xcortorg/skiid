from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Extra(BaseModel):
    fatal_item_ids: Optional[List] = None
    logid: Optional[str] = None
    now: Optional[int] = None


class LogPb(BaseModel):
    impr_id: Optional[str] = None


class ShareMeta(BaseModel):
    desc: Optional[str] = None
    title: Optional[str] = None


class Stats(BaseModel):
    diggCount: Optional[int] = None
    followerCount: Optional[int] = None
    followingCount: Optional[int] = None
    friendCount: Optional[int] = None
    heart: Optional[int] = None
    heartCount: Optional[int] = None
    videoCount: Optional[int] = None


class CommerceUserInfo(BaseModel):
    commerceUser: Optional[bool] = None


class ProfileTab(BaseModel):
    showPlayListTab: Optional[bool] = None


class User(BaseModel):
    avatarLarger: Optional[str] = None
    avatarMedium: Optional[str] = None
    avatarThumb: Optional[str] = None
    canExpPlaylist: Optional[bool] = None
    commentSetting: Optional[int] = None
    commerceUserInfo: Optional[CommerceUserInfo] = None
    downloadSetting: Optional[int] = None
    duetSetting: Optional[int] = None
    followingVisibility: Optional[int] = None
    ftc: Optional[bool] = None
    id: Optional[str] = None
    isADVirtual: Optional[bool] = None
    isEmbedBanned: Optional[bool] = None
    nickNameModifyTime: Optional[int] = None
    nickname: Optional[str] = None
    openFavorite: Optional[bool] = None
    privateAccount: Optional[bool] = None
    profileEmbedPermission: Optional[int] = None
    profileTab: Optional[ProfileTab] = None
    relation: Optional[int] = None
    secUid: Optional[str] = None
    secret: Optional[bool] = None
    signature: Optional[str] = None
    stitchSetting: Optional[int] = None
    ttSeller: Optional[bool] = None
    uniqueId: Optional[str] = None
    verified: Optional[bool] = None


class UserInfo(BaseModel):
    stats: Optional[Stats] = None
    user: Optional[User] = None


class TikTokUserProfileResponse(BaseModel):
    extra: Optional[Extra] = None
    log_pb: Optional[LogPb] = None
    shareMeta: Optional[ShareMeta] = None
    statusCode: Optional[int] = None
    status_code: Optional[int] = None
    status_msg: Optional[str] = None
    userInfo: Optional[UserInfo] = None
