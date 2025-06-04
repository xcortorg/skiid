from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from aiohttp import ClientSession
from io import BytesIO
from discord import Message, Embed, File, Color
from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    display_url: Optional[str] = None
    expanded_url: Optional[str] = None
    indices: Optional[List[int]] = None
    url: Optional[str] = None


class Entities(BaseModel):
    hashtags: Optional[List] = None
    urls: Optional[List] = None
    user_mentions: Optional[List] = None
    symbols: Optional[List] = None
    media: Optional[List[MediaItem]] = None


class User(BaseModel):
    id_str: Optional[str] = None
    name: Optional[str] = None
    profile_image_url_https: Optional[str] = None
    screen_name: Optional[str] = None
    verified: Optional[bool] = None
    is_blue_verified: Optional[bool] = None
    profile_image_shape: Optional[str] = None


class EditControl(BaseModel):
    edit_tweet_ids: Optional[List[str]] = None
    editable_until_msecs: Optional[str] = None
    is_edit_eligible: Optional[bool] = None
    edits_remaining: Optional[str] = None


class ExtMediaAvailability(BaseModel):
    status: Optional[str] = None


class FocusRect(BaseModel):
    x: Optional[int] = None
    y: Optional[int] = None
    w: Optional[int] = None
    h: Optional[int] = None


class OriginalInfo(BaseModel):
    height: Optional[int] = None
    width: Optional[int] = None
    focus_rects: Optional[List[FocusRect]] = None


class Large(BaseModel):
    h: Optional[int] = None
    resize: Optional[str] = None
    w: Optional[int] = None


class Medium(BaseModel):
    h: Optional[int] = None
    resize: Optional[str] = None
    w: Optional[int] = None


class Small(BaseModel):
    h: Optional[int] = None
    resize: Optional[str] = None
    w: Optional[int] = None


class Thumb(BaseModel):
    h: Optional[int] = None
    resize: Optional[str] = None
    w: Optional[int] = None


class Sizes(BaseModel):
    large: Optional[Large] = None
    medium: Optional[Medium] = None
    small: Optional[Small] = None
    thumb: Optional[Thumb] = None


class MediaDetail(BaseModel):
    display_url: Optional[str] = None
    expanded_url: Optional[str] = None
    ext_media_availability: Optional[ExtMediaAvailability] = None
    indices: Optional[List[int]] = None
    media_url_https: Optional[str] = None
    original_info: Optional[OriginalInfo] = None
    sizes: Optional[Sizes] = None
    type: Optional[str] = None
    url: Optional[str] = None


class BackgroundColor(BaseModel):
    red: Optional[int] = None
    green: Optional[int] = None
    blue: Optional[int] = None


class CropCandidate(BaseModel):
    x: Optional[int] = None
    y: Optional[int] = None
    w: Optional[int] = None
    h: Optional[int] = None


class Photo(BaseModel):
    backgroundColor: Optional[BackgroundColor] = None
    cropCandidates: Optional[List[CropCandidate]] = None
    expandedUrl: Optional[str] = None
    url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class MediaAvailability(BaseModel):
    status: Optional[str] = None


class Variant(BaseModel):
    type: Optional[str] = None
    src: Optional[str] = None


class VideoId(BaseModel):
    type: Optional[str] = None
    id: Optional[str] = None


class Audience(BaseModel):
    name: Optional[str] = None


class Device(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None


class Platform(BaseModel):
    audience: Optional[Audience] = None
    device: Optional[Device] = None


class CardPlatform(BaseModel):
    platform: Optional[Platform] = None


class UnifiedCard(BaseModel):
    string_value: Optional[str] = None
    type: Optional[str] = None


class CardUrl(BaseModel):
    scribe_key: Optional[str] = None
    string_value: Optional[str] = None
    type: Optional[str] = None


class BindingValues(BaseModel):
    unified_card: Optional[UnifiedCard] = None
    card_url: Optional[CardUrl] = None


class Card(BaseModel):
    card_platform: Optional[CardPlatform] = None
    name: Optional[str] = None
    url: Optional[str] = None
    binding_values: Optional[BindingValues] = None


class Video(BaseModel):
    aspectRatio: Optional[List[int]] = None
    contentType: Optional[str] = None
    durationMs: Optional[int] = None
    mediaAvailability: Optional[MediaAvailability] = None
    poster: Optional[str] = None
    variants: Optional[List[Variant]] = None
    videoId: Optional[VideoId] = None
    viewCount: Optional[int] = None


class Tweet(BaseModel):
    field__typename: Optional[str] = Field(None, alias="__typename")
    lang: Optional[str] = None
    favorite_count: Optional[int] = None
    possibly_sensitive: Optional[bool] = None
    created_at: Optional[str] = None
    display_text_range: Optional[List[int]] = None
    entities: Optional[Entities] = None
    id_str: Optional[str] = None
    text: Optional[str] = None
    user: Optional[User] = None
    edit_control: Optional[EditControl] = None
    mediaDetails: Optional[List[MediaDetail]] = None
    photos: Optional[List[Photo]] = None
    video: Optional[Video] = None
    conversation_count: Optional[int] = None
    news_action_type: Optional[str] = None
    card: Optional[Card] = None
    isEdited: Optional[bool] = None
    isStaleEdit: Optional[bool] = None
