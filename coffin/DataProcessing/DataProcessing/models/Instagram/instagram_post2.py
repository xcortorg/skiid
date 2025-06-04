from __future__ import annotations

import textwrap
from typing import Any, List, Optional

import arrow
import discord  # noqa
import regex as re
from boltons.strutils import find_hashtags
from pydantic import BaseModel, Field


class InstaPostURLMeta(BaseModel):
    media_id: Optional[str] = None
    url: Optional[str] = None


class InstagramCredentialItem(BaseModel):
    alias: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None


class Location(BaseModel):
    short_name: Optional[str] = None
    external_source: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    lng: Optional[float] = None
    lat: Optional[float] = None
    is_eligible_for_guides: Optional[bool] = None


class Thumbnails(BaseModel):
    video_length: Optional[float] = None
    thumbnail_width: Optional[int] = None
    thumbnail_height: Optional[int] = None
    thumbnail_duration: Optional[float] = None
    sprite_urls: Optional[List[str]] = None
    thumbnails_per_row: Optional[int] = None
    total_thumbnail_num_per_sprite: Optional[int] = None
    max_thumbnails_per_sprite: Optional[int] = None
    sprite_width: Optional[int] = None
    sprite_height: Optional[int] = None
    rendered_width: Optional[int] = None
    file_size_kb: Optional[int] = None


class Candidate(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    url: Optional[str] = None


class IgtvFirstFrame(Candidate):
    pass


class FirstFrame(Candidate):
    pass


class AdditionalCandidates(BaseModel):
    igtv_first_frame: Optional[IgtvFirstFrame] = None
    first_frame: Optional[FirstFrame] = None


class ImageVersions2(BaseModel):
    candidates: Optional[List[Candidate]] = None
    additional_candidates: Optional[AdditionalCandidates] = None


class FriendshipStatus(BaseModel):
    following: Optional[bool] = None
    outgoing_request: Optional[bool] = None
    is_bestie: Optional[bool] = None
    is_restricted: Optional[bool] = None
    is_feed_favorite: Optional[bool] = None


class FanClubInfo(BaseModel):
    fan_club_id: Optional[Any] = None
    fan_club_name: Optional[Any] = None


class User(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_private: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    profile_pic_id: Optional[str] = None

    is_verified: Optional[bool] = None


class InstagramUserResponse(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_private: Optional[bool] = None
    avatar_filename: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: Optional[bool] = None


class In(BaseModel):
    user: Optional[InstagramUserResponse] = None
    position: Optional[List[float]] = None
    start_time_in_video_in_sec: Optional[Any] = None
    duration_in_video_in_sec: Optional[Any] = None


class Usertags(BaseModel):
    in_: Optional[List[In]] = Field(alias="in")


class MashupInfo(BaseModel):
    mashups_allowed: Optional[bool] = None
    can_toggle_mashups_allowed: Optional[bool] = None
    has_been_mashed_up: Optional[bool] = None
    formatted_mashups_count: Optional[Any] = None
    original_media: Optional[Any] = None
    non_privacy_filtered_mashups_media_count: Optional[Any] = None
    mashup_type: Optional[Any] = None
    is_creator_requesting_mashup: Optional[bool] = None
    has_nonmimicable_additional_audio: Optional[Any] = None


class VideoVersion(BaseModel):
    type: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    url: Optional[str] = None
    id: Optional[str] = None


class User2(InstagramUserResponse):
    pass


class Caption(BaseModel):
    text: Optional[str] = None


class CommentInformTreatment(BaseModel):
    should_have_inform_treatment: Optional[bool] = None
    text: Optional[str] = None
    url: Optional[Any] = None
    action_type: Optional[Any] = None


class SharingFrictionInfo(BaseModel):
    should_have_sharing_friction: Optional[bool] = None
    bloks_app_url: Optional[Any] = None
    sharing_friction_payload: Optional[Any] = None


class MusicMetadata(BaseModel):
    music_canonical_id: Optional[str] = None
    audio_type: Optional[Any] = None
    music_info: Optional[Any] = None
    original_sound_info: Optional[Any] = None
    pinned_media_ids: Optional[Any] = None


class CarouselMedia(BaseModel):
    id: Optional[str] = None
    media_type: Optional[int] = None
    video_versions: Optional[List[VideoVersion]] = None
    image_versions2: Optional[ImageVersions2] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None
    accessibility_caption: Optional[str] = None
    pk: Optional[str] = None
    carousel_parent_id: Optional[str] = None
    usertags: Optional[Usertags] = None
    commerciality_status: Optional[str] = None


class InstagramCarouselMediaResponse(BaseModel):
    url: Optional[str] = None
    preview_image_url: Optional[str] = None
    preview_image_filename: Optional[str] = None
    is_video: Optional[bool] = False
    filename: Optional[str] = None


class Item(BaseModel):
    taken_at: Optional[int] = None
    pk: Optional[str] = None
    id: Optional[str] = None
    device_timestamp: Optional[int] = None
    media_type: Optional[int] = None
    code: Optional[str] = None
    client_cache_key: Optional[str] = None
    filter_type: Optional[int] = None
    is_unified_video: Optional[bool] = None
    location: Optional[Location] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    should_request_ads: Optional[bool] = None
    caption_is_edited: Optional[bool] = None
    like_and_view_counts_disabled: Optional[bool] = None
    commerciality_status: Optional[str] = None
    is_paid_partnership: Optional[bool] = None
    is_visual_reply_commenter_notice_enabled: Optional[bool] = None
    original_media_has_visual_reply_media: Optional[bool] = None
    has_delayed_metadata: Optional[bool] = None
    comment_likes_enabled: Optional[bool] = None
    comment_threading_enabled: Optional[bool] = None
    has_more_comments: Optional[bool] = None
    max_num_visible_preview_comments: Optional[int] = None
    preview_comments: Optional[list] = None
    comments: Optional[list] = None
    can_view_more_preview_comments: Optional[bool] = None
    comment_count: Optional[int] = None
    hide_view_all_comment_entrypoint: Optional[bool] = None
    inline_composer_display_condition: Optional[str] = None
    title: Optional[str] = None
    carousel_media_count: Optional[int] = None
    carousel_media: Optional[List[CarouselMedia]] = None
    product_type: Optional[str] = None
    nearly_complete_copyright_match: Optional[bool] = None
    media_cropping_info: Optional[dict[str, Any]] = None
    thumbnails: Optional[Thumbnails] = None
    igtv_exists_in_viewer_series: Optional[bool] = None
    is_post_live: Optional[bool] = None
    image_versions2: Optional[ImageVersions2] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None
    user: Optional[User] = None
    can_viewer_reshare: Optional[bool] = None
    like_count: Optional[int] = None
    has_liked: Optional[bool] = None
    top_likers: Optional[list] = None
    facepile_top_likers: Optional[list] = None
    photo_of_you: Optional[bool] = None
    usertags: Optional[Usertags] = None
    is_organic_product_tagging_eligible: Optional[bool] = None
    can_see_insights_as_brand: Optional[bool] = None
    mashup_info: Optional[MashupInfo] = None
    video_subtitles_confidence: Optional[float] = None
    video_subtitles_uri: Optional[str] = None
    is_dash_eligible: Optional[int] = None
    video_dash_manifest: Optional[str] = None
    video_codec: Optional[str] = None
    number_of_qualities: Optional[int] = None
    video_versions: Optional[List[VideoVersion]] = None
    has_audio: Optional[bool] = None
    video_duration: Optional[float] = None
    view_count: Optional[int] = None
    caption: Optional[Caption] = None
    featured_products_cta: Optional[Any] = None
    comment_inform_treatment: Optional[CommentInformTreatment] = None
    sharing_friction_info: Optional[SharingFrictionInfo] = None
    can_viewer_save: Optional[bool] = None
    is_in_profile_grid: Optional[bool] = None
    profile_grid_control_enabled: Optional[bool] = None
    organic_tracking_token: Optional[str] = None
    has_shared_to_fb: Optional[int] = None
    deleted_reason: Optional[int] = None
    integrity_review_decision: Optional[str] = None
    commerce_integrity_review_decision: Optional[Any] = None
    music_metadata: Optional[MusicMetadata] = None
    is_artist_pick: Optional[bool] = None


class PostModel(BaseModel):
    items: Optional[List[Item]] = None
    num_results: Optional[int] = None
    more_available: Optional[bool] = None
    auto_load_more_enabled: Optional[bool] = None
    status: Optional[str] = None


class Comment(BaseModel):
    pk: Optional[str] = None
    user_id: Optional[int] = None
    text: Optional[str] = None
    type: Optional[int] = None
    created_at: Optional[int] = None
    created_at_utc: Optional[int] = None
    content_type: Optional[str] = None
    status: Optional[str] = None
    bit_flags: Optional[int] = None
    did_report_as_spam: Optional[bool] = None
    share_enabled: Optional[bool] = None
    user: Optional[InstagramUserResponse] = None
    is_covered: Optional[bool] = None
    media_id: Optional[str] = None
    has_liked_comment: Optional[bool] = None
    comment_like_count: Optional[int] = None
    private_reply_status: Optional[int] = None


class InstagramPostItem(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    reply_count: Optional[int] = None
    taken_at: Optional[int] = None
    comment_count: Optional[int] = None
    is_video: Optional[bool] = False
    like_count: Optional[int] = None
    view_count: Optional[int] = None
    sidecars: Optional[List[InstagramCarouselMediaResponse]] = []
    sidecar_count: Optional[int] = None
    image_url: Optional[str] = None
    image_filename: Optional[str] = None
    video_url: Optional[str] = None
    video_filename: Optional[str] = None
    video_duration: Optional[float] = None
    caption: Optional[Caption] = None
    preview_image_url: Optional[str] = None
    preview_image_filename: Optional[str] = None


class InstagramPostResponse(BaseModel):
    num_results: Optional[int] = 0
    share_url: Optional[str] = None
    author: Optional[InstagramUserResponse] = None
    items: Optional[List[InstagramPostItem]] = []


class InstagramPostRequest(BaseModel):
    content: Optional[str] = None
    user_id: Optional[int] = None
    guild_id: Optional[int] = None
