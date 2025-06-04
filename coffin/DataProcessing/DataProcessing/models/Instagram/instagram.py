from __future__ import annotations

from typing import Any, List, Optional, Union

from loguru import logger as log
from pydantic import BaseModel, Field


class BioLink(BaseModel):
    title: Optional[str] = None
    lynx_url: Optional[str] = None
    url: Optional[str] = None
    link_type: Optional[str] = None


class BiographyWithEntities(BaseModel):
    raw_text: Optional[str] = None
    entities: Optional[list] = None


class ClipsMusicAttributionInfo(BaseModel):
    artist_name: Optional[str] = None
    song_name: Optional[str] = None
    uses_original_audio: Optional[bool] = None
    should_mute_audio: Optional[bool] = None
    should_mute_audio_reason: Optional[str] = None
    audio_id: Optional[str] = None


class CoauthorProducer(BaseModel):
    id: Optional[int] = None
    is_verified: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    username: Optional[str] = None


class DashInfo(BaseModel):
    is_dash_eligible: Optional[bool] = None
    video_dash_manifest: Optional[str] = None
    number_of_qualities: Optional[int] = None


class Dimensions(BaseModel):
    height: Optional[int] = None
    width: Optional[int] = None


class EdgeFollowClass(BaseModel):
    count: Optional[int] = None


class FluffyNode(BaseModel):
    text: Optional[str] = None


class NodeUser(BaseModel):
    full_name: Optional[str] = None
    followed_by_viewer: Optional[bool] = None
    id: Optional[str] = None
    is_verified: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    username: Optional[str] = None


class Location(BaseModel):
    id: Optional[int] = None
    has_public_page: Optional[bool] = None
    name: Optional[str] = None
    slug: Optional[str] = None


class Owner(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None


class SharingFrictionInfo(BaseModel):
    should_have_sharing_friction: Optional[bool] = None
    bloks_app_url: Optional[Any] = None


class ThumbnailResource(BaseModel):
    src: Optional[str] = None
    config_width: Optional[int] = None
    config_height: Optional[int] = None


class PageInfo(BaseModel):
    has_next_page: Optional[bool] = None
    end_cursor: Optional[str] = None


class StickyNode(BaseModel):
    username: Optional[str] = None


class EdgeMediaToCaptionEdge(BaseModel):
    node: Optional[FluffyNode] = None


class TentacledNode(BaseModel):
    user: Optional[NodeUser] = None
    x: Optional[float] = None
    y: Optional[float] = None


class EdgeMutualFollowedByEdge(BaseModel):
    node: Optional[StickyNode] = None


class EdgeMediaToCaption(BaseModel):
    edges: Optional[List[EdgeMediaToCaptionEdge]] = None


class EdgeMediaToTaggedUserEdge(BaseModel):
    node: Optional[TentacledNode] = None


class EdgeMutualFollowedBy(BaseModel):
    count: Optional[int] = None
    edges: Optional[List[EdgeMutualFollowedByEdge]] = None


class EdgeMediaToTaggedUser(BaseModel):
    edges: Optional[List[EdgeMediaToTaggedUserEdge]] = None


class PurpleNode(BaseModel):
    field__typename: Optional[str] = Field(None, alias="__typename")
    id: Optional[str] = None
    shortcode: Optional[str] = None
    dimensions: Optional[Dimensions] = None
    display_url: Optional[str] = None
    edge_media_to_tagged_user: Optional[EdgeMediaToTaggedUser] = None
    fact_check_overall_rating: Optional[Any] = None
    fact_check_information: Optional[Any] = None
    gating_info: Optional[Any] = None
    sharing_friction_info: Optional[SharingFrictionInfo] = None
    media_overlay_info: Optional[Any] = None
    media_preview: Optional[str] = None
    owner: Optional[Owner] = None
    is_video: Optional[bool] = None
    has_upcoming_event: Optional[bool] = None
    accessibility_caption: Optional[str] = None
    dash_info: Optional[DashInfo] = None
    has_audio: Optional[bool] = None
    tracking_token: Optional[str] = None
    video_url: Optional[str] = None
    video_view_count: Optional[int] = None
    edge_media_to_caption: Optional[EdgeMediaToCaption] = None
    edge_media_to_comment: Optional[EdgeFollowClass] = None
    comments_disabled: Optional[bool] = None
    taken_at_timestamp: Optional[int] = None
    edge_liked_by: Optional[EdgeFollowClass] = None
    edge_media_preview_like: Optional[EdgeFollowClass] = None
    location: Optional[Location] = None
    nft_asset_info: Optional[Any] = None
    thumbnail_src: Optional[str] = None
    thumbnail_resources: Optional[List[ThumbnailResource]] = None
    felix_profile_grid_crop: Optional[Any] = None
    coauthor_producers: Optional[List[CoauthorProducer]] = None
    pinned_for_users: Optional[List[CoauthorProducer]] = None
    viewer_can_reshare: Optional[bool] = None
    encoding_status: Optional[Any] = None
    is_published: Optional[bool] = None
    product_type: Optional[str] = None
    title: Optional[str] = None
    video_duration: Optional[float] = None
    clips_music_attribution_info: Optional[ClipsMusicAttributionInfo] = None


class EdgeFelixVideoTimelineEdge(BaseModel):
    node: Optional[PurpleNode] = None


class EdgeFelixVideoTimelineClass(BaseModel):
    count: Optional[int] = None
    page_info: Optional[PageInfo] = None
    edges: Optional[List[EdgeFelixVideoTimelineEdge]] = None


class InstagramProfileModel(BaseModel):
    biography: Optional[str] = None
    bio_links: Optional[List[BioLink]] = None
    biography_with_entities: Optional[BiographyWithEntities] = None
    blocked_by_viewer: Optional[bool] = None
    restricted_by_viewer: Optional[bool] = None
    country_block: Optional[bool] = None
    external_url: Optional[str] = None
    external_url_linkshimmed: Optional[str] = None
    edge_followed_by: Optional[EdgeFollowClass] = None
    fbid: Optional[str] = None
    followed_by_viewer: Optional[bool] = None
    edge_follow: Optional[EdgeFollowClass] = None
    follows_viewer: Optional[bool] = None
    full_name: Optional[str] = None
    group_metadata: Optional[Any] = None
    has_ar_effects: Optional[bool] = None
    has_clips: Optional[bool] = None
    has_guides: Optional[bool] = None
    has_channel: Optional[bool] = None
    has_blocked_viewer: Optional[bool] = None
    highlight_reel_count: Optional[int] = None
    has_requested_viewer: Optional[bool] = None
    hide_like_and_view_counts: Optional[bool] = None
    id: Optional[int] = None
    is_business_account: Optional[bool] = None
    is_professional_account: Optional[bool] = None
    is_supervision_enabled: Optional[bool] = None
    is_guardian_of_viewer: Optional[bool] = None
    is_supervised_by_viewer: Optional[bool] = None
    is_supervised_user: Optional[bool] = None
    is_embeds_disabled: Optional[bool] = None
    is_joined_recently: Optional[bool] = None
    guardian_id: Optional[Any] = None
    business_address_json: Optional[Any] = None
    business_contact_method: Optional[str] = None
    business_email: Optional[Any] = None
    business_phone_number: Optional[Any] = None
    business_category_name: Optional[Any] = None
    overall_category_name: Optional[Any] = None
    category_enum: Optional[Any] = None
    category_name: Optional[str] = None
    is_private: Optional[bool] = None
    is_verified: Optional[bool] = None
    edge_mutual_followed_by: Optional[EdgeMutualFollowedBy] = None
    profile_pic_url: Optional[str] = None
    profile_pic_url_hd: Optional[str] = None
    requested_by_viewer: Optional[bool] = None
    should_show_category: Optional[bool] = None
    should_show_public_contacts: Optional[bool] = None
    show_account_transparency_details: Optional[bool] = None
    transparency_label: Optional[Any] = None
    transparency_product: Optional[str] = None
    username: Optional[str] = None
    connected_fb_page: Optional[Any] = None
    pronouns: Optional[list] = None
    edge_felix_video_timeline: Optional[EdgeFelixVideoTimelineClass] = None
    edge_owner_to_timeline_media: Optional[EdgeFelixVideoTimelineClass] = None
    edge_saved_media: Optional[EdgeFelixVideoTimelineClass] = None
    edge_media_collections: Optional[EdgeFelixVideoTimelineClass] = None
    followed_by_count: Optional[int] = None
    following_count: Optional[int] = None
    post_count: Optional[int] = None

    @classmethod
    async def from_web_info_response(cls, data: dict):
        user = data["data"]["user"]

        cls = cls.parse_obj(user)
        try:
            cls.followed_by_count = user["edge_followed_by"]["count"]
        except KeyError:
            log.error("Unable to extract edge_followed_by")
        try:
            cls.following_count = user["edge_follow"]["count"]
        except KeyError:
            log.error("Unable to extract edge_follow")
        try:
            cls.post_count = user["edge_owner_to_timeline_media"]["count"]
        except KeyError:
            log.error("Unable to get post count..")
        return cls


class Data(BaseModel):
    user: Optional[InstagramProfileModel] = None


class TopLevel(BaseModel):
    data: Optional[Data] = None
    status: Optional[str] = None


def shortcode_to_mediaid(shortcode) -> int:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    mediaid = 0
    for letter in shortcode:
        mediaid = (mediaid * 64) + alphabet.index(letter)
    return mediaid


class UserPostItem(BaseModel):
    id: Optional[str] = None
    shortcode: Optional[str] = None
    url: Optional[str] = None
    is_video: Optional[bool] = None
    taken_at_timestamp: Optional[int] = None
    title: Optional[str] = None
    display_url: Optional[str] = None
    video_url: Optional[str] = None
    comment_count: Optional[int] = 0
    view_count: Optional[int] = 0
    like_count: Optional[int] = 0


class InstagramProfileModelResponse(BaseModel):
    avatar_filename: Optional[str] = None
    avatar_url: Optional[str] = None
    bio_links: Optional[List[Any]] = None
    biography: Optional[str] = None
    external_url: Optional[str] = None
    followed_by_count: Optional[int] = None
    following_count: Optional[int] = None
    full_name: Optional[str] = None
    has_channel: Optional[bool] = None
    has_clips: Optional[bool] = None
    highlight_reel_count: Optional[int] = None
    id: Optional[Union[int, str]] = None
    is_business_account: Optional[bool] = None
    is_joined_recently: Optional[bool] = None
    is_private: Optional[bool] = None
    is_professional_account: Optional[bool] = None
    is_verified: Optional[bool] = None
    post_count: Optional[int] = None
    pronouns: Optional[List[str]] = None
    username: Optional[str] = None
    post_items: Optional[List[UserPostItem]] = []
    created_at: Optional[float] = None
