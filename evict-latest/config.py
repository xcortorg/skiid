class DISCORD:
    """
    Main bot connection class.
    """
    TOKEN: str = ""
    PUBLIC_KEY: str = ""
    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    REDIRECT_URI: str = ""
    CDN_API_KEY: str = ""

class CLIENT:
    """
    Main client class.
    """
    PREFIX: str = ""
    DESCRIPTION: str | None = None
    OWNER_IDS: list[int] = []
    SUPPORT_URL: str = ""
    INVITE_URL: str = ""
    TWITCH_URL: str = ""
    BACKEND_HOST: str = ""
    FRONTEND_HOST: str = ""
    WARP: str = ""

class LOGGER:
    """
    Change the bots logging channels.
    """
    MAIN_GUILD: int = 0
    LOGGING_GUILD: int = 0
    TESTING_GUILD: int = 0
    COMMAND_LOGGER: int = 0
    STATUS_LOGGER: int = 0
    GUILD_JOIN_LOGGER: int = 0
    GUILD_BLACKLIST_LOGGER: int = 0
    USER_BLACKLIST_LOGGER: int = 0

class LAVALINK:
    """
    Lavalink authentication node.
    """
    NODE_COUNT: int = 0
    HOST: str = ""
    PORT: int = 0
    PASSWORD: str = ""

class NETWORK:
    """
    Main IPC authentication class.
    """
    HOST: str = ""
    PORT: int = 0
    
class DATABASE:
    """
    Postgres authentication class.
    """
    DSN: str = ""

class REDIS:
    """
    Redis authentication class.
    """
    DB: int = 0
    HOST: str = ""
    PORT: int = 0

class AUTHORIZATION:
    """
    API keys for various services.
    """
    FNBR: str = ""
    CLEVER: str = ""
    WOLFRAM: str = ""
    WEATHER: str = ""
    OSU: str = ""
    LASTFM: list[str] = []
    SOUNDCLOUD: str = ""
    GEMINI: str = ""
    KRAKEN: str = ""
    FERNET_KEY: str = ""
    PIPED_API: str = ""
    JEYY_API: str = ""
    OPENAI: str = ""
    LOVENSE: str = ""

    class GOOGLE:
        """
        Google API class.
        """
        CX: str = ""
        KEY: str = ""

    class TWITCH:
        """
        Twitch API class.
        """
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""

    class SPOTIFY:
        """
        Spotify API class.
        """
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""

    class REDDIT:
        """
        Reddit API class.
        """
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""

    class BACKUPS:
        """
        BunnyCDN backups authentication class.
        """
        HOST: str = ""
        USER: str = ""
        PASSWORD: str = ""

    class AVH:
        """
        BUNNYCDN AVH authentication class.
        """
        URL: str = ""
        ACCESS_KEY: str = ""

    class SOCIALS:
        """
        BUNNYCDN SOCIALS authentication class.
        """
        URL: str = ""
        ACCESS_KEY: str = ""

class EMOJIS:
    """
    Controls the emojis throughout the bot.
    """
    class FUN:
        LESBIAN: str = ""
        GAY: str = ""
        DUMBASS: str = ""
    
    class ECONOMY:
        """
        Changes the emojis on the economy commands.
        """
        WELCOME: str = ""
        COMMAND: str = ""
        GEM: str = ""
        CROWN: str = ""
        INVIS: str = ""
    
    class POLL:
        """
        Change the emojis used on the poll embeds.
        """
        BLR: str = ""
        SQUARE: str = ""
        BRR: str = ""
        WLR: str = ""
        WHITE: str = ""
        WRR: str = ""

    class STAFF:
        """
        Changes the emojis on staff commands.
        """
        DEVELOPER: str = ""
        HEADSTAFF: str = ""
        HEADQA: str = ""
        OWNER: str = ""
        SUPPORT: str = ""
        TRIAL: str = ""
        MODERATOR: str = ""
        DONOR: str = ""
        INSTANCE: str = ""
        STAFF: str = ""

    class INTERFACE:
        """
        Changes the emojis on the VoiceMaster Panel.
        """
        LOCK: str = ""
        UNLOCK: str = ""
        GHOST: str = ""
        REVEAL: str = ""
        CLAIM: str = ""
        DISCONNECT: str = ""
        ACTIVITY: str = ""
        INFORMATION: str = ""
        INCREASE: str = ""
        DECREASE: str = ""

    class PAGINATOR:
        """
        Changes the emojis on the paginator.
        """
        NEXT: str = ""
        NAVIGATE: str = ""
        PREVIOUS: str = ""
        CANCEL: str = ""

    class AUDIO:
        """
        Changes the emojis on the audio panel.
        """
        SKIP: str = ""
        RESUME: str = ""
        REPEAT: str = ""
        PREVIOUS: str = ""
        PAUSE: str = ""
        QUEUE: str = ""
        REPEAT_TRACK: str = ""

    class ANTINUKE:
        """
        Changes the emojis on the Antinuke-Config command.
        """
        ENABLE: str = ""
        DISABLE: str = ""

    class BADGES:
        """
        Changes the emojis that show on badges.
        """
        HYPESQUAD_BRILLIANCE: str = ""
        BOOST: str = ""
        STAFF: str = ""
        VERIFIED_BOT_DEVELOPER: str = ""
        SERVER_OWNER: str = ""
        HYPESQUAD_BRAVERY: str = ""
        PARTNER: str = ""
        HYPESQUAD_BALANCE: str = ""
        EARLY_SUPPORTER: str = ""
        HYPESQUAD: str = ""
        BUG_HUNTER_LEVEL_2: str = ""
        CERTIFIED_MODERATOR: str = ""
        NITRO: str = ""
        BUG_HUNTER: str = ""
        ACTIVE_DEVELOPER: str = ""

    class CONTEXT:
        """
        Changes the emojis on context.
        """
        APPROVE: str = ""
        DENY: str = ""
        WARN: str = ""
        FILTER: str = ""
        LEFT: str = ""
        RIGHT: str = ""
        JUUL: str = ""
        NO_JUUL: str = ""

    class SOCIAL:
        """
        Changes the emojis on social commands.
        """
        DISCORD: str = ""
        GITHUB: str = ""
        WEBSITE: str = ""

    class TICKETS:
        """
        Changes the emojis on tickets.
        """
        TRASH: str = ""

    class SPOTIFY:
        """
        Changes the emojis on the Spotify commands.
        """
        LEFT: str = ""
        RIGHT: str = ""
        BLACK: str = ""
        BLACK_RIGHT: str = ""
        WHITE: str = ""
        ICON: str = ""
        LISTENING: str = ""
        SHUFFLE: str = ""
        REPEAT: str = ""
        DEVICE: str = ""
        NEXT: str = ""
        PREVIOUS: str = ""
        PAUSE: str = ""
        VOLUME: str = ""
        FAVORITE: str = ""
        REMOVE: str = ""
        EXPLCIT: str = ""
    
    class LOVENSE:
        """
        Changes the emojis on the Lovense commands.
        """
        LOVENSE: str = ""
        KEY: str = ""
        IV: str = ""
    
    class DOCKET: 
        """
        Change the emojis on the commands relating to Docket.
        """
        INFO: str = ""
        YELLOW: str = ""
        BLACK: str = ""
        PURPLE: str = ""
        RED: str = ""
        CYAN: str = ""
    
    class MISC:
        """
        Miscellaneous emojis used throughout the bot.
        """
        CONNECTION: str = ""
        CRYPTO: str = ""
        BITCOIN: str = ""
        ETHEREUM: str = ""
        XRP: str = ""
        LITECOIN: str = ""
        EXTRA_SUPPORT: str = ""
        SECURITY: str = ""
        ANAYLTICS: str = ""
        REDUCED_COOLDOWNS: str = ""
        AI: str = ""
        MODERATION: str = ""
        COMMANDS: str = ""

class ROLES:
    """
    Changes the roles on the bot.
    """
    MODERATOR: int = 0
    TRIAL: int = 0
    DEVELOPER: int = 0
    HEADSTAFF: int = 0
    HEADQA: int = 0
    SUPPORT: int = 0
    DONOR: int = 0
    INSTANCE: int = 0

class COLORS:
    """
    Changes the colors on context outputs.
    """
    NEUTRAL: int = 0
    APPROVE: int = 0
    WARN: int = 0
    DENY: int = 0
    SPOTIFY: int = 0

class ECONOMY:
    """
    Changes the chances on economy commands.
    """
    CHANCES = {
        "roll": {"percentage": 0.0, "total": 0.0},
        "coinflip": {"percentage": 0.0, "total": 0.0},
        "gamble": {"percentage": 0.0, "total": 0.0},
        "supergamble": {"percentage": 0.0, "total": 0.0},
    }

class RATELIMITS:
    """
    Changes the rate limits on the bot.
    """
    PER_10S: int = 0
    PER_30S: int = 0
    PER_1M: int = 0