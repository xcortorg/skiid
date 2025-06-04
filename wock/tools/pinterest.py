import asyncio
import os
import re
import subprocess
import typing
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Annotated, Any  # type: ignore
from typing import AnyStr as AnyUrl
from typing import Dict, List, Optional  # type: ignore

import aiofiles
import requests
# yes
import tuuid
from aiohttp import ClientSession as Session
from anyio import Path as AsyncPath
from discord.ext.commands import CommandError
from loguru import logger
from orjson import dumps  # type: ignore
from pydantic import BaseModel, Field


class PinterestProfileResponse(BaseModel):
    username: Optional[str] = None
    description: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    pins: Optional[int] = None
    url: Optional[str] = None
    avatar_url: Optional[str] = None


class ActiveExperiments(BaseModel):
    pass


class AnalysisUa(BaseModel):
    pass


class User(BaseModel):
    verified_identity: Optional[ActiveExperiments] = None
    image_small_url: Optional[str] = None
    last_name: Optional[str] = None
    verified_user_websites: Optional[List] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    can_enable_mfa: Optional[bool] = None
    has_password: Optional[bool] = None
    image_xlarge_url: Optional[str] = None
    image_medium_url: Optional[str] = None
    twitter_publish_enabled: Optional[bool] = None
    connected_to_etsy: Optional[bool] = None
    is_partner: Optional[bool] = None
    allow_personalization_cookies: Optional[Any] = None
    phone_country: Optional[Any] = None
    facebook_timeline_enabled: Optional[bool] = None
    connected_to_microsoft: Optional[bool] = None
    personalize_from_offsite_browsing: Optional[bool] = None
    nags: Optional[List] = None
    is_any_website_verified: Optional[bool] = None
    is_candidate_for_parental_control_passcode: Optional[bool] = None
    is_parental_control_passcode_enabled: Optional[bool] = None
    phone_number: Optional[Any] = None
    should_show_messaging: Optional[bool] = None
    username: Optional[str] = None
    ip_country: Optional[str] = None
    unverified_phone_country: Optional[Any] = None
    twitter_url: Optional[Any] = None
    website_url: Optional[Any] = None
    connected_to_google: Optional[bool] = None
    ip_region: Optional[str] = None
    allow_marketing_cookies: Optional[Any] = None
    push_package_user_id: Optional[str] = None
    phone_number_end: Optional[str] = None
    is_matured_new_user: Optional[bool] = None
    is_under_16: Optional[bool] = None
    unverified_phone_number_without_country: Optional[str] = None
    created_at: Optional[str] = None
    connected_to_dropbox: Optional[bool] = None
    is_high_risk: Optional[bool] = None
    resurrection_info: Optional[Any] = None
    third_party_marketing_tracking_enabled: Optional[bool] = None
    domain_verified: Optional[bool] = None
    facebook_publish_stream_enabled: Optional[bool] = None
    connected_to_instagram: Optional[bool] = None
    is_private_profile: Optional[bool] = None
    profile_discovered_public: Optional[Any] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    Listed_website_url: Optional[Any] = None
    connected_to_facebook: Optional[bool] = None
    connected_to_youtube: Optional[bool] = None
    age_in_years: Optional[int] = None
    is_ads_only_profile: Optional[bool] = None
    epik: Optional[str] = None
    first_name: Optional[str] = None
    ads_only_profile_site: Optional[Any] = None
    unverified_phone_number: Optional[Any] = None
    parental_control_anonymized_email: Optional[Any] = None
    domain_url: Optional[Any] = None
    type: Optional[str] = None
    allow_analytic_cookies: Optional[Any] = None
    is_employee: Optional[bool] = None
    is_any_website_verified: Optional[bool] = None
    is_candidate_for_parental_control_passcode: Optional[bool] = None
    is_parental_control_passcode_enabled: Optional[bool] = None
    phone_number: Optional[Any] = None
    should_show_messaging: Optional[bool] = None
    username: Optional[str] = None
    ip_country: Optional[str] = None
    unverified_phone_country: Optional[Any] = None
    twitter_url: Optional[Any] = None
    website_url: Optional[Any] = None
    connected_to_google: Optional[bool] = None
    ip_region: Optional[str] = None
    allow_marketing_cookies: Optional[Any] = None
    push_package_user_id: Optional[str] = None
    phone_number_end: Optional[str] = None
    is_matured_new_user: Optional[bool] = None
    is_under_16: Optional[bool] = None
    unverified_phone_number_without_country: Optional[str] = None
    created_at: Optional[str] = None
    connected_to_dropbox: Optional[bool] = None
    is_high_risk: Optional[bool] = None
    resurrection_info: Optional[Any] = None
    third_party_marketing_tracking_enabled: Optional[bool] = None
    domain_verified: Optional[bool] = None
    facebook_publish_stream_enabled: Optional[bool] = None
    connected_to_instagram: Optional[bool] = None
    is_private_profile: Optional[bool] = None
    profile_discovered_public: Optional[Any] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    Listed_website_url: Optional[Any] = None
    connected_to_facebook: Optional[bool] = None
    connected_to_youtube: Optional[bool] = None
    age_in_years: Optional[int] = None
    is_ads_only_profile: Optional[bool] = None
    epik: Optional[str] = None
    first_name: Optional[str] = None
    ads_only_profile_site: Optional[Any] = None
    unverified_phone_number: Optional[Any] = None
    parental_control_anonymized_email: Optional[Any] = None
    domain_url: Optional[Any] = None
    type: Optional[str] = None
    allow_analytic_cookies: Optional[Any] = None
    is_employee: Optional[bool] = None


class AggregateRating:
    id: Optional[str]
    name: Optional[Any]
    rating_distribution: Optional[List]
    rating_value: Optional[str]
    type: Optional[str]


class AggregatedStats:
    done: Optional[int]
    saves: Optional[int]


class Options:
    bookmarks: Optional[List[str]]
    username: Optional[str]
    field_set_key: Optional[str]


class EligibleProfileTab:
    id: Optional[str]
    type: Optional[str]
    tab_type: Optional[int]
    name: Optional[str]
    is_default: Optional[bool]


class ProfileCover:
    id: Optional[str]


class RepinsFrom:
    repins_from: Optional[List]
    image_medium_url: Optional[str]
    username: Optional[str]
    full_name: Optional[str]
    id: Optional[str]
    image_small_url: Optional[str]


class User:  # noqa: F811
    verified_identity: Optional[Any]
    image_small_url: Optional[str]
    last_name: Optional[str]
    verified_user_websites: Optional[List]
    gender: Optional[str]
    country: Optional[str]
    can_enable_mfa: Optional[bool]
    has_password: Optional[bool]
    image_xlarge_url: Optional[str]
    image_medium_url: Optional[str]
    twitter_publish_enabled: Optional[bool]
    connected_to_etsy: Optional[bool]
    is_partner: Optional[bool]
    allow_personalization_cookies: Optional[Any]
    phone_country: Optional[Any]
    facebook_timeline_enabled: Optional[bool]
    connected_to_microsoft: Optional[bool]
    personalize_from_offsite_browsing: Optional[bool]
    nags: Optional[List]
    is_any_website_verified: Optional[bool]
    is_candidate_for_parental_control_passcode: Optional[bool]
    is_parental_control_passcode_enabled: Optional[bool]
    phone_number: Optional[Any]
    should_show_messaging: Optional[bool]
    username: Optional[str]
    ip_country: Optional[str]
    unverified_phone_country: Optional[Any]
    twitter_url: Optional[Any]
    website_url: Optional[Any]
    connected_to_google: Optional[bool]
    ip_region: Optional[str]
    allow_marketing_cookies: Optional[Any]
    push_package_user_id: Optional[str]
    phone_number_end: Optional[str]
    is_matured_new_user: Optional[bool]
    is_under_16: Optional[bool]
    unverified_phone_number_without_country: Optional[str]
    created_at: Optional[str]
    connected_to_dropbox: Optional[bool]
    is_high_risk: Optional[bool]
    resurrection_info: Optional[Any]
    third_party_marketing_tracking_enabled: Optional[bool]
    domain_verified: Optional[bool]
    facebook_publish_stream_enabled: Optional[bool]
    connected_to_instagram: Optional[bool]
    is_private_profile: Optional[bool]
    profile_discovered_public: Optional[Any]
    email: Optional[str]
    full_name: Optional[str]
    Listed_website_url: Optional[Any]
    connected_to_facebook: Optional[bool]
    connected_to_youtube: Optional[bool]
    age_in_years: Optional[int]
    is_ads_only_profile: Optional[bool]
    epik: Optional[str]
    first_name: Optional[str]
    ads_only_profile_site: Optional[Any]
    unverified_phone_number: Optional[Any]
    parental_control_anonymized_email: Optional[Any]
    domain_url: Optional[Any]
    type: Optional[str]
    allow_analytic_cookies: Optional[Any]
    is_employee: Optional[bool]
    is_write_banned: Optional[bool]
    gplus_url: Optional[str]
    id: Optional[str]
    login_state: Optional[int]
    image_large_url: Optional[str]
    verified_domains: Optional[List]
    facebook_id: Optional[str]
    has_mfa_enabled: Optional[bool]
    custom_gender: Optional[Any]


class ClientContext:
    active_experiments: Optional[Any]
    analysis_ua: Optional[Any]
    app_type_detailed: Optional[int]
    app_version: Optional[str]
    batch_exp: Optional[bool]
    browser_locale: Optional[str]
    browser_name: Optional[str]
    browser_type: Optional[int]
    browser_version: Optional[str]
    country: Optional[str]
    country_from_hostname: Optional[str]
    country_from_ip: Optional[str]
    csp_nonce: Optional[str]
    current_url: Optional[str]
    debug: Optional[bool]
    deep_link: Optional[str]
    enabled_advertiser_countries: Optional[List[str]]
    experiment_hash: Optional[str]
    facebook_token: Optional[Any]
    full_path: Optional[str]
    http_referrer: Optional[str]
    impersonator_user_id: Optional[Any]
    invite_code: Optional[str]
    invite_sender_id: Optional[str]
    is_authenticated: Optional[bool]
    is_bot: Optional[str]
    is_internal_ip: Optional[bool]
    is_full_page: Optional[bool]
    is_managed_advertiser: Optional[bool]
    is_mobile_agent: Optional[bool]
    is_shop_the_pin_campaign_whiteListed: Optional[bool]
    is_sterling_on_steroids: Optional[bool]
    is_tablet_agent: Optional[bool]
    language: Optional[str]
    locale: Optional[str]
    origin: Optional[str]
    path: Optional[str]
    placed_experiences: Optional[Any]
    referrer: Optional[Any]
    region_from_ip: Optional[str]
    request_host: Optional[str]
    request_identifier: Optional[str]
    social_bot: Optional[str]
    stage: Optional[str]
    sterling_on_steroids_ldap: Optional[Any]
    sterling_on_steroids_user_type: Optional[Any]
    triggerable_experiments: Optional[dict[str, str]]
    unauth_id: Optional[str]
    seo_debug: Optional[bool]
    user_agent_can_use_native_app: Optional[bool]
    user_agent_platform: Optional[str]
    user_agent_platform_version: Optional[Any]
    user_agent: Optional[str]
    user: Optional[User]
    utm_campaign: Optional[Any]
    visible_url: Optional[str]


class Resource:
    name: Optional[str]
    options: Optional[Options]


class Data:
    blocked_by_me: Optional[bool]
    board_count: Optional[int]
    is_tastemaker: Optional[bool]
    native_pin_count: Optional[int]
    storefront_search_enabled: Optional[bool]
    explicitly_followed_by_me: Optional[bool]
    pins_done_count: Optional[int]
    show_creator_profile: Optional[bool]
    show_engagement_tab: Optional[bool]
    Listed_website_url: Optional[str]
    pronouns: Optional[List]
    has_showcase: Optional[bool]
    story_pin_count: Optional[int]
    is_ads_only_profile: Optional[bool]
    should_show_messaging: Optional[bool]
    is_partner: Optional[bool]
    profile_reach: Optional[int]
    group_board_count: Optional[int]
    profile_cover: Optional[ProfileCover]
    website_url: Optional[str]
    is_inspirational_merchant: Optional[bool]
    profile_discovered_public: Optional[Any]
    image_small_url: Optional[str]
    interest_following_count: Optional[int]
    show_impressum: Optional[bool]
    full_name: Optional[str]
    video_pin_count: Optional[int]
    has_published_pins: Optional[bool]
    is_verified_merchant: Optional[bool]
    last_pin_save_time: Optional[str]
    has_catalog: Optional[bool]
    impressum_url: Optional[Any]
    username: Optional[str]
    eligible_profile_tabs: Optional[List[EligibleProfileTab]]
    profile_views: Optional[int]
    ads_only_profile_site: Optional[Any]
    storefront_management_enabled: Optional[bool]
    has_shopping_showcase: Optional[bool]
    following_count: Optional[int]
    image_medium_url: Optional[str]
    show_discovered_feed: Optional[Any]
    explicit_user_following_count: Optional[int]
    partner: Optional[Any]
    first_name: Optional[str]
    about: Optional[str]
    indexed: Optional[bool]
    follower_count: Optional[int]
    has_custom_board_sorting_order: Optional[bool]
    joined_communities_count: Optional[int]
    last_name: Optional[str]
    pin_count: Optional[int]
    type: Optional[str]
    image_large_url: Optional[str]
    is_primary_website_verified: Optional[bool]
    image_xlarge_url: Optional[str]
    verified_identity: Optional[Any]
    domain_url: Optional[Any]
    id: Optional[str]
    should_default_comments_off: Optional[bool]
    domain_verified: Optional[bool]
    repins_from: Optional[List[RepinsFrom]]
    has_board: Optional[bool]


class AggregateRating(BaseModel):  # noqa: F811
    id: Optional[str]
    name: Optional[Any]
    rating_distribution: Optional[List]
    rating_value: Optional[str]
    type: Optional[str]


class AggregatedStats(BaseModel):  # noqa: F811
    done: Optional[int]
    saves: Optional[int]


class AnalysisUa(BaseModel):  # noqa: F811
    app_type: Optional[int]
    browser_name: Optional[str]
    browser_version: Optional[str]
    device: Optional[str]
    device_type: Optional[Any]
    os_name: Optional[str]
    os_version: Optional[str]


class FaviconImages(BaseModel):
    orig: Optional[AnyUrl]


class Image(BaseModel):
    height: Optional[int]
    url: Optional[AnyUrl]
    width: Optional[int]


class OfferSummary(BaseModel):
    availability: Optional[int]
    currency: Optional[str]
    in_stock: Optional[bool]
    price: Optional[str]
    price_val: Optional[float]


class Options(BaseModel):
    bookmarks: Optional[List[str]]
    field_set_key: Optional[str]
    id: Optional[str]


class RecommendScore(BaseModel):
    count: Optional[int]
    score: Optional[float]


class Resource(BaseModel):  # noqa: F811
    name: Optional[str]
    options: Optional[Options]


class VerifiedIdentity(BaseModel):
    pass


class Field736X(BaseModel):
    canonical_image: Optional[Image]
    image_signature: Optional[str]


class AdditionalImagesPerSpec(BaseModel):
    field_736x: Annotated[Optional[List[Field736X]], Field(alias="736x")]


class CanonicalImages(BaseModel):
    field_736x: Annotated[Optional[Image], Field(alias="736x")]


class CloseupAttribution(BaseModel):
    ads_only_profile_site: Optional[Any]
    blocked_by_me: Optional[bool]
    domain_url: Optional[str]
    domain_verified: Optional[bool]
    explicitly_followed_by_me: Optional[bool]
    first_name: Optional[str]
    followed_by_me: Optional[bool]
    follower_count: Optional[int]
    full_name: Optional[str]
    id: Optional[str]
    image_medium_url: Optional[AnyUrl]
    image_small_url: Optional[AnyUrl]
    indexed: Optional[bool]
    is_ads_only_profile: Optional[bool]
    is_default_image: Optional[bool]
    is_verified_merchant: Optional[bool]
    type: Optional[str]
    username: Optional[str]
    verified_identity: Optional[VerifiedIdentity]


class DidItData(BaseModel):
    details_count: Optional[int]
    images_count: Optional[int]
    rating: Optional[int]
    recommend_scores: Optional[List[RecommendScore]]
    recommended_count: Optional[int]
    responses_count: Optional[int]
    tags: Optional[List]
    type: Optional[str]
    user_count: Optional[int]
    videos_count: Optional[int]


class LinkDomain(BaseModel):
    official_user: Optional[CloseupAttribution]


class User(BaseModel):
    ads_only_profile_site: Optional[Any]
    age_in_years: Optional[int]
    allow_analytic_cookies: Optional[Any]
    allow_marketing_cookies: Optional[Any]
    allow_personalization_cookies: Optional[Any]
    can_enable_mfa: Optional[bool]
    connected_to_dropbox: Optional[bool]
    connected_to_etsy: Optional[bool]
    connected_to_facebook: Optional[bool]
    connected_to_google: Optional[bool]
    connected_to_instagram: Optional[bool]
    connected_to_microsoft: Optional[bool]
    connected_to_youtube: Optional[bool]
    country: Optional[str]
    created_at: Optional[str]
    custom_gender: Optional[Any]
    domain_url: Optional[Any]
    domain_verified: Optional[bool]
    email: Optional[str]
    epik: Optional[str]
    facebook_id: Optional[str]
    facebook_publish_stream_enabled: Optional[bool]
    facebook_timeline_enabled: Optional[bool]
    first_name: Optional[str]
    full_name: Optional[str]
    gender: Optional[str]
    gplus_url: Optional[AnyUrl]
    has_mfa_enabled: Optional[bool]
    has_password: Optional[bool]
    has_quicksave_board: Optional[bool]
    id: Optional[str]
    image_large_url: Optional[AnyUrl]
    image_medium_url: Optional[AnyUrl]
    image_small_url: Optional[AnyUrl]
    image_xlarge_url: Optional[AnyUrl]
    ip_country: Optional[str]
    ip_region: Optional[str]
    is_ads_only_profile: Optional[bool]
    is_any_website_verified: Optional[bool]
    is_candidate_for_parental_control_passcode: Optional[bool]
    is_eligible_for_image_only_grid: Optional[bool]
    is_employee: Optional[bool]
    is_high_risk: Optional[bool]
    is_matured_new_user: Optional[bool]
    is_parental_control_passcode_enabled: Optional[bool]
    is_partner: Optional[bool]
    is_private_profile: Optional[bool]
    is_under_16: Optional[bool]
    is_under_18: Optional[bool]
    is_write_banned: Optional[bool]
    last_name: Optional[str]
    Listed_website_url: Optional[Any]
    login_state: Optional[int]
    nags: Optional[List]
    parental_control_anonymized_email: Optional[Any]
    partner: Optional[Any]
    personalize_from_offsite_browsing: Optional[bool]
    phone_country: Optional[Any]
    phone_number: Optional[Any]
    phone_number_end: Optional[str]
    profile_discovered_public: Optional[Any]
    push_package_user_id: Optional[str]
    resurrection_info: Optional[Any]
    should_show_messaging: Optional[bool]
    show_personal_boutique: Optional[bool]
    third_party_marketing_tracking_enabled: Optional[bool]
    twitter_publish_enabled: Optional[bool]
    twitter_url: Optional[Any]
    type: Optional[str]
    unverified_phone_country: Optional[Any]
    unverified_phone_number: Optional[Any]
    unverified_phone_number_without_country: Optional[str]
    username: Optional[str]
    verified_domains: Optional[List]
    verified_identity: Optional[VerifiedIdentity]
    verified_user_websites: Optional[List]
    website_url: Optional[Any]


class AdditionalImage(BaseModel):
    canonical_images: Optional[CanonicalImages]
    image_signature: Optional[str]


class AggregatedPinData(BaseModel):
    aggregated_stats: Optional[AggregatedStats]
    comment_count: Optional[int]
    did_it_data: Optional[DidItData]
    id: Optional[str]
    is_shop_the_look: Optional[bool]


class Board(BaseModel):
    access: Optional[List]
    category: Optional[Any]
    collaborated_by_me: Optional[bool]
    description: Optional[str]
    followed_by_me: Optional[bool]
    id: Optional[str]
    image_cover_url: Optional[AnyUrl]
    image_thumbnail_url: Optional[AnyUrl]
    is_collaborative: Optional[bool]
    layout: Optional[str]
    map_id: Optional[str]
    name: Optional[str]
    owner: Optional[CloseupAttribution]
    pin_thumbnail_urls: Optional[List[AnyUrl]]
    privacy: Optional[str]
    type: Optional[str]
    url: Optional[str]


class ClientContext(BaseModel):  # noqa: F811
    analysis_ua: Optional[AnalysisUa]
    app_type_detailed: Optional[int]
    app_version: Optional[str]
    batch_exp: Optional[bool]
    browser_locale: Optional[str]
    browser_name: Optional[str]
    browser_type: Optional[int]
    browser_version: Optional[str]
    country: Optional[str]
    country_from_hostname: Optional[str]
    country_from_ip: Optional[str]
    csp_nonce: Optional[str]
    current_url: Optional[str]
    debug: Optional[bool]
    deep_link: Optional[str]
    enabled_advertiser_countries: Optional[List[str]]
    facebook_token: Optional[Any]
    full_path: Optional[str]
    http_referrer: Optional[str]
    impersonator_user_id: Optional[Any]
    invite_code: Optional[str]
    invite_sender_id: Optional[str]
    is_authenticated: Optional[bool]
    is_bot: Optional[str]
    is_full_page: Optional[bool]
    is_internal_ip: Optional[bool]
    is_managed_advertiser: Optional[bool]
    is_mobile_agent: Optional[bool]
    is_shop_the_pin_campaign_whiteListed: Optional[bool]
    is_sterling_on_steroids: Optional[bool]
    is_tablet_agent: Optional[bool]
    language: Optional[str]
    locale: Optional[str]
    origin: Optional[AnyUrl]
    path: Optional[str]
    placed_experiences: Optional[Any]
    referrer: Optional[Any]
    region_from_ip: Optional[str]
    request_host: Optional[str]
    request_identifier: Optional[str]
    seo_debug: Optional[bool]
    social_bot: Optional[str]
    stage: Optional[str]
    sterling_on_steroids_ldap: Optional[Any]
    sterling_on_steroids_user_type: Optional[Any]
    unauth_id: Optional[str]
    user: Optional[User]
    user_agent: Optional[str]
    user_agent_can_use_native_app: Optional[bool]
    user_agent_platform: Optional[str]
    user_agent_platform_version: Optional[Any]
    utm_campaign: Optional[Any]
    visible_url: Optional[str]


class Product(BaseModel):
    additional_images: Optional[List[AdditionalImage]]
    additional_images_per_spec: Optional[AdditionalImagesPerSpec]
    has_multi_images: Optional[bool]
    id: Optional[str]
    item_id: Optional[str]
    item_set_id: Optional[str]
    label_info: Optional[VerifiedIdentity]
    name: Optional[str]
    offer_summary: Optional[OfferSummary]
    offers: Optional[List]
    purchase_url: Optional[Any]
    shipping_info: Optional[VerifiedIdentity]
    type: Optional[str]
    variant_set: Optional[Any]
    videos: Optional[List]


class RichMetadata(BaseModel):
    aggregate_rating: Optional[AggregateRating]
    amp_url: Optional[str]
    amp_valid: Optional[bool]
    apple_touch_icon_images: Optional[Any]
    apple_touch_icon_link: Optional[Any]
    canonical_url: Optional[Any]
    description: Optional[str]
    favicon_images: Optional[FaviconImages]
    favicon_link: Optional[AnyUrl]
    has_price_drop: Optional[bool]
    id: Optional[str]
    link_status: Optional[int]
    locale: Optional[str]
    products: Optional[List[Product]]
    site_name: Optional[str]
    title: Optional[str]
    tracker: Optional[Any]
    type: Optional[str]
    url: Optional[AnyUrl]


class Data(BaseModel):  # noqa: F811
    access: Optional[List]
    images: Optional[Dict[str, Image]]
    videos: Optional[Any]

    aggregated_pin_data: Optional[AggregatedPinData]
    alt_text: Optional[Any]
    attribution: Optional[Any]
    auto_alt_text: Optional[Any]
    board: Optional[Board]
    buyable_product_availability: Optional[Any]
    can_delete_did_it_and_comments: Optional[bool]
    carousel_data: Optional[Any]
    category: Optional[str]
    closeup_attribution: Optional[CloseupAttribution]
    closeup_description: Optional[str]
    closeup_unified_description: Optional[str]
    closeup_user_note: Optional[str]
    comment_count: Optional[int]
    comments_disabled: Optional[bool]
    content_sensitivity: Optional[VerifiedIdentity]
    created_at: Optional[str]
    creator_class: Optional[Any]
    creator_class_instance: Optional[Any]
    description: Optional[str]
    description_html: Optional[str]
    did_it_disabled: Optional[bool]
    domain: Optional[str]
    dominant_color: Optional[str]
    embed: Optional[Any]
    grid_title: Optional[str]
    hashtags: Optional[List]
    id: Optional[str]
    image_medium_url: Optional[AnyUrl]
    image_signature: Optional[str]
    is_eligible_for_aggregated_comments: Optional[bool]
    is_eligible_for_brand_catalog: Optional[bool]
    is_eligible_for_pdp: Optional[bool]
    is_hidden: Optional[bool]
    is_native: Optional[bool]
    is_oos_product: Optional[bool]
    is_playable: Optional[bool]
    is_promotable: Optional[bool]
    is_promoted: Optional[bool]
    is_quick_promotable: Optional[bool]
    is_quick_promotable_by_pinner: Optional[bool]
    is_repin: Optional[bool]
    is_stale_product: Optional[bool]
    is_video: Optional[bool]
    is_whiteListed_for_tried_it: Optional[bool]
    link: Optional[AnyUrl]
    link_domain: Optional[LinkDomain]
    method: Optional[str]
    mobile_link: Optional[Any]
    music_attributions: Optional[List]
    native_creator: Optional[CloseupAttribution]
    origin_pinner: Optional[Any]
    pinned_to_board: Optional[Any]
    pinner: Optional[CloseupAttribution]
    price_currency: Optional[str]
    price_value: Optional[int]
    privacy: Optional[str]
    product_pin_data: Optional[Any]
    promoted_is_removable: Optional[bool]
    promoter: Optional[Any]
    reaction_counts: Optional[VerifiedIdentity]
    repin_count: Optional[int]
    rich_metadata: Optional[RichMetadata]
    section: Optional[Any]
    seo_url: Optional[str]
    share_count: Optional[int]
    shopping_flags: Optional[List[int]]
    shopping_rec_disabled: Optional[bool]
    should_mute: Optional[Any]
    should_open_in_stream: Optional[bool]
    should_redirect_id_only_url_to_text_url: Optional[bool]
    sponsorship: Optional[Any]
    story_pin_data: Optional[Any]
    story_pin_data_id: Optional[Any]
    third_party_pin_owner: Optional[Any]
    title: Optional[str]
    tracked_link: Optional[AnyUrl]
    tracking_params: Optional[str]
    type: Optional[str]
    via_pinner: Optional[Any]


class ResourceResponse(BaseModel):
    message: Optional[str]
    status: Optional[str]
    code: Optional[int]
    data: Optional[Data]
    endpoint_name: Optional[str]
    http_status: Optional[int]

    x_pinterest_sli_endpoint_name: Optional[str]


class PinterestResponseModel(BaseModel):
    resource_response: Optional[ResourceResponse]
    client_context: Optional[ClientContext]
    request_identifier: Optional[str]
    resource: Optional[Resource]


class ResourceResponse(BaseModel):
    status: Optional[str] = None
    code: Optional[int] = None
    message: Optional[str] = None
    endpoint_name: Optional[str] = None
    data: Optional[Data] = None
    x_pinterest_sli_endpoint_name: Optional[str] = None
    http_status: Optional[int] = None


class PinterestUserinfoAPIResponse(BaseModel):
    resource_response: Optional[ResourceResponse] = None
    client_context: Optional[ClientContext] = None
    resource: Optional[Resource] = None
    request_identifier: Optional[str] = None


POST_RE = re.compile(
    r"(?x) https?://(?:[^/]+\.)?pinterest\.(?: com|fr|de|ch|jp|cl|ca|it|co\.uk|nz|ru|com\.au|at|pt|co\.kr|es|com\.mx|"
    r" dk|ph|th|com\.uy|co|nl|info|kr|ie|vn|com\.vn|ec|mx|in|pe|co\.at|hu|"
    r" co\.in|co\.nz|id|com\.ec|com\.py|tw|be|uk|com\.bo|com\.pe)/pin/(?P<id>\d+)",
)

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36",
}


@asynccontextmanager
async def borrow_temp_file(
    base="/root", extension=None
) -> typing.Generator[AsyncPath, None, None]:  # type: ignore
    if not extension:
        extension = ""
    file = AsyncPath(f"{base}/{tuuid.tuuid()}{extension}")
    try:
        yield file
    finally:
        await file.unlink(missing_ok=True)


class Pinterest:
    def __init__(self, proxies: Optional[List[str]] = None):
        self.proxies = proxies
        self.locks = defaultdict(asyncio.Lock)

    async def get_post_or_pin(self, url: str):
        if "pin.it" in url.lower():
            async with Session() as session:
                async with session.get(url, headers=headers) as f:
                    #                    logger.info(f.url)
                    url = str(f.url)
        if "url_shortener" in url:
            raise CommandError("Pin was **DELETED**")
        ident = POST_RE.match(url).group("id")
        async with Session() as session:
            opt = {
                "options": {
                    "field_set_key": "unauth_react_main_pin",
                    "id": f"{ident}",
                },
            }
            param = {"data": dumps(opt).decode()}
            async with session.get(
                "https://www.pinterest.com/resource/PinResource/get/",
                headers=headers,
                params=param,
            ) as request:
                return await request.json()

    async def get_user(self, username: str):
        headers = {
            "authority": "www.pinterest.com",
            "accept": "application/json, text/javascript, */*, q=0.01",
            "accept-language": "en-US,en;q=0.6",
            "dnt": "1",
            "referer": "https://www.pinterest.com/",
            "sec-ch-ua": '"Brave";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
            "x-pinterest-appstate": "active",
            "x-pinterest-pws-handler": "www/[username].js",
            "x-pinterest-source-url": f"/{username}/",
            "x-requested-with": "XMLHttpRequest",
        }

        params = {
            "source_url": f"/{username}/",
            "data": '{"options":{"username":"USERNAME","field_set_key":"profile"},"context":{}}'.replace(
                "USERNAME", username
            ),
        }
        async with Session() as session:
            async with session.get(
                "https://www.pinterest.com/resource/UserResource/get/",
                params=params,
                headers=headers,
            ) as request:
                from tools.pinmodels import Model  # type: ignore

                return Model(**await request.json())

    async def reverse_search(self, url: str):
        return await self.do_reverse_search(url)

    async def do_reverse_search(self, url: str):
        input_file = await self.do_download(url)

        def do_iter(input_file: str, url: str):
            extension = url.split(".")[-1]
            outfile = f"/root/{tuuid.tuuid()}.{extension}"
            cmd_call = ["/usr/bin/ffmpeg", "-i", str(input_file), str(outfile)]
            subprocess.check_output(cmd_call, timeout=10)
            return outfile

        outfile = await asyncio.to_thread(do_iter, input_file, url)

        os.remove(input_file)
        cookies = {
            "_b": '"AXIt4oa8ISFG2rFVwRUb5OWPtrIlGn67w77AocdE5cnngaZdDtLezPB85wcdVcAjsJE="',
            "_pinterest_ct": '"TWc9PSZZRmQ5akJOYzhYSjRzU0ZKSXIwa3p0RFRVQU9TekhrL0JiNkdhQ1pXWTJDQ3pxNHQ4WEgvVHNZcklPQUN2ZlRrMnJwT0Q2Wk94bU1FT3JOYVlQNDBjV0hLRXBXT0gxU2s0REFZcnpmQnpsND0mZzR4L242SDRHdnBDczRidjRFRmVQMUlvZXpNPQ=="',
            "_ir": "0",
        }

        headers = {
            "Host": "api.pinterest.com",
            "Connection": "keep-alive",
            "Accept": "application/json",
            "X-Pinterest-Device": "iPhone12,5",
            "Authorization": "Bearer MTQzMTU5NDo5MzEzMzA1MzUzNDk5NTE5NDk6OTIyMzM3MjAzNjg1NDc3NTgwNzoxfDE2OTU5NTc5Mzc6MC0tN2M4M2IzNGI3MzdjNDg0YmM2ZjZhZjM3ZTFmODlmMWM=",
            "X-B3-TraceId": "7f221854c2f2ccbc",
            "X-B3-SpanId": "ddb7e71c2f6a85a7",
            "X-Pinterest-InstallId": "27a13092970944abba54c3634175564e",
            "Accept-Language": "en-US",
            "X-Pinterest-AppState": "active",
            "X-Pinterest-App-Type-Detailed": "1",
            "User-Agent": "Pinterest for iOS/11.34.1 (iPhone12,5; 16.6.1)",
            "X-B3-ParentSpanId": "10871d6bf6d66b21",
        }

        files = {
            "x": (None, "0"),
            "fields": (
                None,
                "pin.{is_downstream_promotion,is_whiteListed_for_tried_it,description,comments_disabled,created_at,is_stale_product,is_video,promoted_is_max_video,link,id,pinner(),reaction_counts,top_interest,promoted_quiz_pin_data,domain_tracking_params,board(),promoter(),ad_data(),is_premiere,image_signature,auto_alt_text,story_pin_data(),ad_destination_url,is_promoted,sponsorship,image_square_url,native_creator(),videos(),virtual_try_on_type,destination_url_type,grid_title,is_year_in_preview,view_tags,is_scene,rich_summary(),aggregated_pin_data(),is_oos_product,is_ghost,category,should_preload,image_medium_url,dark_profile_link,is_full_width,call_to_action_text,additional_hide_reasons,ip_eligible_for_stela,shuffle_asset(),comment_count,promoted_is_quiz,ad_match_reason,is_unsafe_for_comments,is_eligible_for_aggregated_comments,is_eligible_for_related_products,origin_pinner(),is_unsafe,is_native,ad_targeting_attribution,ad_closeup_behaviors,source_interest(),question_comment_id,image_crop,shuffle(),shopping_mdl_browser_type,should_mute,shopping_flags,promoted_lead_form(),promoted_is_showcase,is_eligible_for_web_closeup,domain,story_pin_data,tracking_params,is_eligible_for_pdp_plus,mobile_link,share_count,cacheable_id,tracked_link,is_eligible_for_brand_catalog,done_by_me,is_shopping_ad,title,carousel_data(),type,attribution,is_repin,promoted_is_lead_ad,comment_reply_comment_id,should_open_in_stream,dominant_color,product_pin_data(),creative_types,embed(),alt_text,is_cpc_ad,promoted_ios_deep_link,repin_count,is_eligible_for_pdp,promoted_is_removable,music_attributions},board.{image_cover_url,layout,owner(),id,privacy,is_ads_only,followed_by_me,name,image_thumbnail_url},interest.{follower_count,id,key,type,name,is_followed},productmetadatav2.{items},itemmetadata.{additional_images},richpingriddata.{aggregate_rating,id,type_name,products(),site_name,display_cook_time,is_product_pin_v2,display_name,actions,mobile_app},aggregatedpindata.{collections_header_text,catalog_collection_type,pin_tags,id,is_shop_the_look,has_xy_tags,is_dynamic_collections,aggregated_stats,pin_tags_chips,slideshow_collections_aspect_ratio},pincarouselslot.{domain,details,id,title,link,image_signature,ios_deep_link,ad_destination_url},storypindata.{has_product_pins,page_count,id,has_virtual_try_on_makeup_pins,static_page_count,total_video_duration,has_affiliate_products,pages_preview,metadata,type},shuffle.{id,type,source_app_type_detailed},embed.{src,width,type,height},pincarouseldata.{id,carousel_slots,index},storypinpage.{blocks,style,layout,id,image_signature_adjusted,video_signature,image_signature,music_attributions,type,should_mute,video[V_HLSV3_MOBILE,V_HLS_HEVC,V_HEVC_MP4_T1_V2,V_HEVC_MP4_T2_V2,V_HEVC_MP4_T3_V2,V_HEVC_MP4_T4_V2,V_HEVC_MP4_T5_V2]},shuffleasset.{id,item_type,shuffle_item_image,pin()},storypinimageblock.{image_signature,block_style,type,block_type,text},storypinvideoblock.{text,block_style,video_signature,type,block_type,video[V_HLSV3_MOBILE,V_HLS_HEVC,V_HEVC_MP4_T1_V2,V_HEVC_MP4_T2_V2,V_HEVC_MP4_T3_V2,V_HEVC_MP4_T4_V2,V_HEVC_MP4_T5_V2]},user.{explicitly_followed_by_me,id,image_small_url,show_creator_profile,full_name,native_pin_count,username,first_name},video.{id,video_List[V_HLSV3_MOBILE,V_HLS_HEVC]},board.cover_images[200x],pin.images[345x,736x],interest.images[70x70,236x],pincarouselslot.images[345x,736x],imagemetadata.canonical_images[1200x,474x],storypinimageblock.image[1200x,345x,736x],storypinpage.image_adjusted[1200x,345x,736x],storypinpage.image[1200x,345x,736x]",
            ),
            "y": (None, "0"),
            "h": (None, "1"),
            "camera_type": (None, "0"),
            "search_type": (None, "0"),
            "source_type": (None, "0"),
            "crop_source": (None, "5"),
            "w": (None, "1"),
            "page_size": (None, "25"),
            "page_size": (None, "50"),  # noqa: F601
            "image": open(str(outfile), "rb"),
        }

        def do_request(cookies, headers, files):
            response = requests.post(
                "https://api.pinterest.com/v3/visual_search/lens/search/",
                cookies=cookies,
                headers=headers,
                files=files,
            )
            return response.json()

        return await asyncio.to_thread(do_request, cookies, headers, files)

    async def do_download(self, url: str):
        async with self.locks["reverse_search"]:
            extension = url.split(".")[-1]
            filename = f"/root/{tuuid.tuuid()}.{extension}"
            async with aiofiles.open(filename, "wb") as input_file:
                async with Session() as session:
                    async with session.get(url) as response:
                        await input_file.write(await response.read())
            return filename


async def test_post():
    p = Pinterest()
    data = await p.get_post_or_pin("https://www.pinterest.com/pin/42080577763364147/")
    import orjson

    with open("data.json", "wb") as f:
        f.write(orjson.dumps(data))
    print(data)


async def test_user():
    p = Pinterest()
    data = await p.get_user("poshmark")
    print(data)
    from pinmodels import Model

    m = Model(**data)
    print(m.resource_response.data.dict())  # type: ignore
    return m


async def test_reverse():
    p = Pinterest()
    print(
        await p.reverse_search(
            "https://i.pinimg.com/474x/8e/22/61/8e226193088b7a446f26a424d6f3dbc6.jpg"
        )
    )


# asyncio.run(test_post())
