WARP = "socks5://127.0.0.1:40000"


class Bleed:
    token = ""
    prefix = ","
    owner_id = []
    support = "https://discord.gg/example"
    website = "https://example.com"
    docs = "https://docs.example.com"
    servername = "Bleed"


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


class Database:
    host = "localhost"
    port = 5432
    username = "postgres"
    password = "admin"
    database = "bleed"


class Redis:
    db = 2
    host = "localhost"
    port = 6379
    hash = "pTc6Ajf72sHvQvFBf9w3"


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
    "that new bleed.bot domain",
    "mell's mud hut",
    "Bleed bot proxy server",
    "6ix9ines ankle monitor",
    "trumps ears",
    "The",
    "mell's mud hut",
    "267 tries to wake derrick up from hibernation",
    "horny asian women around your area",
    "the migos minecraft server",
    "localhost",
]


class Emoji:

    class Paginator:
        next = "<:next:1285457501877174303>"
        navigate = "<:navigate:1285457495191719956>"
        previous = "<:previous:1285457511520014371>"
        cancel = "<:cancel:1285457487637647422>"
        trash = "<:trash:1292022991093235851>"
        random = "<:random:1293040572579450951>"

    class Interface:
        lock = "<:lock:1292400569331220501>"
        unlock = "<:unlock:1292400591804436511>"
        ghost = "<:ghost:1292400541862723595>"
        reveal = "<:reveal:1292400546384445450>"
        claim = "<:claim:1292400539094614027>"
        disconnect = "<:disconnect:1292400541317464074>"
        activity = "<:activity:1292400538431918100>"
        information = "<:information:1292400544123719770>"
        increase = "<:increase:1292400543183929386>"
        decrease = "<:decrease:1292400539908177964>"

    class Music:
        PAUSED = "<:resume:1303452008795340882>"
        UNPAUSED = "<:paused:1303451990038286346>"
        PREVIOUS = "<:previews:1303451999861346386>"
        SKIP = "<:forward:1303451979799859360>"

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

    approve = "<:approve:1291906736948641936>"
    warn = "<:warn:1291906735040364604>"
    deny = "<:deny:1291906739876401213>"
    loading = "<a:loading:1301005688545476609>"
    add = "<:add:1301005688545476609>"
    remove = "<:remove:1301005688545476609>"
    wave = ":wave:"
    cooldown = "<:cooldown:1291906737883975751>"
    shazam = "<:shazam:1291906732561272925>"
    juul = "<:juul:1292677353377366016>"
    no_juul = "<:no_juul:1292677354656632993>"
    lastfm = "<:lastfm:1292677355344322622>"
    help = "<:help:1292677356323336212>"
    permissions = "<:permissions:1292677357123336212>"
    notes = ":notepad_spiral:"
    monion = "<:monion:1302331257916493834>"


class LAVALINK:
    NODE_COUNT: int = 1
    HOST: str = "0.0.0.0"
    PORT: int = 2333
    PASSWORD: str = ""


class Authorization:
    class SPOTIFY:
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""
