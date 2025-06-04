from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field


class Extra(BaseModel):
    fatal_item_ids: Optional[List] = None
    logid: Optional[str] = None
    now: Optional[int] = None


class Author(BaseModel):
    avatarLarger: Optional[str] = None
    avatarMedium: Optional[str] = None
    avatarThumb: Optional[str] = None
    commentSetting: Optional[int] = None
    downloadSetting: Optional[int] = None
    duetSetting: Optional[int] = None
    ftc: Optional[bool] = None
    id: Optional[str] = None
    isADVirtual: Optional[bool] = None
    isEmbedBanned: Optional[bool] = None
    nickname: Optional[str] = None
    openFavorite: Optional[bool] = None
    privateAccount: Optional[bool] = None
    relation: Optional[int] = None
    secUid: Optional[str] = None
    secret: Optional[bool] = None
    signature: Optional[str] = None
    stitchSetting: Optional[int] = None
    uniqueId: Optional[str] = None
    verified: Optional[bool] = None


class Challenge(BaseModel):
    coverLarger: Optional[str] = None
    coverMedium: Optional[str] = None
    coverThumb: Optional[str] = None
    desc: Optional[str] = None
    id: Optional[str] = None
    profileLarger: Optional[str] = None
    profileMedium: Optional[str] = None
    profileThumb: Optional[str] = None
    title: Optional[str] = None


class TextExtraItem(BaseModel):
    awemeId: Optional[str] = None
    end: Optional[int] = None
    hashtagId: Optional[str] = None
    hashtagName: Optional[str] = None
    isCommerce: Optional[bool] = None
    start: Optional[int] = None
    subType: Optional[int] = None
    type: Optional[int] = None


class Content(BaseModel):
    desc: Optional[str] = None
    textExtra: Optional[List[TextExtraItem]] = None


class ImageURL(BaseModel):
    urlList: Optional[List[str]] = None


class Cover(BaseModel):
    imageHeight: Optional[int] = None
    imageURL: Optional[ImageURL] = None
    imageWidth: Optional[int] = None


class Image(BaseModel):
    imageHeight: Optional[int] = None
    imageURL: Optional[ImageURL] = None
    imageWidth: Optional[int] = None


class ShareCover(BaseModel):
    imageHeight: Optional[int] = None
    imageURL: Optional[ImageURL] = None
    imageWidth: Optional[int] = None


class ImagePost(BaseModel):
    cover: Optional[Cover] = None
    images: Optional[List[Image]] = None
    shareCover: Optional[ShareCover] = None
    title: Optional[str] = None


class ItemControl(BaseModel):
    can_repost: Optional[bool] = None


class Music(BaseModel):
    album: Optional[str] = None
    authorName: Optional[str] = None
    coverLarge: Optional[str] = None
    coverMedium: Optional[str] = None
    coverThumb: Optional[str] = None
    duration: Optional[int] = None
    id: Optional[str] = None
    original: Optional[bool] = None
    playUrl: Optional[str] = None
    title: Optional[str] = None


class Stats(BaseModel):
    collectCount: Optional[int] = None
    commentCount: Optional[int] = None
    diggCount: Optional[int] = None
    playCount: Optional[int] = None
    shareCount: Optional[int] = None


class StatsV2(BaseModel):
    collectCount: Optional[str] = None
    commentCount: Optional[str] = None
    diggCount: Optional[str] = None
    playCount: Optional[str] = None
    repostCount: Optional[str] = None
    shareCount: Optional[str] = None


class VolumeInfo(BaseModel):
    Loudness: Optional[float] = None
    Peak: Optional[float] = None


class PlayAddrrr(BaseModel):
    DataSize: Optional[Any] = None
    FileCs: Optional[Any] = None
    FileHash: Optional[Any] = None
    Height: Optional[Any] = None
    Uri: Optional[Any] = None
    UrlKey: Optional[Any] = None
    UrlList: Optional[List[Any]] = None
    Width: Optional[Any] = None


class BitrateInfoItem(BaseModel):
    Bitrate: Optional[int] = None
    CodecType: Optional[str] = None
    GearName: Optional[str] = None
    MVMAF: Optional[str] = None
    PlayAddr: Optional[PlayAddrrr] = None
    QualityType: Optional[int] = None


class CaptionInfo(BaseModel):
    captionFormat: Optional[str] = None
    claSubtitleID: Optional[str] = None
    expire: Optional[str] = None
    isAutoGen: Optional[bool] = None
    isOriginalCaption: Optional[bool] = None
    language: Optional[str] = None
    languageCode: Optional[str] = None
    languageID: Optional[str] = None
    subID: Optional[str] = None
    subtitleType: Optional[str] = None
    url: Optional[str] = None
    urlList: Optional[List[str]] = None
    variant: Optional[str] = None


class OriginalLanguageInfo(BaseModel):
    language: Optional[str] = None
    languageCode: Optional[str] = None
    languageID: Optional[str] = None


class ClaInfo(BaseModel):
    captionInfos: Optional[List[CaptionInfo]] = None
    captionsType: Optional[int] = None
    enableAutoCaption: Optional[bool] = None
    hasOriginalAudio: Optional[bool] = None
    originalLanguageInfo: Optional[OriginalLanguageInfo] = None


class SubtitleInfo(BaseModel):
    Format: Optional[str] = None
    LanguageCodeName: Optional[str] = None
    LanguageID: Optional[str] = None
    Size: Optional[int] = None
    Source: Optional[str] = None
    Url: Optional[str] = None
    UrlExpire: Optional[int] = None
    Version: Optional[str] = None


class ZoomCover(BaseModel):
    field_240: Optional[str] = Field(None, alias="240")
    field_480: Optional[str] = Field(None, alias="480")
    field_720: Optional[str] = Field(None, alias="720")
    field_960: Optional[str] = Field(None, alias="960")


class Video(BaseModel):
    cover: Optional[str] = None
    duration: Optional[int] = None
    height: Optional[int] = None
    id: Optional[str] = None
    originCover: Optional[str] = None
    ratio: Optional[str] = None
    volumeInfo: Optional[VolumeInfo] = None
    width: Optional[int] = None
    VQScore: Optional[str] = None
    bitrate: Optional[int] = None
    bitrateInfo: Optional[List[BitrateInfoItem]] = None
    claInfo: Optional[ClaInfo] = None
    codecType: Optional[str] = None
    definition: Optional[str] = None
    downloadAddr: Optional[str] = None
    dynamicCover: Optional[str] = None
    encodeUserTag: Optional[str] = None
    encodedType: Optional[str] = None
    format: Optional[str] = None
    playAddr: Optional[str] = None
    subtitleInfos: Optional[List[SubtitleInfo]] = None
    videoQuality: Optional[str] = None
    zoomCover: Optional[ZoomCover] = None


class ItemStruct(BaseModel):
    AIGCDescription: Optional[str] = None
    author: Optional[Author] = None
    backendSourceEventTracking: Optional[str] = None
    challenges: Optional[List[Challenge]] = None
    collected: Optional[bool] = None
    contents: Optional[List[Content]] = None
    createTime: Optional[int] = None
    desc: Optional[str] = None
    digged: Optional[bool] = None
    duetDisplay: Optional[int] = None
    forFriend: Optional[bool] = None
    id: Optional[str] = None
    imagePost: Optional[ImagePost] = None
    itemCommentStatus: Optional[int] = None
    item_control: Optional[ItemControl] = None
    music: Optional[Music] = None
    officalItem: Optional[bool] = None
    originalItem: Optional[bool] = None
    playlistId: Optional[str] = None
    privateItem: Optional[bool] = None
    secret: Optional[bool] = None
    shareEnabled: Optional[bool] = None
    stats: Optional[Stats] = None
    statsV2: Optional[StatsV2] = None
    stitchDisplay: Optional[int] = None
    suggestedWords: Optional[List[str]] = None
    textExtra: Optional[List[TextExtraItem]] = None
    video: Optional[Video] = None
    diversificationId: Optional[int] = None
    duetEnabled: Optional[bool] = None
    stitchEnabled: Optional[bool] = None


class ItemInfo(BaseModel):
    itemStruct: Optional[ItemStruct] = None


class LogPb(BaseModel):
    impr_id: Optional[str] = None


class ShareMeta(BaseModel):
    desc: Optional[str] = None
    title: Optional[str] = None


class TikTokPostResponse(BaseModel):
    extra: Optional[Extra] = None
    itemInfo: Optional[ItemInfo] = None
    log_pb: Optional[LogPb] = None
    shareMeta: Optional[ShareMeta] = None
    statusCode: Optional[int] = None
    status_code: Optional[int] = None
    status_msg: Optional[str] = None
