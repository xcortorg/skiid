from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


class FanClubInfo(BaseModel):
    fan_club_id: Optional[Any] = None
    fan_club_name: Optional[Any] = None
    is_fan_club_referral_eligible: Optional[Any] = None
    fan_consideration_page_revamp_eligiblity: Optional[Any] = None
    is_fan_club_gifting_eligible: Optional[Any] = None


class FriendshipStatus(BaseModel):
    following: Optional[bool] = None
    outgoing_request: Optional[bool] = None
    is_bestie: Optional[bool] = None
    is_restricted: Optional[bool] = None
    is_feed_favorite: Optional[bool] = None


class AchievementsInfo(BaseModel):
    show_achievements: Optional[bool] = None
    num_earned_achievements: Optional[Any] = None


class AudioReattributionInfo(BaseModel):
    should_allow_restore: Optional[bool] = None


class AudioRankingInfo(BaseModel):
    best_audio_cluster_id: Optional[str] = None


class BrandedContentTagInfo(BaseModel):
    can_add_tag: Optional[bool] = None


class ContentAppreciationInfo(BaseModel):
    enabled: Optional[bool] = None
    entry_point_container: Optional[Any] = None


class MashupInfo(BaseModel):
    mashups_allowed: Optional[bool] = None
    can_toggle_mashups_allowed: Optional[bool] = None
    has_been_mashed_up: Optional[bool] = None
    formatted_mashups_count: Optional[Any] = None
    original_media: Optional[Any] = None
    privacy_filtered_mashups_media_count: Optional[Any] = None
    non_privacy_filtered_mashups_media_count: Optional[int] = None
    mashup_type: Optional[Any] = None
    is_creator_requesting_mashup: Optional[bool] = None
    has_nonmimicable_additional_audio: Optional[bool] = None


class ConsumptionInfo(BaseModel):
    is_bookmarked: Optional[bool] = None
    should_mute_audio_reason: Optional[str] = None
    is_trending_in_clips: Optional[bool] = None
    should_mute_audio_reason_type: Optional[Any] = None
    display_media_id: Optional[Any] = None


class IgArtist(BaseModel):
    pk: Optional[str] = None
    pk_id: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_private: Optional[bool] = None
    is_verified: Optional[bool] = None
    profile_pic_id: Optional[str] = None
    profile_pic_url: Optional[str] = None


class CommentInformTreatment(BaseModel):
    should_have_inform_treatment: Optional[bool] = None
    text: Optional[str] = None
    url: Optional[Any] = None
    action_type: Optional[Any] = None


class InUser(BaseModel):
    pk: Optional[int] = None
    pk_id: Optional[int] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_private: Optional[bool] = None
    is_verified: Optional[bool] = None
    profile_pic_id: Optional[str] = None
    profile_pic_url: Optional[str] = None


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
    user: Optional[InUser] = None
    is_covered: Optional[bool] = None
    is_ranked_comment: Optional[bool] = None
    media_id: Optional[str] = None
    has_liked_comment: Optional[bool] = None
    comment_like_count: Optional[int] = None
    private_reply_status: Optional[int] = None


class FirstFrame(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    url: Optional[str] = None


class SquareCrop(BaseModel):
    crop_left: Optional[float] = None
    crop_right: Optional[float] = None
    crop_top: Optional[float] = None
    crop_bottom: Optional[float] = None


class SharingFrictionInfo(BaseModel):
    should_have_sharing_friction: Optional[bool] = None
    bloks_app_url: Optional[Any] = None
    sharing_friction_payload: Optional[Any] = None


class VideoVersion(BaseModel):
    type: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    url: Optional[str] = None
    id: Optional[str] = None


class User(BaseModel):
    has_anonymous_profile_picture: Optional[bool] = None
    fan_club_info: Optional[FanClubInfo] = None
    transparency_product_enabled: Optional[bool] = None
    latest_reel_media: Optional[int] = None
    is_favorite: Optional[bool] = None
    is_unpublished: Optional[bool] = None
    pk: Optional[str] = None
    pk_id: Optional[str] = None
    strong_id__: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_private: Optional[bool] = None
    is_verified: Optional[bool] = None
    friendship_status: Optional[FriendshipStatus] = None
    profile_pic_id: Optional[str] = None
    profile_pic_url: Optional[str] = None
    account_badges: Optional[list] = None
    show_account_transparency_details: Optional[bool] = None


class AdditionalAudioInfo(BaseModel):
    additional_audio_username: Optional[Any] = None
    audio_reattribution_info: Optional[AudioReattributionInfo] = None


class OriginalSoundInfo(BaseModel):
    audio_asset_id: Optional[str] = None
    music_canonical_id: Optional[Any] = None
    progressive_download_url: Optional[str] = None
    duration_in_ms: Optional[int] = None
    dash_manifest: Optional[str] = None
    ig_artist: Optional[IgArtist] = None
    should_mute_audio: Optional[bool] = None
    hide_remixing: Optional[bool] = None
    original_media_id: Optional[str] = None
    time_created: Optional[int] = None
    original_audio_title: Optional[str] = None
    consumption_info: Optional[ConsumptionInfo] = None
    can_remix_be_shared_to_fb: Optional[bool] = None
    formatted_clips_media_count: Optional[Any] = None
    allow_creator_to_rename: Optional[bool] = None
    audio_parts: Optional[list] = None
    is_explicit: Optional[bool] = None
    original_audio_subtype: Optional[str] = None
    is_audio_automatically_attributed: Optional[bool] = None
    is_reuse_disabled: Optional[bool] = None
    is_xpost_from_fb: Optional[bool] = None
    xpost_fb_creator_info: Optional[Any] = None
    nft_info: Optional[Any] = None


class AdditionalCandidates(BaseModel):
    igtv_first_frame: Optional[FirstFrame] = None
    first_frame: Optional[FirstFrame] = None
    smart_frame: Optional[Any] = None


class MediaCroppingInfo(BaseModel):
    square_crop: Optional[SquareCrop] = None


class Caption(BaseModel):
    pk: Optional[str] = None
    user_id: Optional[str] = None
    text: Optional[str] = None
    type: Optional[int] = None
    created_at: Optional[int] = None
    created_at_utc: Optional[int] = None
    content_type: Optional[str] = None
    status: Optional[str] = None
    bit_flags: Optional[int] = None
    did_report_as_spam: Optional[bool] = None
    share_enabled: Optional[bool] = None
    user: Optional[User] = None
    is_covered: Optional[bool] = None
    is_ranked_comment: Optional[bool] = None
    media_id: Optional[str] = None
    private_reply_status: Optional[int] = None


class ClipsMetadata(BaseModel):
    music_info: Optional[Any] = None
    original_sound_info: Optional[OriginalSoundInfo] = None
    audio_type: Optional[str] = None
    music_canonical_id: Optional[str] = None
    featured_label: Optional[Any] = None
    mashup_info: Optional[MashupInfo] = None
    reusable_text_info: Optional[Any] = None
    nux_info: Optional[Any] = None
    viewer_interaction_settings: Optional[Any] = None
    branded_content_tag_info: Optional[BrandedContentTagInfo] = None
    shopping_info: Optional[Any] = None
    additional_audio_info: Optional[AdditionalAudioInfo] = None
    is_shared_to_fb: Optional[bool] = None
    breaking_content_info: Optional[Any] = None
    challenge_info: Optional[Any] = None
    reels_on_the_rise_info: Optional[Any] = None
    breaking_creator_info: Optional[Any] = None
    asset_recommendation_info: Optional[Any] = None
    contextual_highlight_info: Optional[Any] = None
    clips_creation_entry_point: Optional[str] = None
    audio_ranking_info: Optional[AudioRankingInfo] = None
    template_info: Optional[Any] = None
    is_fan_club_promo_video: Optional[bool] = None
    disable_use_in_clips_client_cache: Optional[bool] = None
    content_appreciation_info: Optional[ContentAppreciationInfo] = None
    achievements_info: Optional[AchievementsInfo] = None
    show_achievements: Optional[bool] = None
    show_tips: Optional[bool] = None
    merchandising_pill_info: Optional[Any] = None
    is_public_chat_welcome_video: Optional[bool] = None
    professional_clips_upsell_type: Optional[int] = None


class ImageVersions2(BaseModel):
    candidates: Optional[List[FirstFrame]] = None
    additional_candidates: Optional[AdditionalCandidates] = None
    smart_thumbnail_enabled: Optional[bool] = None


class In(BaseModel):
    user: Optional[InUser] = None
    position: Optional[List[float]] = None
    start_time_in_video_in_sec: Optional[Any] = None
    duration_in_video_in_sec: Optional[Any] = None


class Usertags(BaseModel):
    in_: Optional[List[In]] = None


class CarouselMedia(BaseModel):
    id: Optional[str] = None
    media_type: Optional[int] = None
    product_type: Optional[str] = None
    image_versions2: Optional[ImageVersions2] = None
    video_versions: Optional[List[VideoVersion]] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None
    accessibility_caption: Optional[str] = None
    pk: Optional[str] = None
    carousel_parent_id: Optional[str] = None
    usertags: Optional[Usertags] = None
    commerciality_status: Optional[str] = None
    sharing_friction_info: Optional[SharingFrictionInfo] = None


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
    should_request_ads: Optional[bool] = None
    original_media_has_visual_reply_media: Optional[bool] = None
    like_and_view_counts_disabled: Optional[bool] = None
    commerciality_status: Optional[str] = None
    is_paid_partnership: Optional[bool] = None
    is_visual_reply_commenter_notice_enabled: Optional[bool] = None
    clips_tab_pinned_user_ids: Optional[list] = None
    has_delayed_metadata: Optional[bool] = None
    comment_likes_enabled: Optional[bool] = None
    comment_threading_enabled: Optional[bool] = None
    max_num_visible_preview_comments: Optional[int] = None
    has_more_comments: Optional[bool] = None
    preview_comments: Optional[list] = None
    comments: Optional[list] = None
    next_max_id: Optional[str] = None

    comment_count: Optional[int] = None
    can_view_more_preview_comments: Optional[bool] = None
    hide_view_all_comment_entrypoint: Optional[bool] = None
    inline_composer_display_condition: Optional[str] = None
    carousel_media_count: Optional[int] = None
    carousel_media: Optional[List[CarouselMedia]] = None
    can_see_insights_as_brand: Optional[bool] = None
    photo_of_you: Optional[bool] = None
    is_organic_product_tagging_eligible: Optional[bool] = None
    user: Optional[User] = None
    can_viewer_reshare: Optional[bool] = None
    like_count: Optional[int] = None
    fb_like_count: Optional[int] = None
    has_liked: Optional[bool] = None
    top_likers: Optional[list] = None
    facepile_top_likers: Optional[list] = None
    is_comments_gif_composer_enabled: Optional[bool] = None
    image_versions2: Optional[ImageVersions2] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None
    video_subtitles_confidence: Optional[float] = None
    video_subtitles_uri: Optional[str] = None
    caption: Optional[Caption] = None
    caption_is_edited: Optional[bool] = None
    comment_inform_treatment: Optional[CommentInformTreatment] = None
    sharing_friction_info: Optional[SharingFrictionInfo] = None
    is_dash_eligible: Optional[int] = None
    video_dash_manifest: Optional[str] = None
    video_codec: Optional[str] = None
    number_of_qualities: Optional[int] = None
    video_versions: Optional[List[VideoVersion]] = None
    has_audio: Optional[bool] = None
    video_duration: Optional[float] = None
    can_viewer_save: Optional[bool] = None
    is_in_profile_grid: Optional[bool] = None
    profile_grid_control_enabled: Optional[bool] = None
    play_count: Optional[int] = None
    fb_play_count: Optional[int] = None
    organic_tracking_token: Optional[str] = None
    third_party_downloads_enabled: Optional[bool] = None
    has_shared_to_fb: Optional[int] = None
    product_type: Optional[str] = None
    show_shop_entrypoint: Optional[bool] = None
    deleted_reason: Optional[int] = None
    integrity_review_decision: Optional[str] = None
    commerce_integrity_review_decision: Optional[Any] = None
    music_metadata: Optional[Any] = None
    is_artist_pick: Optional[bool] = None
    ig_media_sharing_disabled: Optional[bool] = None
    clips_metadata: Optional[ClipsMetadata] = None
    media_cropping_info: Optional[MediaCroppingInfo] = None


class InstagramPostModelRaw(BaseModel):
    items: Optional[List[Item]] = None
    num_results: Optional[int] = None
    more_available: Optional[bool] = None
    auto_load_more_enabled: Optional[bool] = None
    status: Optional[str] = None
