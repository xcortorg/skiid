from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Url(BaseModel):
    url: Optional[str] = None
    urlType: Optional[str] = None


class Badge(BaseModel):
    url: Optional[str] = None


class Label(BaseModel):
    url: Optional[Url] = None
    badge: Optional[Badge] = None
    description: Optional[str] = None
    userLabelType: Optional[str] = None
    userLabelDisplayType: Optional[str] = None


class AffiliatesHighlightedLabel(BaseModel):
    label: Optional[Label] = None


class Description(BaseModel):
    urls: Optional[List] = None


class Url2(BaseModel):
    display_url: Optional[str] = None
    expanded_url: Optional[str] = None
    url: Optional[str] = None
    indices: Optional[List[int]] = None


class Url1(BaseModel):
    urls: Optional[List[Url2]] = None


class Entities(BaseModel):
    description: Optional[Description] = None
    url: Optional[Url1] = None


class Legacy(BaseModel):
    created_at: Optional[str] = None
    default_profile: Optional[bool] = None
    default_profile_image: Optional[bool] = None
    description: Optional[str] = None
    entities: Optional[Entities] = None
    fast_followers_count: Optional[int] = None
    favourites_count: Optional[int] = None
    followers_count: Optional[int] = None
    friends_count: Optional[int] = None
    has_custom_timelines: Optional[bool] = None
    is_translator: Optional[bool] = None
    listed_count: Optional[int] = None
    protected: Optional[bool] = False
    location: Optional[str] = None
    media_count: Optional[int] = None
    name: Optional[str] = None
    normal_followers_count: Optional[int] = None
    pinned_tweet_ids_str: Optional[List[str]] = None
    possibly_sensitive: Optional[bool] = None
    profile_banner_url: Optional[str] = None
    profile_image_url_https: Optional[str] = None
    profile_interstitial_type: Optional[str] = None
    screen_name: Optional[str] = None
    statuses_count: Optional[int] = None
    translator_type: Optional[str] = None
    url: Optional[str] = None
    verified: Optional[bool] = None
    withheld_in_countries: Optional[List] = None


class Professional(BaseModel):
    rest_id: Optional[str] = None
    professional_type: Optional[str] = None
    category: Optional[List] = None


class TipjarSettings(BaseModel):
    is_enabled: Optional[bool] = None
    bandcamp_handle: Optional[str] = None
    bitcoin_handle: Optional[str] = None
    cash_app_handle: Optional[str] = None
    ethereum_handle: Optional[str] = None
    gofundme_handle: Optional[str] = None
    patreon_handle: Optional[str] = None
    pay_pal_handle: Optional[str] = None
    venmo_handle: Optional[str] = None


class Ref(BaseModel):
    url: Optional[str] = None
    url_type: Optional[str] = None


class Entity(BaseModel):
    from_index: Optional[int] = None
    to_index: Optional[int] = None
    ref: Optional[Ref] = None


class Description1(BaseModel):
    text: Optional[str] = None
    entities: Optional[List[Entity]] = None


class Reason(BaseModel):
    description: Optional[Description1] = None
    verified_since_msec: Optional[str] = None
    override_verified_year: Optional[int] = None


class VerificationInfo(BaseModel):
    is_identity_verified: Optional[bool] = None
    reason: Optional[Reason] = None


class HighlightsInfo(BaseModel):
    can_highlight_tweets: Optional[bool] = None
    highlighted_tweets: Optional[str] = None


class Result(BaseModel):
    field__typename: Optional[str] = Field(None, alias="__typename")
    id: Optional[str] = None
    rest_id: Optional[str] = None
    affiliates_highlighted_label: Optional[AffiliatesHighlightedLabel] = None
    is_blue_verified: Optional[bool] = None
    profile_image_shape: Optional[str] = None
    legacy: Optional[Legacy] = None
    professional: Optional[Professional] = None
    tipjar_settings: Optional[TipjarSettings] = None
    verified_phone_status: Optional[bool] = None
    legacy_extended_profile: Optional[Dict[str, Any]] = None
    is_profile_translatable: Optional[bool] = None
    has_hidden_likes_on_profile: Optional[bool] = None
    has_hidden_subscriptions_on_profile: Optional[bool] = None
    verification_info: Optional[VerificationInfo] = None
    highlights_info: Optional[HighlightsInfo] = None
    user_seed_tweet_count: Optional[int] = None
    message: Optional[str] = None
    reason: Optional[str] = None
    business_account: Optional[Dict[str, Any]] = None
    creator_subscriptions_count: Optional[int] = None


class User(BaseModel):
    result: Optional[Result] = None


class Data(BaseModel):
    user: Optional[User] = None


class TwitterUser(BaseModel):
    data: Optional[Data] = None
