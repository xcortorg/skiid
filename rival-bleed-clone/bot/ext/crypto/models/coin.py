from __future__ import annotations

from typing import Any, Dict, List, Optional
from aiohttp import ClientSession
from pydantic import BaseModel


class ASSETALTERNATIVEID(BaseModel):
    NAME: Optional[str] = None
    ID: Optional[str] = None


class SUPPORTEDPLATFORM(BaseModel):
    BLOCKCHAIN: Optional[str] = None
    BLOCKCHAIN_ASSET_ID: Optional[int] = None
    TOKEN_STANDARD: Optional[str] = None
    EXPLORER_URL: Optional[str] = None
    SMART_CONTRACT_ADDRESS: Optional[str] = None
    LAUNCH_DATE: Optional[int] = None
    TRADING_AS: Optional[str] = None
    DECIMALS: Optional[int] = None
    IS_INHERITED: Optional[bool] = None
    RETIRE_DATE: Optional[int] = None


class ASSETCUSTODIAN(BaseModel):
    NAME: Optional[str] = None


class ASSETSECURITYMETRIC(BaseModel):
    NAME: Optional[str] = None
    OVERALL_SCORE: Optional[float] = None
    OVERALL_RANK: Optional[int] = None
    UPDATED_AT: Optional[int] = None


class SUPPORTEDSTANDARD(BaseModel):
    NAME: Optional[str] = None


class LAYERTWOSOLUTION(BaseModel):
    NAME: Optional[str] = None
    WEBSITE_URL: Optional[str] = None
    DESCRIPTION: Optional[str] = None
    CATEGORY: Optional[str] = None


class PRIVACYSOLUTIONFEATURE(BaseModel):
    NAME: Optional[str] = None


class PRIVACYSOLUTION(BaseModel):
    NAME: Optional[str] = None
    WEBSITE_URL: Optional[str] = None
    DESCRIPTION: Optional[str] = None
    PRIVACY_SOLUTION_TYPE: Optional[str] = None
    PRIVACY_SOLUTION_FEATURES: Optional[List[PRIVACYSOLUTIONFEATURE]] = None


class ENDPOINTSUSEDItem(BaseModel):
    URL: Optional[str] = None
    TYPE: Optional[str] = None
    LAST_CALL: Optional[int] = None
    LAST_CALL_SUCCESS: Optional[int] = None
    EXTERNAL_CACHE_KEY: Optional[str] = None


class CODEREPOSITORY(BaseModel):
    URL: Optional[str] = None
    MAKE_3RD_PARTY_REQUEST: Optional[bool] = None
    OPEN_ISSUES: Optional[int] = None
    CLOSED_ISSUES: Optional[int] = None
    OPEN_PULL_REQUESTS: Optional[int] = None
    CLOSED_PULL_REQUESTS: Optional[int] = None
    CONTRIBUTORS: Optional[int] = None
    FORKS: Optional[int] = None
    STARS: Optional[int] = None
    SUBSCRIBERS: Optional[int] = None
    LAST_UPDATED_TS: Optional[int] = None
    CREATED_AT: Optional[int] = None
    UPDATED_AT: Optional[int] = None
    LAST_PUSH_TS: Optional[int] = None
    CODE_SIZE_IN_BYTES: Optional[int] = None
    IS_FORK: Optional[bool] = None
    LANGUAGE: Optional[str] = None
    FORKED_ASSET_DATA: None = None
    ENDPOINTS_USED: Optional[List[ENDPOINTSUSEDItem]] = None


class ENDPOINTSUSEDItem1(BaseModel):
    URL: Optional[str] = None
    TYPE: Optional[str] = None
    LAST_CALL: Optional[int] = None
    LAST_CALL_SUCCESS: Optional[int] = None


class SUBREDDIT(BaseModel):
    URL: Optional[str] = None
    MAKE_3RD_PARTY_REQUEST: Optional[bool] = None
    NAME: Optional[str] = None
    CURRENT_ACTIVE_USERS: Optional[int] = None
    AVERAGE_POSTS_PER_DAY: Optional[float] = None
    AVERAGE_POSTS_PER_HOUR: Optional[float] = None
    AVERAGE_COMMENTS_PER_DAY: Optional[float] = None
    AVERAGE_COMMENTS_PER_HOUR: Optional[float] = None
    SUBSCRIBERS: Optional[int] = None
    COMMUNITY_CREATED_AT: Optional[int] = None
    LAST_UPDATED_TS: Optional[int] = None
    ENDPOINTS_USED: Optional[List[ENDPOINTSUSEDItem1]] = None


class TWITTERACCOUNT(BaseModel):
    URL: Optional[str] = None
    MAKE_3RD_PARTY_REQUEST: Optional[bool] = None
    NAME: Optional[str] = None
    USERNAME: Optional[str] = None
    VERIFIED: Optional[bool] = None
    VERIFIED_TYPE: Optional[str] = None
    FOLLOWING: Optional[int] = None
    FOLLOWERS: Optional[int] = None
    FAVOURITES: Optional[int] = None
    LISTS: Optional[int] = None
    STATUSES: Optional[int] = None
    ACCOUNT_CREATED_AT: Optional[int] = None
    LAST_UPDATED_TS: Optional[int] = None


class OTHERSOCIALNETWORK(BaseModel):
    NAME: Optional[str] = None
    URL: Optional[str] = None


class EXPLORERADDRESS(BaseModel):
    URL: Optional[str] = None


class ASSETINDUSTRY(BaseModel):
    ASSET_INDUSTRY: Optional[str] = None
    JUSTIFICATION: Optional[str] = None


class CONSENSUSMECHANISM(BaseModel):
    NAME: Optional[str] = None


class CONSENSUSALGORITHMTYPE(BaseModel):
    NAME: Optional[str] = None
    DESCRIPTION: Optional[str] = None


class HASHINGALGORITHMTYPE(BaseModel):
    NAME: Optional[str] = None


class PRICECONVERSIONASSET(BaseModel):
    ID: Optional[int] = None
    SYMBOL: Optional[str] = None
    ASSET_TYPE: Optional[str] = None


class TOPLISTBASERANK(BaseModel):
    CREATED_ON: Optional[int] = None
    LAUNCH_DATE: Optional[int] = None
    CIRCULATING_MKT_CAP_USD: Optional[int] = None
    TOTAL_MKT_CAP_USD: Optional[int] = None
    SPOT_MOVING_24_HOUR_QUOTE_VOLUME_USD: Optional[int] = None
    SPOT_MOVING_7_DAY_QUOTE_VOLUME_USD: Optional[int] = None
    SPOT_MOVING_30_DAY_QUOTE_VOLUME_USD: Optional[int] = None


class PROJECTLEADER(BaseModel):
    LEADER_TYPE: Optional[str] = None
    FULL_NAME: Optional[str] = None
    CONTACT_MEDIUM: Optional[str] = None
    ADDRESS: Optional[str] = None
    COMMENTS: Optional[str] = None


class ASSOCIATEDCONTACTDETAIL(BaseModel):
    CONTACT_TYPE: Optional[str] = None
    CONTACT_MEDIUM: Optional[str] = None
    FULL_NAME: Optional[str] = None
    ADDRESS: Optional[str] = None
    COMMENTS: Optional[str] = None


class Data(BaseModel):
    ID: Optional[int] = None
    TYPE: Optional[str] = None
    ID_LEGACY: Optional[int] = None
    ID_PARENT_ASSET: None = None
    ID_ASSET_ISSUER: None = None
    SYMBOL: Optional[str] = None
    URI: Optional[str] = None
    IS_PUBLIC: Optional[bool] = None
    ASSET_TYPE: Optional[str] = None
    ASSET_ISSUER_NAME: None = None
    PARENT_ASSET_SYMBOL: None = None
    CREATED_ON: Optional[int] = None
    UPDATED_ON: Optional[int] = None
    PUBLIC_NOTICE: None = None
    NAME: Optional[str] = None
    LOGO_URL: Optional[str] = None
    LAUNCH_DATE: Optional[int] = None
    PREVIOUS_ASSET_SYMBOLS: None = None
    ASSET_ALTERNATIVE_IDS: Optional[List[ASSETALTERNATIVEID]] = None
    ASSET_DESCRIPTION_SNIPPET: Optional[str] = None
    ASSET_DECIMAL_POINTS: Optional[int] = None
    SUPPORTED_PLATFORMS: Optional[List[SUPPORTEDPLATFORM]] = None
    ASSET_CUSTODIANS: Optional[List[ASSETCUSTODIAN]] = None
    CONTROLLED_ADDRESSES: None = None
    ASSET_SECURITY_METRICS: Optional[List[ASSETSECURITYMETRIC]] = None
    SUPPLY_MAX: Optional[float] = None
    SUPPLY_ISSUED: Optional[int] = None
    SUPPLY_TOTAL: Optional[int] = None
    SUPPLY_CIRCULATING: Optional[int] = None
    SUPPLY_FUTURE: Optional[float] = None
    SUPPLY_LOCKED: Optional[int] = None
    SUPPLY_BURNT: Optional[int] = None
    SUPPLY_STAKED: Optional[int] = None
    LAST_BLOCK_MINT: Optional[float] = None
    LAST_BLOCK_BURN: None = None
    BURN_ADDRESSES: None = None
    LOCKED_ADDRESSES: None = None
    HAS_SMART_CONTRACT_CAPABILITIES: Optional[bool] = None
    SMART_CONTRACT_SUPPORT_TYPE: Optional[str] = None
    TARGET_BLOCK_MINT: Optional[float] = None
    TARGET_BLOCK_TIME: Optional[int] = None
    LAST_BLOCK_NUMBER: Optional[int] = None
    LAST_BLOCK_TIMESTAMP: Optional[int] = None
    LAST_BLOCK_TIME: Optional[int] = None
    LAST_BLOCK_SIZE: Optional[int] = None
    LAST_BLOCK_ISSUER: None = None
    LAST_BLOCK_TRANSACTION_FEE_TOTAL: None = None
    LAST_BLOCK_TRANSACTION_COUNT: Optional[int] = None
    LAST_BLOCK_HASHES_PER_SECOND: Optional[int] = None
    LAST_BLOCK_DIFFICULTY: Optional[float] = None
    SUPPORTED_STANDARDS: Optional[List[SUPPORTEDSTANDARD]] = None
    LAYER_TWO_SOLUTIONS: Optional[List[LAYERTWOSOLUTION]] = None
    PRIVACY_SOLUTIONS: Optional[List[PRIVACYSOLUTION]] = None
    CODE_REPOSITORIES: Optional[List[CODEREPOSITORY]] = None
    SUBREDDITS: Optional[List[SUBREDDIT]] = None
    TWITTER_ACCOUNTS: Optional[List[TWITTERACCOUNT]] = None
    DISCORD_SERVERS: None = None
    TELEGRAM_GROUPS: None = None
    OTHER_SOCIAL_NETWORKS: Optional[List[OTHERSOCIALNETWORK]] = None
    HELD_TOKEN_SALE: Optional[bool] = None
    HELD_EQUITY_SALE: Optional[bool] = None
    WEBSITE_URL: Optional[str] = None
    BLOG_URL: Optional[str] = None
    WHITE_PAPER_URL: Optional[str] = None
    OTHER_DOCUMENT_URLS: None = None
    EXPLORER_ADDRESSES: Optional[List[EXPLORERADDRESS]] = None
    RPC_OPERATORS: None = None
    ASSET_SYMBOL_GLYPH: Optional[str] = None
    IS_EXCLUDED_FROM_PRICE_TOPLIST: None = None
    IS_EXCLUDED_FROM_VOLUME_TOPLIST: None = None
    IS_EXCLUDED_FROM_MKT_CAP_TOPLIST: None = None
    ASSET_INDUSTRIES: Optional[List[ASSETINDUSTRY]] = None
    CONSENSUS_MECHANISMS: Optional[List[CONSENSUSMECHANISM]] = None
    CONSENSUS_ALGORITHM_TYPES: Optional[List[CONSENSUSALGORITHMTYPE]] = None
    HASHING_ALGORITHM_TYPES: Optional[List[HASHINGALGORITHMTYPE]] = None
    PRICE_USD: Optional[float] = None
    PRICE_USD_SOURCE: Optional[str] = None
    PRICE_USD_LAST_UPDATE_TS: Optional[int] = None
    PRICE_CONVERSION_ASSET: Optional[PRICECONVERSIONASSET] = None
    PRICE_CONVERSION_RATE: Optional[int] = None
    PRICE_CONVERSION_VALUE: Optional[float] = None
    PRICE_CONVERSION_SOURCE: Optional[str] = None
    PRICE_CONVERSION_LAST_UPDATE_TS: Optional[int] = None
    MKT_CAP_PENALTY: Optional[int] = None
    CIRCULATING_MKT_CAP_USD: Optional[float] = None
    TOTAL_MKT_CAP_USD: Optional[float] = None
    CIRCULATING_MKT_CAP_CONVERSION: Optional[float] = None
    TOTAL_MKT_CAP_CONVERSION: Optional[float] = None
    SPOT_MOVING_24_HOUR_QUOTE_VOLUME_TOP_TIER_DIRECT_USD: Optional[float] = None
    SPOT_MOVING_24_HOUR_QUOTE_VOLUME_DIRECT_USD: Optional[float] = None
    SPOT_MOVING_24_HOUR_QUOTE_VOLUME_TOP_TIER_USD: Optional[float] = None
    SPOT_MOVING_24_HOUR_QUOTE_VOLUME_USD: Optional[float] = None
    SPOT_MOVING_24_HOUR_QUOTE_VOLUME_TOP_TIER_CONVERSION: Optional[float] = None
    SPOT_MOVING_24_HOUR_QUOTE_VOLUME_CONVERSION: Optional[float] = None
    SPOT_MOVING_7_DAY_QUOTE_VOLUME_TOP_TIER_DIRECT_USD: Optional[float] = None
    SPOT_MOVING_7_DAY_QUOTE_VOLUME_DIRECT_USD: Optional[float] = None
    SPOT_MOVING_7_DAY_QUOTE_VOLUME_TOP_TIER_USD: Optional[float] = None
    SPOT_MOVING_7_DAY_QUOTE_VOLUME_USD: Optional[float] = None
    SPOT_MOVING_7_DAY_QUOTE_VOLUME_TOP_TIER_CONVERSION: Optional[float] = None
    SPOT_MOVING_7_DAY_QUOTE_VOLUME_CONVERSION: Optional[float] = None
    SPOT_MOVING_30_DAY_QUOTE_VOLUME_TOP_TIER_DIRECT_USD: Optional[float] = None
    SPOT_MOVING_30_DAY_QUOTE_VOLUME_DIRECT_USD: Optional[float] = None
    SPOT_MOVING_30_DAY_QUOTE_VOLUME_TOP_TIER_USD: Optional[float] = None
    SPOT_MOVING_30_DAY_QUOTE_VOLUME_USD: Optional[float] = None
    SPOT_MOVING_30_DAY_QUOTE_VOLUME_TOP_TIER_CONVERSION: Optional[float] = None
    SPOT_MOVING_30_DAY_QUOTE_VOLUME_CONVERSION: Optional[float] = None
    SPOT_MOVING_24_HOUR_CHANGE_USD: Optional[float] = None
    SPOT_MOVING_24_HOUR_CHANGE_PERCENTAGE_USD: Optional[float] = None
    SPOT_MOVING_24_HOUR_CHANGE_CONVERSION: Optional[float] = None
    SPOT_MOVING_24_HOUR_CHANGE_PERCENTAGE_CONVERSION: Optional[float] = None
    SPOT_MOVING_7_DAY_CHANGE_USD: Optional[float] = None
    SPOT_MOVING_7_DAY_CHANGE_PERCENTAGE_USD: Optional[float] = None
    SPOT_MOVING_7_DAY_CHANGE_CONVERSION: Optional[float] = None
    SPOT_MOVING_7_DAY_CHANGE_PERCENTAGE_CONVERSION: Optional[float] = None
    SPOT_MOVING_30_DAY_CHANGE_USD: Optional[float] = None
    SPOT_MOVING_30_DAY_CHANGE_PERCENTAGE_USD: Optional[float] = None
    SPOT_MOVING_30_DAY_CHANGE_CONVERSION: Optional[float] = None
    SPOT_MOVING_30_DAY_CHANGE_PERCENTAGE_CONVERSION: Optional[float] = None
    TOPLIST_BASE_RANK: Optional[TOPLISTBASERANK] = None
    ASSET_DESCRIPTION: Optional[str] = None
    ASSET_DESCRIPTION_SUMMARY: Optional[str] = None
    PROJECT_LEADERS: Optional[List[PROJECTLEADER]] = None
    ASSOCIATED_CONTACT_DETAILS: Optional[List[ASSOCIATEDCONTACTDETAIL]] = None
    SEO_TITLE: Optional[str] = None
    SEO_DESCRIPTION: Optional[str] = None
    ASSET_DESCRIPTION_EXTENDED_SEO: Optional[str] = None
    COMMENT: Optional[str] = None
    ASSIGNED_TO: Optional[int] = None
    ASSIGNED_TO_USERNAME: Optional[str] = None
    CREATED_BY: Optional[int] = None
    CREATED_BY_USERNAME: Optional[str] = None
    UPDATED_BY: Optional[int] = None
    UPDATED_BY_USERNAME: Optional[str] = None
    IS_USED_IN_DEFI: Optional[bool] = None
    IS_USED_IN_NFT: Optional[bool] = None
    TOTAL_ENDPOINTS_OK: Optional[int] = None
    TOTAL_ENDPOINTS_WITH_ISSUES: Optional[int] = None


class CryptoResponse(BaseModel):
    Data: Optional[Data] = None
    Err: Optional[Dict[str, Any]] = None

    @classmethod
    async def from_coin(cls, coin: str, currency: Optional[str] = "usd"):
        async with ClientSession() as session:
            async with session.get(
                "https://api.cryptocompare.coindesk.com/asset/v1/metadata",
                params={
                    "asset": coin.upper(),
                    "asset_lookup_priority": "SYMBOL",
                    "quote_asset": currency.upper(),
                    "response_format": "JSON",
                },
            ) as response:
                data = await response.read()
        return cls.parse_raw(data)
