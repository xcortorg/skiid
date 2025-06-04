WARP = "socks5://127.0.0.1:7483"
PIPED_API: str = "pipedapi.adminforge.de"


class Mono:
    token = ""
    owner = [0000000000000000000]
    prefix = ";"
    support = "https://discord.gg/server"
    website = "https://website.com"
    docs = "https://docs.website.com"


class Emojis:
    approve = "<:approve:1274155946230153350>"
    warn = "<:warn:1274156062743990343>"
    deny = "<:deny:1274155960058773605>"
    loading = "<a:loading:1274155985149100143>"
    cooldown = "<:cooldown:1274155952655962204>"
    wave = ":wave:"
    shazam = "<:shazam:1291906732561272925>"
    juul = "<:juul:1292677353377366016>"
    no_juul = "<:no_juul:1292677354656632993>"

    class Paginator:
        next = "<:next:1285457501877174303>"
        navigate = "<:navigate:1285457495191719956>"
        previous = "<:previous:1285457511520014371>"
        cancel = "<:cancel:1285457487637647422>"
        trash = "<:trash:1292022991093235851>"
        random = "<:random:1293040572579450951>"

    class Embed:
        approve = "<:approve:1243011306932404356>"
        warn = "<:warn:1243011306932404356>"
        error = "<:error:1243011306932404356>"
        cooldown = "<:cooldown:1243011306932404356>"
        AN_ON = "<:approve:1291906736948641936>"
        AN_OFF = "<:deny:1291906739876401213>"

    class Audio:
        skip: str = "<:skip:1243011308333564006>"
        resume: str = "<:resume:1243011309449252864>"
        repeat: str = "<:repeat:1243011309843382285>"
        previous: str = "<:previous:1243011310942162990>"
        pause: str = "<:pause:1243011311860842627>"
        queue: str = "<:queue:1243011313006022698>"
        repeat_track: str = "<:repeat_track:1243011313660334101>"

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


# help me


class Color:
    neutral = 0x2B2D31
    approve = 0xA5E47A
    warn = 0xF6CA2F
    deny = 0xF86261
    base = 0x2B2D31
    cooldown = 0x4EC3E8
    settings = 0x7289DA
    dark = 0x2B2D31
    shazam = 0x08A8FF


class Database:
    host = "localhost"
    port = 5432
    username = "postgres"
    password = "admin"
    database = "mono"


class Redis:
    db = 0
    host = "localhost"
    port = 6379
    hash = "pTc6Ajf72sHvQvFBf9w3"


class Api:
    GEMINI = ""
    WEATHER = ""
    OPEN_WEATHER = ""
    JEYY: str = ""
    LASTFM: list[str] = [
        "",
        "",
    ]

    class Spotify:
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""

    class Genious:
        client_id: str = ""
        client_secret: str = ""
        client_access_token: str = ""


class Network:
    host = "localhost"
    port = 1339


class Authorization:
    FNBR: str = ""
    CLEVER: str = ""
    WOLFRAM: str = ""
    WEATHER: str = ""
    OSU: str = ""
    LASTFM: list[str] = [
        "",
        "",
    ]
    SOUNDCLOUD: str = ""
    GEMINI: str = ""
    JEYY: str = ""
    KRAKEN: str = ""

    class GOOGLE:
        CX: str = ""
        KEY: str = ""

    class TWITCH:
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""

    class SPOTIFY:
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""

    class REDDIT:
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""

    class INSTAGRAM:
        COOKIES: list[dict] = [
            {
                "ds_user_id": "",
                "sessionid": "",
            },
        ]
        GRAPHQL: list[str] = [
            "",
        ]
