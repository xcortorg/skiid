PIPED_API: str = "pipedapi.adminforge.de"
WARP: str = "socks5://localhost:7483"


class DISCORD:
    """
    Discord authentication tokens and IDs.
    """

    TOKEN: str = (
        "MTE0OTUzNTgzNDc1Njg3NDI1MA.G4pwXL.WwYzvA5A9LNvWxJ30XpT1vPAc2CnWb2s4BWNEY"
    )
    PUBLIC_KEY: str = ""
    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    REDIRECT_URI: str = ""


class CLIENT:
    """
    Client settings for the bot.
    """

    UPDATE_SHARD_STATS: bool | None = True
    PREFIX: str = ","
    DESCRIPTION: str | None = None
    OWNER_IDS: list[int] = [
        744806691396124673, 
        930383131863842816,
        915350867438338058
    ]  
    # yurrion  # adam # rico
    SUPPORT_SERVER: str = "https://discord.gg/greedbot"
    WEBSITE: str = "https://greed.best/commands"
    class COLORS:
        APPROVE: int = 0x48DB01
        NEUTRAL: int = 0x7291DF
        WARN: int = 0xFF3735

class STAFF_ROLES:
    STAFF_IDS: list[int] = [
        392300135323009024,
        1259443225542918218,
        153643814605553665,
        744806691396124673, 
        930383131863842816,
        915350867438338058
    ]
    # xur # feud # keron  # yurrion # adam # rico
    MODERATOR_IDS: list[int] = [
        392300135323009024,
        1259443225542918218,
        153643814605553665,
        744806691396124673,  
    ]
    # xur # feud # keron  # yurrion # adam # rico
    DEVELOPER_IDS: list[int] = [
        744806691396124673, 
        930383131863842816,
        915350867438338058
    ]
    # yurrion  # adam # rico
    OWNER_IDS: list[int] = [
        915350867438338058,
        930383131863842816
    ]
    # rico # adam

class LAVALINK:
    """
    Lavalink configuration
    """

    HOST: str = "0.0.0.0"
    PORT: int | None = None
    PASSWORD: str | None = None


class NETWORK:
    """
    Network configuration
    """

    HOST: str | None = None
    PORT: int | None = None


class DATABASE:
    DSN: str = "postgresql://postgres:aiem6hP-zXtt0m22x35m@localhost:5432/greed"


class REDIS:
    DB: int = 0
    HOST: str = "localhost"
    PORT: int = 6379
    PASS: str = "H?vanmir09Mason12screen-rzan"


class AUTHORIZATION:
    """
    AUTHORIZATION configuration
    """

    class SPOTIFY:
        CLIENT_ID: str = "908846bb106d4190b4cdf5ceb3d1e0e5"
        CLIENT_SECRET: str = "d08df8638ee44bdcbfe6057a5e7ffd78"

    class TWITCH:
        CLIENT_ID: str = "30guvrlrw4lvf3knqsbin99asxdg4t"
        CLIENT_SECRET: str = "pxfuxxo2mn5qebq5xrl8g31ryh91gz"

    class REDDIT:
        CLIENT_ID: str = "gM_QdMnswc2geCIvlbTkdQ"
        CLIENT_SECRET: str = "sMnPrsejKe5btrGPULuYrVOjMpAXkA"

    WEATHER: str = "0c5b47ed5774413c90b155456223004"
    FNBR: str = "20490584-82aa-4ac3-8831-73d411d7c3d2"
    LASTFM: list[str] = [
        "bc84a74e4b3cf9eb040fbeaab4071df5",
        "4210d59afeeb6c350442d7141747704c",
    ]
    GEMINI: str = "AIzaSyCjgGH83OyUblhY4JHMQFJ5j3UVH5ztkaA"
    WOLFRAM: str = "W95RJG-RRUXURP6XY"


class EMOJIS:
    class CONFIG:
        WARN: str = "<:warn:1225126477880623175>"
        APPROVE: str = "<:check:1225126153098891304>"
        DENY: str = "<:deny:1225126443638325361>"

    class BADGES:
        HYPESQUAD_BRILLIANCE: str = "<:hypesquad_brilliance:1247992057067212833>"
        BOOST: str = "<:boost:1247992058036097236>"
        STAFF: str = "<:staff:1247992058975879312>"
        VERIFIED_BOT_DEVELOPER: str = "<:verified_bot_developer:1247992059919466588>"
        SERVER_OWNER: str = "<:server_owner:1247992060598947861>"
        HYPESQUAD_BRAVERY: str = "<:hypesquad_bravery:1247992061773221908>"
        PARTNER: str = "<:partner:1247992062318477463>"
        HYPESQUAD_BALANCE: str = "<:hypesquad_balance:1247992063174250616>"
        EARLY_SUPPORTER: str = "<:early_supporter:1247992063849660416>"
        HYPESQUAD: str = "<:hypesquad:1247992064713691198>"
        BUG_HUNTER_LEVEL_2: str = "<:bug_hunter_level_2:1247992065179127860>"
        CERTIFIED_MODERATOR: str = "<:certified_moderator:1247992066554728618>"
        NITRO: str = "<:nitro:1247992067309965423>"
        BUG_HUNTER: str = "<:bug_hunter:1247992068005953719>"
        ACTIVE_DEVELOPER: str = "<:active_developer:1247992068895146095>"
    
    class STAFF_BADGES: 
        GREED_DEVELOPER: str = "<:uiGreedDeveloper:1270306434445479937>"
        GREED_MODERATOR: str = "<:uiGreedModerator:1270306432268370000>"
        GREED_OWNER: str = "<:uiGreedOwner:1270306439079923742>"
        GREED_STAFF: str = "<:uiGreedStaff:1270306436353888329>"

    class PAGINATOR:
        NEXT: str = "<:next:1247992069620764857>"
        NAVIGATE: str = "<:navigate:1247992070510219384>"
        PREVIOUS: str = "<:previous:1247992071634161765>"
        CANCEL: str = "<:cancel:1247992072305250345>"

    class AUDIO:
        SKIP: str = "<:skip:1247992073794093106>"
        RESUME: str = "<:resume:1247992074561650880>"
        REPEAT: str = "<:repeat:1247992075677597707>"
        PREVIOUS: str = "<:previous:1247992076964991059>"
        PAUSE: str = "<:pause:1247992077694799894>"
        QUEUE: str = "<:queue:1247992079091503194>"
        REPEAT_TRACK: str = "<:repeat_track:1247992079737421824>"

    class VOICEMASTER:
        REJECT: str = "<:greedKick:1248724625727426661>"
        DELETE: str = "<:greedReject:1250620697982795837>"
        PLUS: str = "<:greedPlus:1248724621751095409>"
        MINUS: str = "<:greedMinus:1248724620383748198>"
        LOCK: str = "<:greedLock:1248724611370192928>"
        UNLOCK: str = "<:greedUnlock:1248724613127602277>"
        GHOST: str = "<:greedUnghost:1248724617036562605>"
        UNGHOST: str = "<:greedUnghost:1248724617036562605>"
        INFO: str = "<:greedInfo:1248724623537868851>"
        CLAIM: str = "<:greedClaim:1248724627161878559>"

    class UTILS:
        REPLY: str = "<:greedReply:1270320315532312576>"
        CHAT: str = "<:greedChat:1270320816109650013>"


class API:
    greed: str = "Oxb0ZpNkWVmkA2J6JnI3xr9qORPJv"
    TOPGG: str = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjExNDk1MzU4MzQ3NTY4NzQyNTAiLCJib3QiOnRydWUsImlhdCI6MTcwODYyMDQ4Nn0.htIQgitv90wWGmK8qXf0zMTiDIF0xO7coZfBwUe9k0c"
    )

class ANALYTICS:
    api_key: str = "phc_ds8DUIOmRamXtLOekJPgdUJ5sIYxUyagooTn3Y3ZI0k"
    url: str = "https://us.i.posthog.com"

class AVATAR_HISTORY:
    BUNNY_NET_FTP_HOST: str = "ny.storage.bunnycdn.com"
    BUNNY_NET_FTP_PORT: int = 21
    BUNNY_NET_FTP_USERNAME: str = "greedavh"
    BUNNY_NET_FTP_PASSWORD: str = "c9861f15-e5ba-415b-a71db01632fc-6dce-421c"
