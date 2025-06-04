import asyncio  # noqa: F401  # type: ignore
import io
import pathlib
from random import shuffle
from typing import Any, Dict
from typing import List
from typing import List as array
from typing import Optional  # type: ignore
from typing import Optional as pos
from typing import Union as one

import aiohttp
import discord
from discord import Message
from discord.ext.commands import Context
from discord.ext.commands.errors import CommandError
from munch import DefaultMunch
from pydantic import BaseModel, Field
from tools.important import \
    EmbedBuilder as Builder  # type: ignore  # noqa: F401


class YouTubeAuthor(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    channel_url: Optional[str] = None
    is_live: Optional[bool] = None
    follower_count: Optional[int] = None


class YouTube(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    thumbnail: None = None
    description: Optional[str] = None
    full_title: Optional[str] = None
    was_live: Optional[bool] = None
    url: Optional[str] = None
    duration: Optional[int] = None
    fps: Optional[int] = None
    created_at: Optional[int] = None
    author: Optional[YouTubeAuthor] = None
    view_count: Optional[int] = None
    original_url: Optional[str] = None
    comment_count: Optional[int] = None


class BioLink(BaseModel):
    title: Optional[str] = None
    lynx_url: Optional[str] = None
    url: Optional[str] = None
    link_type: Optional[str] = None


class BiographyWithEntities(BaseModel):
    raw_text: Optional[str] = None
    entities: Optional[List] = None


class EdgeFollowedBy(BaseModel):
    count: Optional[int] = None


class EdgeFollow(BaseModel):
    count: Optional[int] = None


class EdgeMutualFollowedBy(BaseModel):
    count: Optional[int] = None
    edges: Optional[List] = None


class PageInfo(BaseModel):
    has_next_page: Optional[bool] = None
    end_cursor: Optional[str] = None


class Dimensions(BaseModel):
    height: Optional[int] = None
    width: Optional[int] = None


class User1(BaseModel):
    full_name: Optional[str] = None
    followed_by_viewer: Optional[bool] = None
    id: Optional[str] = None
    is_verified: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    username: Optional[str] = None


class Node1(BaseModel):
    user: Optional[User1] = None
    x: Optional[float] = None
    y: Optional[float] = None


class Edge1(BaseModel):
    node: Optional[Node1] = None


class EdgeMediaToTaggedUser(BaseModel):
    edges: Optional[List[Edge1]] = None


class SharingFrictionInfo(BaseModel):
    should_have_sharing_friction: Optional[bool] = None
    bloks_app_url: Optional[Any] = None


class Owner(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None


class DashInfo(BaseModel):
    is_dash_eligible: Optional[bool] = None
    video_dash_manifest: Optional[Any] = None
    number_of_qualities: Optional[int] = None


class Node2(BaseModel):
    text: Optional[str] = None


class Edge2(BaseModel):
    node: Optional[Node2] = None


class EdgeMediaToCaption(BaseModel):
    edges: Optional[List[Edge2]] = None


class EdgeMediaToComment(BaseModel):
    count: Optional[int] = None


class EdgeLikedBy(BaseModel):
    count: Optional[int] = None


class EdgeMediaPreviewLike(BaseModel):
    count: Optional[int] = None


class ThumbnailResource(BaseModel):
    src: Optional[str] = None
    config_width: Optional[int] = None
    config_height: Optional[int] = None


class CoauthorProducer(BaseModel):
    id: Optional[str] = None
    is_verified: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    username: Optional[str] = None


class Node(BaseModel):
    __typename: Optional[str] = None  # type: ignore
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
    media_preview: Optional[Optional[str]] = None
    owner: Optional[Owner] = None
    is_video: Optional[bool] = None
    has_upcoming_event: Optional[bool] = None
    accessibility_caption: Optional[Any] = None
    dash_info: Optional[DashInfo] = None
    has_audio: Optional[bool] = None
    tracking_token: Optional[str] = None
    video_url: Optional[str] = None
    video_view_count: Optional[int] = None
    edge_media_to_caption: Optional[EdgeMediaToCaption] = None
    edge_media_to_comment: Optional[EdgeMediaToComment] = None
    comments_disabled: Optional[bool] = None
    taken_at_timestamp: Optional[int] = None
    edge_liked_by: Optional[EdgeLikedBy] = None
    edge_media_preview_like: Optional[EdgeMediaPreviewLike] = None
    location: Optional[Any] = None
    nft_asset_info: Optional[Any] = None
    thumbnail_src: Optional[str] = None
    thumbnail_resources: Optional[List[ThumbnailResource]] = None
    felix_profile_grid_crop: Optional[Any] = None
    coauthor_producers: Optional[List[CoauthorProducer]] = None
    pinned_for_users: Optional[List] = None
    viewer_can_reshare: Optional[bool] = None
    encoding_status: Optional[Any] = None
    is_published: Optional[bool] = None
    product_type: Optional[str] = None
    title: Optional[str] = None
    video_duration: Optional[float] = None


class Edge(BaseModel):
    node: Optional[Node] = None


class EdgeFelixVideoTimeline(BaseModel):
    count: Optional[int] = None
    page_info: Optional[PageInfo] = None
    edges: Optional[List[Edge]] = None


class PageInfo1(BaseModel):
    has_next_page: Optional[bool] = None
    end_cursor: Optional[str] = None


class Dimensions1(BaseModel):
    height: Optional[int] = None
    width: Optional[int] = None


class User2(BaseModel):
    full_name: Optional[str] = None
    followed_by_viewer: Optional[bool] = None
    id: Optional[str] = None
    is_verified: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    username: Optional[str] = None


class Node4(BaseModel):
    user: Optional[User2] = None
    x: Optional[float] = None
    y: Optional[float] = None


class Edge4(BaseModel):
    node: Optional[Node4] = None


class EdgeMediaToTaggedUser1(BaseModel):
    edges: Optional[List[Edge4]] = None


class SharingFrictionInfo1(BaseModel):
    should_have_sharing_friction: Optional[bool] = None
    bloks_app_url: Optional[Any] = None


class Owner1(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None


class Node5(BaseModel):
    text: Optional[str] = None


class Edge5(BaseModel):
    node: Optional[Node5] = None


class EdgeMediaToCaption1(BaseModel):
    edges: Optional[List[Edge5]] = None


class EdgeMediaToComment1(BaseModel):
    count: Optional[int] = None


class EdgeLikedBy1(BaseModel):
    count: Optional[int] = None


class EdgeMediaPreviewLike1(BaseModel):
    count: Optional[int] = None


class ThumbnailResource1(BaseModel):
    src: Optional[str] = None
    config_width: Optional[int] = None
    config_height: Optional[int] = None


class CoauthorProducer1(BaseModel):
    id: Optional[str] = None
    is_verified: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    username: Optional[str] = None


class Dimensions2(BaseModel):
    height: Optional[int] = None
    width: Optional[int] = None


class User3(BaseModel):
    full_name: Optional[str] = None
    followed_by_viewer: Optional[bool] = None
    id: Optional[str] = None
    is_verified: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    username: Optional[str] = None


class Node7(BaseModel):
    user: Optional[User3] = None
    x: Optional[float] = None
    y: Optional[float] = None


class Edge7(BaseModel):
    node: Optional[Node7] = None


class EdgeMediaToTaggedUser2(BaseModel):
    edges: Optional[List[Edge7]] = None


class SharingFrictionInfo2(BaseModel):
    should_have_sharing_friction: Optional[bool] = None
    bloks_app_url: Optional[Any] = None


class Owner2(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None


class Node6(BaseModel):
    __typename: Optional[str] = None  # type: ignore
    id: Optional[str] = None
    shortcode: Optional[str] = None
    dimensions: Optional[Dimensions2] = None
    display_url: Optional[str] = None
    edge_media_to_tagged_user: Optional[EdgeMediaToTaggedUser2] = None
    fact_check_overall_rating: Optional[Any] = None
    fact_check_information: Optional[Any] = None
    gating_info: Optional[Any] = None
    sharing_friction_info: Optional[SharingFrictionInfo2] = None
    media_overlay_info: Optional[Any] = None
    media_preview: Optional[Optional[str]] = None
    owner: Optional[Owner2] = None
    is_video: Optional[bool] = None
    has_upcoming_event: Optional[bool] = None
    accessibility_caption: Optional[str] = None


class Edge6(BaseModel):
    node: Optional[Node6] = None


class EdgeSidecarToChildren(BaseModel):
    edges: Optional[List[Edge6]] = None


class DashInfo1(BaseModel):
    is_dash_eligible: Optional[bool] = None
    video_dash_manifest: Optional[Any] = None
    number_of_qualities: Optional[int] = None


class ClipsMusicAttributionInfo(BaseModel):
    artist_name: Optional[str] = None
    song_name: Optional[str] = None
    uses_original_audio: Optional[bool] = None
    should_mute_audio: Optional[bool] = None
    should_mute_audio_reason: Optional[str] = None
    audio_id: Optional[str] = None


class Node3(BaseModel):
    __typename: Optional[str] = None  # type: ignore
    id: Optional[str] = None
    shortcode: Optional[str] = None
    dimensions: Optional[Dimensions1] = None
    display_url: Optional[str] = None
    edge_media_to_tagged_user: Optional[EdgeMediaToTaggedUser1] = None
    fact_check_overall_rating: Optional[Any] = None
    fact_check_information: Optional[Any] = None
    gating_info: Optional[Any] = None
    sharing_friction_info: Optional[SharingFrictionInfo1] = None
    media_overlay_info: Optional[Any] = None
    media_preview: Optional[Optional[str]] = None
    owner: Optional[Owner1] = None
    is_video: Optional[bool] = None
    has_upcoming_event: Optional[bool] = None
    accessibility_caption: Optional[Optional[str]] = None
    edge_media_to_caption: Optional[EdgeMediaToCaption1] = None
    edge_media_to_comment: Optional[EdgeMediaToComment1] = None
    comments_disabled: Optional[bool] = None
    taken_at_timestamp: Optional[int] = None
    edge_liked_by: Optional[EdgeLikedBy1] = None
    edge_media_preview_like: Optional[EdgeMediaPreviewLike1] = None
    location: Optional[Any] = None
    nft_asset_info: Optional[Any] = None
    thumbnail_src: Optional[str] = None
    thumbnail_resources: Optional[List[ThumbnailResource1]] = None
    coauthor_producers: Optional[List[CoauthorProducer1]] = None
    pinned_for_users: Optional[List] = None
    viewer_can_reshare: Optional[bool] = None
    edge_sidecar_to_children: Optional[EdgeSidecarToChildren] = None
    dash_info: Optional[DashInfo1] = None
    has_audio: Optional[bool] = None
    tracking_token: Optional[str] = None
    video_url: Optional[str] = None
    video_view_count: Optional[int] = None
    felix_profile_grid_crop: Optional[Any] = None
    product_type: Optional[str] = None
    clips_music_attribution_info: Optional[ClipsMusicAttributionInfo] = None


class Edge3(BaseModel):
    node: Optional[Node3] = None


class EdgeOwnerToTimelineMedia(BaseModel):
    count: Optional[int] = None
    page_info: Optional[PageInfo1] = None
    edges: Optional[List[Edge3]] = None


class PageInfo2(BaseModel):
    has_next_page: Optional[bool] = None
    end_cursor: Optional[Any] = None


class EdgeSavedMedia(BaseModel):
    count: Optional[int] = None
    page_info: Optional[PageInfo2] = None
    edges: Optional[List] = None


class PageInfo3(BaseModel):
    has_next_page: Optional[bool] = None
    end_cursor: Optional[Any] = None


class EdgeMediaCollections(BaseModel):
    count: Optional[int] = None
    page_info: Optional[PageInfo3] = None
    edges: Optional[List] = None


class Node8(BaseModel):
    id: Optional[str] = None
    full_name: Optional[str] = None
    is_private: Optional[bool] = None
    is_verified: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    username: Optional[str] = None


class Edge8(BaseModel):
    node: Optional[Node8] = None


class EdgeRelatedProfiles(BaseModel):
    edges: Optional[List[Edge8]] = None


class User(BaseModel):
    ai_agent_type: Optional[Any] = None
    biography: Optional[str] = None
    bio_links: Optional[List[BioLink]] = None
    fb_profile_biolink: Optional[Any] = None
    biography_with_entities: Optional[BiographyWithEntities] = None
    blocked_by_viewer: Optional[bool] = None
    restricted_by_viewer: Optional[Any] = None
    country_block: Optional[bool] = None
    eimu_id: Optional[str] = None
    external_url: Optional[str] = None
    external_url_linkshimmed: Optional[str] = None
    edge_followed_by: Optional[EdgeFollowedBy] = None
    fbid: Optional[str] = None
    followed_by_viewer: Optional[bool] = None
    edge_follow: Optional[EdgeFollow] = None
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
    id: Optional[str] = None
    is_business_account: Optional[bool] = None
    is_professional_account: Optional[bool] = None
    is_supervision_enabled: Optional[bool] = None
    is_guardian_of_viewer: Optional[bool] = None
    is_supervised_by_viewer: Optional[bool] = None
    is_supervised_user: Optional[bool] = None
    is_embeds_disabled: Optional[bool] = None
    is_joined_recently: Optional[bool] = None
    guardian_id: Optional[Any] = None
    business_address_json: Optional[str] = None
    business_contact_method: Optional[str] = None
    business_email: Optional[Any] = None
    business_phone_number: Optional[Any] = None
    business_category_name: Optional[Any] = None
    overall_category_name: Optional[Any] = None
    category_enum: Optional[Any] = None
    category_name: Optional[str] = None
    is_private: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_verified_by_mv4b: Optional[bool] = None
    is_regulated_c18: Optional[bool] = None
    edge_mutual_followed_by: Optional[EdgeMutualFollowedBy] = None
    pinned_channels_list_count: Optional[int] = None
    profile_pic_url: Optional[str] = None
    profile_pic_url_hd: Optional[str] = None
    requested_by_viewer: Optional[bool] = None
    should_show_category: Optional[bool] = None
    should_show_public_contacts: Optional[bool] = None
    show_account_transparency_details: Optional[bool] = None
    remove_message_entrypoint: Optional[bool] = None
    transparency_label: Optional[Any] = None
    transparency_product: Optional[Any] = None
    username: Optional[str] = None
    connected_fb_page: Optional[Any] = None
    pronouns: Optional[List] = None
    edge_felix_video_timeline: Optional[EdgeFelixVideoTimeline] = None
    edge_owner_to_timeline_media: Optional[EdgeOwnerToTimelineMedia] = None
    edge_saved_media: Optional[EdgeSavedMedia] = None
    edge_media_collections: Optional[EdgeMediaCollections] = None
    edge_related_profiles: Optional[EdgeRelatedProfiles] = None


class Object:
    def __init__(self, data: dict):
        return DefaultMunch(object(), data)


class YouTubeChannel(BaseModel):
    id: pos[str] = None
    name: pos[str] = ""
    channel_url: pos[str] = None
    is_live: pos[bool] = False
    follower_count: pos[int] = 0


class YouTubePost(BaseModel):
    id: pos[str] = None
    title: pos[str] = ""
    thumbnail: pos[str] = None
    description: pos[str] = ""
    full_title: pos[str] = ""
    was_live: pos[bool] = False
    url: pos[str] = None
    duration: pos[int] = 0
    fps: pos[int] = 0
    created_at: pos[int] = 0
    author: pos[YouTubeChannel] = None
    view_count: pos[int] = 0
    original_url: pos[str] = None
    comment_count: pos[int] = 0


class FanClubInfo(BaseModel):
    fan_club_id: pos[Any] = None
    fan_club_name: pos[Any] = None
    is_fan_club_referral_eligible: pos[Any] = None
    fan_consideration_page_revamp_eligiblity: pos[Any] = None
    is_fan_club_gifting_eligible: pos[Any] = None
    subscriber_count: pos[Any] = None
    connected_member_count: pos[Any] = None
    autosave_to_exclusive_highlight: pos[Any] = None
    has_enough_subscribers_for_ssc: pos[Any] = None


class FriendshipStatus(BaseModel):
    following: pos[bool] = None
    is_bestie: pos[bool] = None
    is_restricted: pos[bool] = None
    is_feed_favorite: pos[bool] = None


class HdProfilePicUrlInfo(BaseModel):
    url: pos[str] = None
    width: pos[int] = None
    height: pos[int] = None


class HdProfilePicVersion(BaseModel):
    width: pos[int] = None
    height: pos[int] = None
    url: pos[str] = None


class InstagramMetrics(BaseModel):
    count: int


class InstagramProfile(BaseModel):
    id: int
    username: str
    full_name: str
    biography: pos[str]
    avatar: str
    profile_pic_url_hd: str
    is_private: bool
    is_verified: bool
    edge_owner_to_timeline_media: InstagramMetrics
    edge_followed_by: InstagramMetrics
    edge_follow: InstagramMetrics


class UUSER(BaseModel):
    fbid_v2: pos[int] = None
    feed_post_reshare_disabled: pos[bool] = None
    full_name: pos[str] = None
    id: pos[str] = None
    is_private: pos[bool] = None
    is_unpublished: pos[bool] = None
    pk: pos[int] = None
    pk_id: pos[str] = None
    show_account_transparency_details: pos[bool] = None
    strong_id__: pos[str] = None
    third_party_downloads_enabled: pos[int] = None
    username: pos[str] = None
    account_badges: pos[array] = None
    fan_club_info: pos[FanClubInfo] = None
    friendship_status: pos[FriendshipStatus] = None
    has_anonymous_profile_picture: pos[bool] = None
    hd_profile_pic_url_info: pos[HdProfilePicUrlInfo] = None
    hd_profile_pic_versions: pos[array[HdProfilePicVersion]] = None
    is_favorite: pos[bool] = None
    is_verified: pos[bool] = None
    latest_reel_media: pos[int] = None
    profile_pic_id: pos[str] = None
    profile_pic_url: pos[str] = None
    transparency_product_enabled: pos[bool] = None


class Caption(BaseModel):
    pk: pos[str] = None
    user_id: pos[int] = None
    user: pos[UUSER] = None
    type: pos[int] = None
    text: pos[str] = None
    did_report_as_spam: pos[bool] = None
    created_at: pos[int] = None
    created_at_utc: pos[int] = None
    content_type: pos[str] = None
    status: pos[str] = None
    bit_flags: pos[int] = None
    share_enabled: pos[bool] = None
    is_ranked_comment: pos[bool] = None
    is_covered: pos[bool] = None
    private_reply_status: pos[int] = None
    media_id: pos[int] = None


class CommentInformTreatment(BaseModel):
    should_have_inform_treatment: pos[bool] = None
    text: pos[str] = None
    url: pos[Any] = None
    action_type: pos[Any] = None


class SharingFrictionInfo(BaseModel):
    should_have_sharing_friction: pos[bool] = None
    bloks_app_url: pos[Any] = None
    sharing_friction_payload: pos[Any] = None


class MediaAppreciationSettings(BaseModel):
    media_gifting_state: pos[str] = None
    gift_count_visibility: pos[str] = None


class FbUserTags(BaseModel):
    in_: pos[array] = Field(None, alias="in")


class HighlightsInfo(BaseModel):
    added_to: pos[array] = None


class SquareCrop(BaseModel):
    crop_bottom: pos[float] = None
    crop_left: pos[float] = None
    crop_right: pos[float] = None
    crop_top: pos[float] = None


class MediaCroppingInfo(BaseModel):
    feed_preview_crop: pos[Any] = None
    square_crop: pos[SquareCrop] = None
    three_by_four_preview_crop: pos[Any] = None


class FanClubInfo1(BaseModel):
    fan_club_id: pos[Any] = None
    fan_club_name: pos[Any] = None
    is_fan_club_referral_eligible: pos[Any] = None
    fan_consideration_page_revamp_eligiblity: pos[Any] = None
    is_fan_club_gifting_eligible: pos[Any] = None
    subscriber_count: pos[Any] = None
    connected_member_count: pos[Any] = None
    autosave_to_exclusive_highlight: pos[Any] = None
    has_enough_subscribers_for_ssc: pos[Any] = None


class FriendshipStatus1(BaseModel):
    following: pos[bool] = None
    is_bestie: pos[bool] = None
    is_restricted: pos[bool] = None
    is_feed_favorite: pos[bool] = None


class HdProfilePicUrlInfo1(BaseModel):
    url: pos[str] = None
    width: pos[int] = None
    height: pos[int] = None


class HdProfilePicVersion1(BaseModel):
    width: pos[int] = None
    height: pos[int] = None
    url: pos[str] = None


class User1(BaseModel):
    fbid_v2: pos[int] = None
    feed_post_reshare_disabled: pos[bool] = None
    full_name: pos[str] = None
    id: pos[str] = None
    is_private: pos[bool] = None
    is_unpublished: pos[bool] = None
    pk: pos[int] = None
    pk_id: pos[str] = None
    show_account_transparency_details: pos[bool] = None
    strong_id__: pos[str] = None
    third_party_downloads_enabled: pos[int] = None
    username: pos[str] = None
    account_badges: pos[array] = None
    fan_club_info: pos[FanClubInfo1] = None
    friendship_status: pos[FriendshipStatus1] = None
    has_anonymous_profile_picture: pos[bool] = None
    hd_profile_pic_url_info: pos[HdProfilePicUrlInfo1] = None
    hd_profile_pic_versions: pos[array[HdProfilePicVersion1]] = None
    is_favorite: pos[bool] = None
    is_verified: pos[bool] = None
    latest_reel_media: pos[int] = None
    profile_pic_id: pos[str] = None
    profile_pic_url: pos[str] = None
    transparency_product_enabled: pos[bool] = None


class Candidate(BaseModel):
    width: pos[int] = None
    height: pos[int] = None
    url: pos[str] = None


class IgtvFirstFrame(BaseModel):
    width: pos[int] = None
    height: pos[int] = None
    url: pos[str] = None


class FirstFrame(BaseModel):
    width: pos[int] = None
    height: pos[int] = None
    url: pos[str] = None


class AdditionalCandidates(BaseModel):
    igtv_first_frame: pos[IgtvFirstFrame] = None
    first_frame: pos[FirstFrame] = None
    smart_frame: pos[Any] = None


class ImageVersions2(BaseModel):
    candidates: pos[array[Candidate]] = None
    additional_candidates: pos[AdditionalCandidates] = None
    smart_thumbnail_enabled: pos[bool] = None


class FanClubInfo2(BaseModel):
    fan_club_id: pos[Any] = None
    fan_club_name: pos[Any] = None
    is_fan_club_referral_eligible: pos[Any] = None
    fan_consideration_page_revamp_eligiblity: pos[Any] = None
    is_fan_club_gifting_eligible: pos[Any] = None
    subscriber_count: pos[Any] = None
    connected_member_count: pos[Any] = None
    autosave_to_exclusive_highlight: pos[Any] = None
    has_enough_subscribers_for_ssc: pos[Any] = None


class FriendshipStatus2(BaseModel):
    following: pos[bool] = None
    is_bestie: pos[bool] = None
    is_restricted: pos[bool] = None
    is_feed_favorite: pos[bool] = None


class HdProfilePicUrlInfo2(BaseModel):
    url: pos[str] = None
    width: pos[int] = None
    height: pos[int] = None


class HdProfilePicVersion2(BaseModel):
    width: pos[int] = None
    height: pos[int] = None
    url: pos[str] = None


class Owner(BaseModel):
    fbid_v2: pos[int] = None
    feed_post_reshare_disabled: pos[bool] = None
    full_name: pos[str] = None
    id: pos[str] = None
    is_private: pos[bool] = None
    is_unpublished: pos[bool] = None
    pk: pos[int] = None
    pk_id: pos[str] = None
    show_account_transparency_details: pos[bool] = None
    strong_id__: pos[str] = None
    third_party_downloads_enabled: pos[int] = None
    username: pos[str] = None
    account_badges: pos[array] = None
    fan_club_info: pos[FanClubInfo2] = None
    friendship_status: pos[FriendshipStatus2] = None
    has_anonymous_profile_picture: pos[bool] = None
    hd_profile_pic_url_info: pos[HdProfilePicUrlInfo2] = None
    hd_profile_pic_versions: pos[array[HdProfilePicVersion2]] = None
    is_favorite: pos[bool] = None
    is_verified: pos[bool] = None
    latest_reel_media: pos[int] = None
    profile_pic_id: pos[str] = None
    profile_pic_url: pos[str] = None
    transparency_product_enabled: pos[bool] = None


class VideoVersion(BaseModel):
    type: pos[int] = None
    width: pos[int] = None
    height: pos[int] = None
    url: pos[str] = None
    id: pos[str] = None


class MusicAssetInfo(BaseModel):
    audio_asset_id: pos[str] = None
    audio_cluster_id: pos[str] = None
    id: pos[str] = None
    title: pos[str] = None
    sanitized_title: pos[Any] = None
    subtitle: pos[str] = None
    display_artist: pos[str] = None
    artist_id: pos[str] = None
    is_explicit: pos[bool] = None
    cover_artwork_uri: pos[str] = None
    cover_artwork_thumbnail_uri: pos[str] = None
    progressive_download_url: pos[str] = None
    reactive_audio_download_url: pos[Any] = None
    fast_start_progressive_download_url: pos[str] = None
    web_30s_preview_download_url: pos[str] = None
    highlight_start_times_in_ms: pos[array[int]] = None
    dash_manifest: pos[Any] = None
    has_lyrics: pos[bool] = None
    duration_in_ms: pos[int] = None
    dark_message: pos[Any] = None
    allows_saving: pos[bool] = None
    ig_username: pos[str] = None
    is_eligible_for_audio_effects: pos[bool] = None


class IgArtist(BaseModel):
    pk: pos[int] = None
    pk_id: pos[str] = None
    username: pos[str] = None
    full_name: pos[str] = None
    is_private: pos[bool] = None
    strong_id__: pos[str] = None
    is_verified: pos[bool] = None
    profile_pic_id: pos[str] = None
    profile_pic_url: pos[str] = None


class AudioMutingInfo(BaseModel):
    allow_audio_editing: pos[bool] = None
    mute_audio: pos[bool] = None
    mute_reason: pos[Any] = None
    mute_reason_str: pos[str] = None
    show_muted_audio_toast: pos[bool] = None


class MusicConsumptionInfo(BaseModel):
    ig_artist: pos[IgArtist] = None
    placeholder_profile_pic_url: pos[str] = None
    should_mute_audio: pos[bool] = None
    should_mute_audio_reason: pos[str] = None
    should_mute_audio_reason_type: pos[Any] = None
    is_bookmarked: pos[bool] = None
    overlap_duration_in_ms: pos[int] = None
    audio_asset_start_time_in_ms: pos[int] = None
    allow_media_creation_with_music: pos[bool] = None
    is_trending_in_clips: pos[bool] = None
    trend_rank: pos[Any] = None
    formatted_clips_media_count: pos[Any] = None
    display_labels: pos[Any] = None
    should_allow_music_editing: pos[bool] = None
    derived_content_id: pos[Any] = None
    audio_filter_infos: pos[array] = None
    audio_muting_info: pos[AudioMutingInfo] = None
    contains_lyrics: pos[Any] = None
    should_render_soundwave: pos[bool] = None


class MusicInfo(BaseModel):
    music_asset_info: pos[MusicAssetInfo] = None
    music_consumption_info: pos[MusicConsumptionInfo] = None
    music_canonical_id: pos[Any] = None


class MashupInfo(BaseModel):
    mashups_allowed: pos[bool] = None
    can_toggle_mashups_allowed: pos[bool] = None
    has_been_mashed_up: pos[bool] = None
    is_light_weight_check: pos[bool] = None
    formatted_mashups_count: pos[Any] = None
    original_media: pos[Any] = None
    privacy_filtered_mashups_media_count: pos[Any] = None
    non_privacy_filtered_mashups_media_count: pos[Any] = None
    mashup_type: pos[Any] = None
    is_creator_requesting_mashup: pos[bool] = None
    has_nonmimicable_additional_audio: pos[bool] = None
    is_pivot_page_available: pos[bool] = None


class Color(BaseModel):
    count: pos[int] = None
    hex_rgba_color: pos[str] = None


class ReusableTextInfoItem(BaseModel):
    id: pos[int] = None
    text: pos[str] = None
    start_time_ms: pos[float] = None
    end_time_ms: pos[float] = None
    width: pos[float] = None
    height: pos[float] = None
    offset_x: pos[float] = None
    offset_y: pos[float] = None
    z_index: pos[int] = None
    rotation_degree: pos[float] = None
    scale: pos[float] = None
    alignment: pos[str] = None
    colors: pos[array[Color]] = None
    text_format_type: pos[str] = None
    font_size: pos[float] = None
    text_emphasis_mode: pos[str] = None
    is_animated: pos[int] = None


class BrandedContentTagInfo(BaseModel):
    can_add_tag: pos[bool] = None


class AudioReattributionInfo(BaseModel):
    should_allow_restore: pos[bool] = None


class AdditionalAudioInfo(BaseModel):
    additional_audio_username: pos[Any] = None
    audio_reattribution_info: pos[AudioReattributionInfo] = None


class AudioRankingInfo(BaseModel):
    best_audio_cluster_id: pos[str] = None


class Pill(BaseModel):
    action_type: pos[str] = None
    priority: pos[int] = None


class Comment(BaseModel):
    action_type: pos[str] = None


class EntryPointContainer(BaseModel):
    pill: pos[Pill] = None
    comment: pos[Comment] = None
    overflow: pos[Any] = None
    ufi: pos[Any] = None


class ContentAppreciationInfo(BaseModel):
    enabled: pos[bool] = None
    entry_point_container: pos[EntryPointContainer] = None


class AchievementsInfo(BaseModel):
    show_achievements: pos[bool] = None
    num_earned_achievements: pos[Any] = None


class ClipsMetadata(BaseModel):
    music_info: pos[MusicInfo] = None
    original_sound_info: pos[Any] = None
    audio_type: pos[str] = None
    music_canonical_id: pos[str] = None
    featured_label: pos[Any] = None
    mashup_info: pos[MashupInfo] = None
    reusable_text_info: pos[array[ReusableTextInfoItem]] = None
    reusable_text_attribute_string: pos[str] = None
    nux_info: pos[Any] = None
    viewer_interaction_settings: pos[Any] = None
    branded_content_tag_info: pos[BrandedContentTagInfo] = None
    shopping_info: pos[Any] = None
    additional_audio_info: pos[AdditionalAudioInfo] = None
    is_shared_to_fb: pos[bool] = None
    breaking_content_info: pos[Any] = None
    challenge_info: pos[Any] = None
    reels_on_the_rise_info: pos[Any] = None
    breaking_creator_info: pos[Any] = None
    asset_recommendation_info: pos[Any] = None
    contextual_highlight_info: pos[Any] = None
    clips_creation_entry_point: pos[str] = None
    audio_ranking_info: pos[AudioRankingInfo] = None
    template_info: pos[Any] = None
    is_fan_club_promo_video: pos[bool] = None
    disable_use_in_clips_client_cache: pos[bool] = None
    content_appreciation_info: pos[ContentAppreciationInfo] = None
    achievements_info: pos[AchievementsInfo] = None
    show_achievements: pos[bool] = None
    show_tips: pos[Any] = None
    merchandising_pill_info: pos[Any] = None
    is_public_chat_welcome_video: pos[bool] = None
    professional_clips_upsell_type: pos[int] = None
    external_media_info: pos[Any] = None
    cutout_sticker_info: pos[Any] = None


class Item(BaseModel):
    taken_at: pos[int] = None
    pk: pos[int] = None
    id: pos[str] = None
    device_timestamp: pos[int] = None
    client_cache_key: pos[str] = None
    filter_type: pos[int] = None
    caption_is_edited: pos[bool] = None
    like_and_view_counts_disabled: pos[bool] = None
    strong_id__: pos[str] = None
    is_reshare_of_text_post_app_media_in_ig: pos[bool] = None
    is_post_live_clips_media: pos[bool] = None
    deleted_reason: pos[int] = None
    integrity_review_decision: pos[str] = None
    has_shared_to_fb: pos[int] = None
    is_unified_video: pos[bool] = None
    should_request_ads: pos[bool] = None
    is_visual_reply_commenter_notice_enabled: pos[bool] = None
    commerciality_status: pos[str] = None
    explore_hide_comments: pos[bool] = None
    has_delayed_metadata: pos[bool] = None
    is_quiet_post: pos[bool] = None
    mezql_token: pos[str] = None
    shop_routing_user_id: pos[Any] = None
    can_see_insights_as_brand: pos[bool] = None
    is_organic_product_tagging_eligible: pos[bool] = None
    fb_like_count: pos[int] = None
    has_liked: pos[bool] = None
    has_privately_liked: pos[bool] = None
    like_count: pos[int] = None
    facepile_top_likers: pos[array] = None
    top_likers: pos[array] = None
    video_subtitles_confidence: pos[float] = None
    video_subtitles_uri: pos[str] = None
    media_type: pos[int] = None
    code: pos[str] = None
    can_viewer_reshare: pos[bool] = None
    caption: pos[Caption] = None
    clips_tab_pinned_user_ids: pos[array] = None
    comment_inform_treatment: pos[CommentInformTreatment] = None
    sharing_friction_info: pos[SharingFrictionInfo] = None
    play_count: pos[int] = None
    fb_play_count: pos[int] = None
    media_appreciation_settings: pos[MediaAppreciationSettings] = None
    original_media_has_visual_reply_media: pos[bool] = None
    fb_user_tags: pos[FbUserTags] = None
    invited_coauthor_producers: pos[array] = None
    can_viewer_save: pos[bool] = None
    is_in_profile_grid: pos[bool] = None
    profile_grid_control_enabled: pos[bool] = None
    featured_products: pos[array] = None
    is_comments_gif_composer_enabled: pos[bool] = None
    highlights_info: pos[HighlightsInfo] = None
    media_cropping_info: pos[MediaCroppingInfo] = None
    product_suggestions: pos[array] = None
    user: pos[User1] = None
    image_versions2: pos[ImageVersions2] = None
    original_width: pos[int] = None
    original_height: pos[int] = None
    is_artist_pick: pos[bool] = None
    enable_media_notes_production: pos[bool] = None
    product_type: pos[str] = None
    is_paid_partnership: pos[bool] = None
    music_metadata: pos[Any] = None
    organic_tracking_token: pos[str] = None
    is_third_party_downloads_eligible: pos[bool] = None
    ig_media_sharing_disabled: pos[bool] = None
    open_carousel_submission_state: pos[str] = None
    is_open_to_public_submission: pos[bool] = None
    comment_threading_enabled: pos[bool] = None
    max_num_visible_preview_comments: pos[int] = None
    has_more_comments: pos[bool] = None
    preview_comments: pos[array] = None
    comments: pos[array] = None
    comment_count: pos[int] = None
    can_view_more_preview_comments: pos[bool] = None
    hide_view_all_comment_entrypoint: pos[bool] = None
    inline_composer_display_condition: pos[str] = None
    is_auto_created: pos[bool] = None
    is_cutout_sticker_allowed: pos[bool] = None
    enable_waist: pos[bool] = None
    owner: pos[Owner] = None
    is_dash_eligible: pos[int] = None
    video_dash_manifest: pos[str] = None
    number_of_qualities: pos[int] = None
    video_versions: pos[array[VideoVersion]] = None
    video_duration: pos[float] = None
    has_audio: pos[bool] = None
    clips_metadata: pos[ClipsMetadata] = None


class InstagramMedia(BaseModel):
    items: pos[array[Item]] = None
    num_results: pos[int] = None
    more_available: pos[bool] = None
    auto_load_more_enabled: pos[bool] = None
    showQRModal: pos[bool] = None


class EdgeOwnerToTimelineMedia(BaseModel):
    count: int


class EdgeFollowedBy(BaseModel):
    count: int


class EdgeFollow(BaseModel):
    count: int


class InstagramUser(BaseModel):
    id: pos[int] = None
    username: pos[str] = None
    full_name: pos[str] = None
    biography: pos[str] = None
    avatar: pos[str] = None
    profile_pic_url_hd: pos[str] = None
    is_private: pos[bool] = None
    is_verified: pos[bool] = None
    edge_owner_to_timeline_media: pos[EdgeOwnerToTimelineMedia] = None
    edge_followed_by: pos[EdgeFollowedBy] = None
    edge_follow: pos[EdgeFollow] = None
    posts: pos[array] = None


string = pos[str]


class ImageResult(BaseModel):
    domain: string = None
    title: string = None
    source: string = None
    url: string = None
    color: string = None


class ImageSearchResponse(BaseModel):
    query_time: pos[one[float, str]] = None
    status: string = "current"
    query: string = None
    safe: string = None
    results: array[ImageResult] = None


class GoogleSearchResult(BaseModel):
    title: pos[str] = None
    alt: pos[str] = None
    website: pos[str] = None
    url: pos[str] = None
    color: pos[str] = None


class GoogleSearchRequest(BaseModel):
    RootModel: array[GoogleSearchResult]


class TikTokUser(BaseModel):
    id: pos[str] = None
    username: pos[str] = None
    display_name: pos[str] = None
    avatar: pos[str] = None
    bio: pos[str] = None
    verified: pos[one[str, bool]] = False
    private: pos[one[str, bool]] = False
    likes: pos[int] = 0
    followers: pos[int] = 0
    following: pos[int] = 0
    videos: pos[int] = 0
    tiktok_logo: pos[str] = None
    tiktok_color: pos[str] = None
    avatar_color: pos[str] = None


class TikTokVideoStatistics(BaseModel):
    aweme_id: pos[str] = None
    comment_count: pos[int] = 0
    digg_count: pos[int] = 0
    download_count: pos[int] = 0
    play_count: pos[int] = 0
    share_count: pos[int] = 0
    lose_count: pos[int] = 0
    lose_comment_count: pos[int] = 0
    whatsapp_share_count: pos[int] = 0
    collect_count: pos[int] = 0


class TikTokPost(BaseModel):
    is_video: pos[bool] = False
    items: array[str]
    desc: pos[str] = None
    username: pos[str] = None
    nickname: pos[str] = None
    avatar: pos[str] = None
    stats: TikTokVideoStatistics
    url: pos[str] = None


class TwitterLinks(BaseModel):
    display_url: pos[str] = None
    expanded_url: pos[str] = None
    url: pos[str] = None
    indices: array[int]


class TwitterUser(BaseModel):
    error: pos[str] = None
    username: pos[str] = None
    nickname: pos[str] = None
    bio: pos[str] = None
    location: pos[str] = None
    links: pos[array[TwitterLinks]] = None
    avatar: pos[str] = None
    banner: pos[str] = None
    tweets: pos[int] = 0
    media: pos[int] = None
    followers: pos[int] = 0
    following: pos[int] = 0
    creation: pos[int] = 0
    private: pos[bool] = False
    verified: pos[bool] = False
    id: pos[one[str, int]] = None


class ColorSearch(BaseModel):
    hex: pos[str] = None


class Card(BaseModel):
    small: str
    large: str
    wide: str
    id: str


class VData(BaseModel):
    puuid: str
    region: str
    account_level: int
    name: str
    tag: str
    card: Card
    last_update: str
    last_update_raw: int


class Valorant(BaseModel):
    error: pos[str] = None
    status: pos[int] = None
    data: pos[VData] = None


class Fields(BaseModel):
    name: str
    value: str
    inline: bool


class Author(BaseModel):
    name: str
    url: str
    icon_url: str


class Image(BaseModel):
    url: str


class Thumbnail(BaseModel):
    url: str


class Footer(BaseModel):
    text: str
    icon_url: str


class Embeds(BaseModel):
    fields: array[Fields]
    author: Author
    title: str
    description: str
    image: Image
    thumbnail: Thumbnail
    color: int
    footer: Footer
    timestamp: str


class Embed(BaseModel):
    error: pos[str] = None
    content: pos[str] = None
    embed: pos[Embeds] = None
    delete_after: pos[int] = None


class EmbedFetch(BaseModel):
    status: pos[str] = None
    embed: pos[str] = None


class RobloxStatistics(BaseModel):
    friends: pos[int] = 0
    followers: pos[int] = 0
    following: pos[int] = 0


class Roblox(BaseModel):
    error: pos[str] = None
    url: pos[str] = None
    id: pos[int] = None
    username: pos[str] = None
    display_name: pos[str] = None
    avatar_url: pos[str] = None
    description: pos[Any] = None
    created_at: pos[int] = None
    last_online: pos[Any] = None
    last_location: pos[Any] = None
    badges: pos[array] = None
    statistics: pos[RobloxStatistics] = None


class Statistics(BaseModel):
    files: str
    imports: str
    lines: str
    classes: str
    functions: str
    coroutines: str
    uptime: str


class _MainResult(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    snippet: Optional[str] = None
    full_info: Optional[Dict[str, Any]] = None


class _Result(BaseModel):
    domain: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None


class GoogleSearchResponse(BaseModel):
    query_time: Optional[float] = None
    query: Optional[str] = None
    safe: Optional[str] = None
    main_result: Optional[_MainResult] = None
    results: Optional[List[_Result]] = None


async def get_statistics(bot):  # type: ignore
    p = pathlib.Path("./")
    imp = cm = cr = fn = cl = ls = fc = 0
    for f in p.rglob("*.py"):
        if str(f).startswith("venv"):
            continue
        if str(f).startswith("discord"):
            continue
        fc += 1
        with f.open() as of:
            for l in of.readlines():  # noqa: E741
                l = l.strip()  # noqa: E741
                if l.startswith("class"):
                    cl += 1
                if l.startswith("def"):
                    fn += 1
                if l.startswith("import"):
                    imp += 1
                if l.startswith("from"):
                    imp += 1
                if l.startswith("async def"):
                    cr += 1
                if "#" in l:
                    cm += 1
                ls += 1
    data = {
        "files": f"{fc:,}",
        "imports": f"{imp:,}",
        "lines": f"{ls:,}",
        "classes": f"{cl:,}",
        "functions": f"{fn:,}",
        "coroutines": f"{cr:,}",
    }
    return data


#    return Statistics(**data)


class EmbedException(Exception):
    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


class InvalidURL(Exception):
    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


class Transcribe(BaseModel):
    time_elapsed: pos[one[float, str]] = 0.0
    text: pos[str] = None


class DiscordUser(BaseModel):
    id: str
    username: str
    avatar: pos[str]
    discriminator: str
    public_flags: int
    premium_type: pos[int]
    flags: int
    banner: pos[str]
    accent_color: int
    global_name: str
    avatar_decoration_data: pos[dict]
    banner_color: str
    tag: str
    createdAt: str
    createdTimestamp: int
    public_flags_array: List[str]
    defaultAvatarURL: str
    avatarURL: pos[str]
    bannerURL: pos[str]
    bio: pos[str]
    premium_since: pos[str]
    premium_guild_since: pos[str]


class RivalAPI(object):
    def __init__(self, bot):
        self.bot = bot
        self.key = self.bot.config["rival_api"]

    async def get_session(self):
        if not hasattr(self, "session"):
            self.session = aiohttp.ClientSession()
        return self.session

    async def caption(self, ctx: Context, text: str):
        if len(ctx.message.attachments) == 0:
            if ref := ctx.message.reference:
                message = await self.bot.fetch_message(ctx.channel, ref.message_id)
                if len(message.attachments) == 0:
                    return await ctx.fail("please provide an **image**")
                else:
                    data = (await message.attachments[0].to_file()).fp.read()
                    filename = message.attachments[0].filename
                    message.attachments[0].url  # type: ignore
        else:
            data = (await ctx.message.attachments[0].to_file()).fp.read()
            filename = ctx.message.attachments[0].filename
            ctx.message.attachments[0].url  # type: ignore
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.rival.rocks/caption",
                params={"text": text},
                data={"file": data},
                headers={"api-key": self.key},
            ) as response:
                if response.status != 200:
                    return await ctx.fail("An API Error **occurred**")
                data = await response.read()
        file = discord.File(fp=io.BytesIO(data), filename=filename)
        return await ctx.send(file=file)

    async def discord_user(self, user_id: int):
        await self.get_session()
        async with self.session.get(
            "https://api.rival.rocks/user",
            params={"user_id": user_id},
            headers={"api-key": self.key},
        ) as response:
            data = await response.json()
            d = data["data"]

            for k in ("presence", "connections"):
                del d[k]

        return DiscordUser(**d)

    async def instagram_user(self, username: str):
        await self.get_session()
        async with self.session.get(
            "https://api.rival.rocks/instagram/user",
            params={"username": username},
            headers={"api-key": self.key},
        ) as response:
            data = await response.json()
            d = data["data"]["user"]
        return User(**d)

    async def generate_image(self, prompt: str) -> str:
        await self.get_session()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.rival.rocks/image/generation",
                    params={"prompt": prompt},
                    headers={"api-key": self.key},
                ) as response:
                    data = await response.json()
            return data["url"]
        except Exception:
            raise CommandError("Failed to generate image")

    async def uwuify(self, text: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.rival.rocks/uwuify",
                params={"text": text},
                headers={"api-key": self.key},
            ) as response:
                data = await response.text()
        return data

    async def google_search(
        self, query: str, safe: bool
    ) -> Optional[GoogleSearchResponse]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.rival.rocks/google/search",
                params={"query": query, "safe": "true" if safe is True else "false"},
                headers={"api-key": self.key},
            ) as response:
                data = await response.json()
        return GoogleSearchResponse(**data)

    async def girlfriend(self, ctx: Context):
        if identity := await self.bot.db.fetchval(
            """SELECT identity FROM girlfriend WHERE user_id = $1""",
            ctx.message.author.id,
        ):
            prompt = ctx.message.content
        else:
            return await ctx.fail(
                f"you have not set your girlfriend's identity using `{ctx.prefix}girlfriend identity`"
            )
        async with aiohttp.ClientSession() as session:
            async with session.request(
                "POST",
                "https://api.rival.rocks/girlfriend",
                json={"identity": identity, "message": prompt},
                headers={"api-key": self.key},
            ) as response:
                _ = await response.text()
        return await ctx.reply(content=_.replace('"', ""))

    async def youtube(self, url: str) -> Optional[YouTube]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.rival.rocks/youtube",
                params={"url": url},
                headers={"api-key": self.key},
            ) as response:
                data = await response.json()
        return YouTube(**data)

    async def instagram_media(self, url: str):
        await self.get_session()
        if "stories" in url:
            raise InvalidURL("Instagram Embedding doesn't support stories")
        async with self.session.get(
            "https://api.rival.rocks/instagram/media",
            params={"url": url},
            headers={"api-key": self.key},
        ) as response:
            try:
                data = await response.json()
            except Exception:
                raise InvalidURL("Instagram Embedding failed with an exception")
        return InstagramMedia(**data)

    async def tiktok_user(self, username: str) -> pos[TikTokUser]:
        await self.get_session()
        async with self.session.get(
            "https://api.rival.rocks/tiktok/userinfo",
            params={"username": username},
            headers={"api-key": self.key},
        ) as response:
            data = await response.json()
        data["likes"] = data.pop("hearts", 0)
        return TikTokUser(**data)

    async def get_youtube_post(self, url: str) -> pos[YouTubePost]:
        await self.get_session()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.rival.rocks/youtube",
                params={"url": url},
                headers={"api-key": self.key},
            ) as response:
                data = await response.json()
        return YouTubePost(**data)

    async def transcribe(self, message: Message):
        await self.get_session()
        if len(message.attachments) > 0:
            for attachment in message.attachments:
                if attachment.is_voice_message() is True:
                    async with self.session.get(
                        "https://api.rival.rocks/media/transcribe",
                        params={"url": attachment.url},
                        headers={"api-key": self.key},
                    ) as response:
                        data = await response.json()
                    return Transcribe(**data)

    async def ocr(self, attachments: one[array[discord.Attachment], Context]) -> str:
        await self.get_session()
        responses = []
        if isinstance(attachments, Context):
            files = [attachment.url for attachment in attachments.message.attachments]
        else:
            files = attachments
        for attachment in files:
            #            try:
            async with self.session.get(
                "https://api.rival.rocks/media/ocr",
                params={"url": attachment},
                headers={"api-key": self.key},
            ) as response:
                responses.append(await response.text())
        if len(responses) > 0:
            return responses

    async def google_images(
        self, query: str, safe_search: bool = True
    ) -> pos[ImageSearchResponse]:
        await self.get_session()
        params = {"query": query}
        if safe_search is False:
            params["safe"] = "false"
        async with self.session.request(
            "POST",
            "https://api.rival.rocks/google/image",
            params=params,
            headers={"api-key": self.key},
        ) as response:
            data = await response.json()
        shuffle(data["results"])
        return ImageSearchResponse(**data)

    async def roblox_profile(self, username: str) -> pos[Roblox]:
        await self.get_session()
        async with self.session.get(
            "https://api.rival.rocks/roblox",
            params={"username": username},
            headers={"api-key": self.key},
        ) as response:
            data = await response.json()
        return Roblox(**data)

    async def transparent(self, url: str) -> discord.File:
        await self.get_session()
        async with self.session.request(
            "GET",
            "https://api.rival.rocks/media/transparent",
            params={"url": url},
            headers={"api-key": self.key},
        ) as response:
            data = await response.read()
        return discord.File(fp=io.BytesIO(data), filename="transparent.png")

    async def embed(self, code: str, author: discord.Member = None):
        return await Builder().convert(code)
