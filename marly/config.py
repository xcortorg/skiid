PROXY = "socks5://127.0.0.1:40000"


class Marly:
    PREFIX = ","
    BOT_TOKEN = (
        ""
    )
    OWNER_ID = [1247076592556183598]
    SUPPORT_SERVER = "https://discord.gg/example"
    DOCS_URL = "https://docs.example.com"
    WEBSITE_URL = "https://example.com"
    EMBED_BUILDER_URL = "https://embedbuilder-five.vercel.app/"
    API_KEY = ""
    COLOR = 0x2B2D31


class Color:
    approve = 0xA4EB78
    warn = 0xFAA81A
    deny = 0xFF6464
    spotify = 0x1DD65E
    lastfm = 0xD51107
    add = 0x36AAE0
    remove = 0x36AAE0
    baseColor = 0x747F8D
    neutral = 0x747F8D
    cooldown = 0x4CC8F4
    info = 0x747F8D
    white = 0xFFFFFF
    shazam = 0x1F70FC
    invisible = 0x2B2D31
    dm_yellow = 0xFADB5E


class Database:
    host = "localhost"
    port = 5432
    username = "postgres"
    password = "admin"
    database = "marly"


class Redis:
    db = 0
    host = "localhost"
    port = 6379
    hash = "pTc6Ajf72sHvQvFBf9w3"


class LAVALINK:
    NODE_COUNT: int = 1
    HOST: str = "23.160.168.180"
    PORT: int = 25920
    PASSWORD: str = "youshallnotpass"



class Emojis:
    class Embeds:
        APPROVE = "<:approve:1291906736948641936>"
        WARN = "<:warn:1291906735040364604>"
        DENY = "<:deny:1291906739876401213>"
        WAVE = ":wave:"
        COOLDOWN = "<:cooldown:1291906737883975751>"
        NOTES = ":notepad_spiral:"
        JUUL = "<:juul:1292677353377366016>"
        NOJUUL = "<:no_juul:1292677354656632993>"
        BLUNT = "<:dblunt:1305267857520853083>"

    class Paginator:
        NEXT = "<:next:1285457501877174303>"
        NAVIGATE = "<:navigate:1285457495191719956>"
        PREVIOUS = "<:previous:1285457511520014371>"
        CANCEL = "<:cancel:1285457487637647422>"
        TRASH = "<:trash:1292022991093235851>"

    class BADGES:
        HYPESQUAD_BRILLIANCE = "<:hypesquad_brilliance:1303601472549949511>"
        BOOST = "<:boost:1303601344594313256>"
        STAFF = "<:staff:1303601528611016796>"
        VERIFIED_BOT_DEVELOPER = "<:verified_bot_developer:1303601361648222218>"
        SERVER_OWNER = "<:server_owner:1303601358342979714>"
        HYPESQUAD_BRAVERY = "<:hypesquad_bravery:1303601351204409424>"
        PARTNER = "<:partner:1303601511863156827>"
        HYPESQUAD_BALANCE = "<:hypesquad_balance:1303601453453021204>"
        EARLY_SUPPORTER = "<:early_supporter:1303601347773595692>"
        HYPESQUAD = "<:hypesquad:1303601348423581767>"
        BUG_HUNTER_LEVEL_2 = "<:bug_hunter_level_2:1303601346448195674>"
        CERTIFIED_MODERATOR = "<:certified_moderator:1303601347228205056>"
        NITRO = "<:nitro:1303601354299936869>"
        BUG_HUNTER = "<:bug_hunter:1303601345445494865>"
        ACTIVE_DEVELOPER = "<:active_developer:1303601343642206299>"

    class Music:
        SHUFFLE = "<:random:1293040572579450951>"
        PREVIOUS = "<:previews:1303451999861346386>"
        PAUSED = "<:resume:1303242936221302815>"
        UNPAUSED = "<:pause:1303242929334386730>"
        SKIP = "<:forward:1303451979799859360>"
        NO_LOOP = "<:repeat:1303242933465780254>"
        LOOP_QUEUE = "<:loop:1305026293800243220>"
        LOOP_TRACK = "<:loop_track:1305025702051188788>"

    class Interface:
        lock: str = "<:lock:1292400569331220501>"
        unlock: str = "<:unlock:1292400591804436511>"
        ghost: str = "<:ghost:1292400541862723595>"
        reveal: str = "<:reveal:1292400546384445450>"
        claim: str = "<:claim:1292400539094614027>"
        disconnect: str = "<:disconnect:1292400541317464074>"
        activity: str = "<:activity:1292400538431918100>"
        information: str = "<:information:1292400544123719770>"
        increase: str = "<:increase:1292400543183929386>"
        decrease: str = "<:decrease:1292400539908177964>"


class Apis:
    LASTFM: list[str] = [
        "",
        "",
    ]
    GEMINI: str = ""
    WEATHER: str = ""
    SOUNDCLOUD: str = ""
    TENOR: str = ""

    class SPOTIFY:
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""


ping_responses = [
    "i know nothing.",
    "a connection to the server",
    "i dont even know what to put here",
    "the feds",
    "said im in the club alone",
    "no one",
    "the chinese government",
    "your mom",
    "the russians",
    "that new marly.bot domain",
    "mell's mud hut",
    "marly bot proxy server",
    "6ix9ines ankle monitor",
    "trumps ears",
    "The",
    "mell's mud hut",
    "267 tries to wake derrick up from hibernation",
    "horny asian women around your area",
    "the migos minecraft server",
    "localhost",
]


class Network:
    host = "localhost"
    port = 3030
