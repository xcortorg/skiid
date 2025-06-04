from discord.ext.commands import Converter, CommandError
from discord import TextChannel
from yarl import URL

from system.base.context import Context


NSFW_FILTERS = [
    "liveleak",
    "gore",
    "horse",
    "gay",
    "lesbian",
    "sex",
    "kekma",
    "pornhub",
    "xvideos",
    "xhamster",
    "xnxx",
    "eporner",
    "daftsex",
    "hqporner",
    "beeg",
    "yourporn",
    "spankbang",
    "porntrex",
    "xmoviesforyou",
    "porngo",
    "youjizz",
    "motherless",
    "redtube",
    "youporn",
    "pornone",
    "4tube",
    "porntube",
    "3movs",
    "tube8",
    "porndig",
    "cumlouder",
    "txxx",
    "porndoe",
    "pornhat",
    "ok.xxx",
    "porn00",
    "pornhits",
    "goodporn",
    "bellesa",
    "pornhd3x",
    "xxxfiles",
    "pornktube",
    "tubxporn",
    "tnaflix",
    "porndish",
    "fullporner",
    "porn4days",
    "whoreshub",
    "paradisehill",
    "trendyporn",
    "pornhd8k",
    "xfreehd",
    "perfect",
    "girls",
    "porn300",
    "anysex",
    "vxxx",
    "veporn",
    "drtuber",
    "netfapx",
    "letsjerk",
    "pornobae",
    "pornmz",
    "xmegadrive",
    "brazzers3x",
    "pornky",
    "hitprn",
    "porndune",
    "czechvideo",
    "joysporn",
    "watchxxxfree",
    "hdporn92",
    "yespornpleasexxx",
    "reddit",
    "fuxnxx",
    "4kporn",
    "watchporn",
    "plusone8",
    "povaddict",
    "latest",
    "porn",
    "video",
    "inporn",
    "freeomovie",
    "porntop",
    "pornxp",
    "netfapx.net",
    "anyporn",
    "cliphunter",
    "severeporn",
    "collectionofbestporn",
    "coom",
    "onlyfan",
    "xtapes",
    "xkeezmovies",
    "sextvx",
    "yourdailypornvideos",
    "pornovideoshub",
    "pandamovies",
    "palimas",
    "fullxxxmovies",
    "iceporncasting",
    "pussyspace",
    "pornvibe",
    "siska",
    "xxx",
    "scenes",
    "megatube",
    "fakings",
    "tv",
    "justfullporn",
    "xxvideoss",
    "thepornarea",
    "analdin",
    "xozilla",
    "empflix",
    "eroticmv",
    "erome",
    "vidoz8",
    "perverzija",
    "streamporn",
    "pornhoarder",
    "swingerpornfun",
    "thepornfull",
    "pornfeat",
    "pornwex",
    "pornvideobb",
    "secretstash",
    "mangoporn",
    "castingpornotube",
    "fapmeifyoucan",
    "thepervs",
    "latestporn",
    "pornwis",
    "gimmeporn",
    "whereismyporn",
    "pornoflix",
    "tubeorigin",
    "pornez.cam",
    "euroxxx",
    "americass",
    "sextu",
    "yespornvip",
    "galaxyporn",
    "taxi69",
    "fux.com",
    "sexu",
    "definebabe",
    "hutporner",
    "pornseed",
    "titfap",
    "hd-easyporn",
    "dvdtrailertube",
    "chaturbate",
    "xxx",
    "economy-simulator",
    "pikwy",
    "4chan",
    "watchpeople",
]


class DomainConverter(Converter[URL]):
    def __init__(self: "DomainConverter", filter: bool = True):
        self.filter = filter

    async def convert(self: "DomainConverter", ctx: Context, argument: str) -> URL:
        # Clean up the input
        argument = argument.strip().lower()

        # Handle .ss command prefix if present
        if argument.startswith(".ss "):
            argument = argument[4:]

        # Basic validation before processing
        if not argument or len(argument.split()) > 1:
            raise CommandError("Invalid **URL or domain** - didn't pass validation")

        # Prepend 'http://' if the URL doesn't have a scheme
        if not argument.startswith(("http://", "https://")):
            argument = "http://" + argument

        try:
            # Basic URL validation
            parsed = URL(argument)
            if not parsed.host:
                raise ValueError("Invalid host")

            # Validate the domain structure
            host_parts = parsed.host.split(".")
            if len(host_parts) < 2 or not all(part for part in host_parts):
                raise ValueError("Invalid domain structure")

            # NSFW filter check
            if self.filter and (
                isinstance(ctx.channel, TextChannel) and not ctx.channel.nsfw
            ):
                if any(filter in str(parsed) for filter in NSFW_FILTERS):
                    raise CommandError("**NSFW websites** cannot be screenshotted.")

            return parsed

        except (ValueError, TypeError):
            raise CommandError("Invalid **URL or domain** - didn't pass validation")
