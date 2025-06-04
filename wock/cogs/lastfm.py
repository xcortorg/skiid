import asyncio
from typing import Any, Generator, List, Union

import aiohttp
import discord
import orjson
from discord.ext import commands, menus
from tools.important import Context  # type: ignore
from tools.wock import Wock  # type: ignore


class plural:
    def __init__(self, value: int, bold: bool = False, code: bool = False):
        self.value: int = value
        self.bold: bool = bold
        self.code: bool = code

    def __format__(self, format_spec: str) -> str:
        v = self.value
        if isinstance(v, list):
            v = len(v)
        if self.bold:
            value = f"**{v:,}**"
        elif self.code:
            value = f"`{v:,}`"
        else:
            value = f"{v:,}"

        singular, sep, plural = format_spec.partition("|")  # type: ignore
        plural = plural or f"{singular}s"

        if abs(v) != 1:
            return f"{value} {plural}"

        return f"{value} {singular}"

    def do_plural(self, format_spec: str) -> str:
        v = self.value
        if isinstance(v, list):
            v = len(v)
        if self.bold:
            value = f"**{v:,}**"
        elif self.code:
            value = f"`{v:,}`"
        else:
            value = f"{v:,}"

        singular, sep, plural = format_spec.partition("|")  # type: ignore
        plural = plural or f"{singular}s"

        if abs(v) != 1:
            return f"{value} {plural}"

        return f"{value} {singular}"


def shorten(value: str, length: int = 20):
    if len(value) > length:
        value = value[: length - 2] + (".." if len(value) > length else "").strip()
    return value


def format_duration(duration: Union[int, str], ms: bool = True):
    if isinstance(duration, str):
        duration = int(duration)
    if ms:
        seconds = int((duration / 1000) % 60)
        minutes = int((duration / (1000 * 60)) % 60)
        hours = int((duration / (1000 * 60 * 60)) % 24)
    else:
        seconds = int(duration % 60)
        minutes = int((duration / 60) % 60)
        hours = int((duration / (60 * 60)) % 24)

    if any((hours, minutes, seconds)):
        result = ""
        if hours:
            result += f"{hours:02d}:"
        result += f"{minutes:02d}:"
        result += f"{seconds:02d}"
        return result
    else:
        return "00:00"


def chunk_list(data: list, amount: int) -> list[list]:
    # makes lists of a big list of values every x amount of values
    if len(data) < amount:
        _chunks = [data]
    else:
        chunks = zip(*[iter(data)] * amount)
        _chunks = list(list(_) for _ in chunks)
    from itertools import chain

    l = list(chain.from_iterable(_chunks))  # noqa: E741
    nul = [d for d in data if d not in l]
    if len(nul) > 0:
        _chunks.append(nul)
    return _chunks


def chunks(array: List, chunk_size: int) -> Generator[List, None, None]:
    for i in range(0, len(array), chunk_size):
        yield array[i : i + chunk_size]


class MySource(menus.ListPageSource):
    async def format_page(self, menu, entries):
        if self.get_max_pages() > 1:
            ee = "entries"
        else:
            ee = "entry"
        entries.set_footer(
            text=f"Page {menu.current_page +1}/{self.get_max_pages()}({self.get_max_pages()} {ee})"
        )
        return entries


class DeleteInput(discord.ui.Modal, title="Delete Like"):
    def __init__(self, bot, ctx: Context, data: Any):
        super().__init__()
        self.bot = bot
        self.ctx = ctx
        self.data = data

    playy = discord.ui.TextInput(
        label="Delete", placeholder="Delete a lastfm liked track"
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        song = int(self.playy.value)
        if entry := self.data.get(song):
            await self.bot.db.execute(
                """DELETE FROM lastfm_likes WHERE user_id = $1 AND track = $2 AND artist = $3""",
                self.ctx.author.id,
                entry["track"],
                entry["artist"],
            )
            self.data.pop(song)
            return await interaction.message.edit(
                embeds=[], content="Deleted that lastfm like entry", view=None
            )
        # play track here


class LastFMLikes(discord.ui.View, menus.MenuPages):
    def __init__(self, bot, source, data: Any):
        super().__init__(timeout=60)
        self._source = source
        self.value = 0
        self.data = data
        self.bot = bot
        self.current_page = 0
        self.ctx = None
        self.message = None

    async def start(self, ctx, *, channel=None, wait=False):  # type: ignore # type: ignore
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def on_timeout(self):
        return

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if "view" not in value:
            value.update({"view": self})
        return value

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                ephemeral=True, content="> You **aren't the author** of this command"
            )
        else:
            return interaction.user == self.ctx.author

    @discord.ui.button(
        emoji="<:previous:1110882835167985724>", style=discord.ButtonStyle.grey
    )
    async def before_page(self, interaction, button):  # type: ignore
        if self.current_page == self._source.get_max_pages() - 1:
            return await interaction.response.defer()
        if self.current_page == 0:
            await self.show_page(self._source.get_max_pages() - 1)
        else:
            await self.show_checked_page(self.current_page - 1)
        # await interaction.response.defer()

    @discord.ui.button(
        emoji="<:next:1110882794416132197>", style=discord.ButtonStyle.grey
    )
    async def next_page(self, interaction, button):  # type: ignore
        if self.current_page == self._source.get_max_pages() - 1:
            return await interaction.response.defer()
        if self.current_page == self._source.get_max_pages() - 1:
            await self.show_page(0)
        else:
            await self.show_checked_page(self.current_page + 1)

    @discord.ui.button(
        emoji="<:stop:1110883418708901928>", style=discord.ButtonStyle.grey
    )
    async def delete(self, interaction, button):  # type: ignore
        return await interaction.response.send_modal(
            DeleteInput(self.bot, self.ctx, self.data)
        )


class LastFMHTTPRequester:
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"

    def __init__(self, **kwargs):
        self.api_key = kwargs.get("api_key")

    async def get(self, **params):
        params["api_key"] = self.api_key
        params["format"] = "json"
        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as resp:
                return await resp.json()


class LastFM(commands.Cog):
    def __init__(self, bot: Wock):
        self.bot = bot
        self.requester = LastFMHTTPRequester(api_key="260c08af4a7f26f90743f66637572031")
        self.vars = [
            "{track}: Name of the track.",
            "{artist}: Name of the artist.",
            "{user}: Username of the author.",
            "{avatar}: URL of the author's avatar.",
            "{track.url}: URL of the track.",
            "{artist.url}: URL of the artist.",
            "{scrobbles}: Number of scrobbles for the user.",
            "{track.image}: Image associated with the track.",
            "{username}: Last.FM Username.",
            "{artist.plays}: Number of plays for the artist.",
            "{track.plays}: Number of plays for the track.",
            "{track.lower}: Lowercase name of the track.",
            "{artist.lower}: Lowercase name of the artist.",
            "{track.hyperlink}: Hyperlink to the track with the track name as the text.",
            "{track.hyperlink_bold}: Hyperlink to the track with bold track name as the text.",
            "{artist.hyperlink}: Hyperlink to the artist with the artist name as the text.",
            "{artist.hyperlink_bold}: Hyperlink to the artist with bold artist name as the text.",
            "{track.color}: Dominant color of the track image.",
            "{artist.color}: Dominant color of the artist image.",
            "{date}: Date the track was played on.",
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not await self.bot.glory_cache.ratelimited(
            f"rl:lastfm_customcommand:{message.author.id}", 2, 5
        ) and (
            data := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.command WHERE user_id = $1", message.author.id
            )
        ):
            command = data.command
            if command:
                if message.content == command:
                    ctx = await self.bot.get_context(message)
                    async with ctx.typing():
                        await ctx.invoke(
                            self.bot.get_command("fm np"), user=message.author
                        )

    @commands.hybrid_group(
        name="lastfm",
        aliases=["fm", "lf"],
        invoke_without_command=True,
        with_app_command=True,
        brief="List of commands for lastfm",
        example=",lastfm",
    )
    async def lastfm(self, ctx):  # type: ignore
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command)

    @lastfm.command(
        name="set",
        aliases=["link"],
        brief="Link a LastFM account to your user",
        example=",lastfm set ante_dev",
    )
    async def set(self, ctx: Context, *, username: str):
        if await self.bot.redis.get(f"lfindex:{ctx.author.id}"):
            return await ctx.fail("You are already setting your last.fm username.")
        req = await self.bot.session.get(f"https://www.last.fm/user/{username}")
        if req.status == 404:
            return await ctx.fail("Invalid username.")

        await self.bot.db.execute(
            "INSERT INTO lastfm.conf VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO UPDATE SET username = $2",
            ctx.author.id,
            username,
            "👍",
            "👎",
        )
        artists, tracks = await asyncio.gather(
            *[
                self.requester.get(method="user.gettopartists", user=username),
                self.requester.get(method="user.gettoptracks", user=username),
            ]
        )
        if artists:
            records = [
                {"name": artist["name"], "plays": int(artist["playcount"])}
                for artist in artists["topartists"]["artist"]
            ]
            await self.bot.db.execute(
                "INSERT INTO lastfm.users (user_id, username, artists) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET artists = $3",
                ctx.author.id,
                username,
                orjson.dumps(records).decode(),
            )
        if tracks:
            records = [
                {"name": track["name"], "plays": int(track["playcount"])}
                for track in tracks["toptracks"]["track"]
            ]
            await self.bot.db.execute(
                "INSERT INTO lastfm.users (user_id, username, tracks) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET tracks = $3",
                ctx.author.id,
                username,
                orjson.dumps(records).decode(),
            )
        return await ctx.success(f"**last.fm username** set to `{username}`")

    @lastfm.command(
        name="refresh", brief="Refresh your lastFM data", example=",lastfm refresh"
    )
    async def lastfm_refresh(self, ctx: Context):
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
            )
        ):
            return await ctx.fail("You do **not** have a Last.FM account linked.")
        artists, tracks = await asyncio.gather(
            *[
                self.requester.get(method="user.gettopartists", user=conf.username),
                self.requester.get(method="user.gettoptracks", user=conf.username),
            ]
        )
        total_pages = int(artists["topartists"]["@attr"]["totalPages"])
        if artists:
            records = [
                {"name": artist["name"], "plays": int(artist["playcount"])}
                for artist in artists["topartists"]["artist"]
            ]
            if total_pages > 1:
                tasks = []
                for i in range(2, total_pages + 1):
                    tasks.append(
                        self.requester.get(
                            method="user.gettopartists", user=conf.username, page=i
                        )
                    )
                data = await asyncio.gather(*tasks)
                for d in data:
                    rec2 = [
                        {"name": artist["name"], "plays": int(artist["playcount"])}
                        for artist in d["topartists"]["artist"]
                    ]
                    records.extend(rec2)
                    del rec2
            await self.bot.db.execute(
                "INSERT INTO lastfm.users (user_id, username, artists) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET artists = $3",
                ctx.author.id,
                conf.username,
                orjson.dumps(records).decode(),
            )
        if tracks:
            records = [
                {"name": track["name"], "plays": int(track["playcount"])}
                for track in tracks["toptracks"]["track"]
            ]
            total_track_pages = int(tracks["toptracks"]["@attr"]["totalPages"])
            if total_track_pages > 1:
                tasks = []
                for i in range(2, total_track_pages + 1):
                    tasks.append(
                        self.requester.get(
                            method="user.gettoptracks", user=conf.username, page=i
                        )
                    )
                data = await asyncio.gather(*tasks)
                for d in data:
                    rec2 = [
                        {"name": track["name"], "plays": int(track["playcount"])}
                        for track in d["toptracks"]["track"]
                    ]
                    records.extend(rec2)
                    del rec2

            await self.bot.db.execute(
                "INSERT INTO lastfm.users (user_id, username, tracks) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET tracks = $3",
                ctx.author.id,
                conf.username,
                orjson.dumps(records).decode(),
            )
        return await ctx.success("**Refreshed** your last.fm data")

    @lastfm.command(
        name="nowplaying",
        aliases=["np"],
        brief="Show what song is currently playing through your linked LastFM account",
        example=",lastfm nowplaying",
    )
    async def nowplaying(self, ctx: Context, *, user: discord.Member = None):
        if user is None:
            user = ctx.author
        #  if hasattr(self.bot, "node"):
        #     if player := self.bot.node.get_player(ctx.guild.id):
        #        if player.current:
        #           if user in player.channel.members:
        #              embed = discord.Embed(
        #                 title=f"Currently playing..", color=0x2B2D31
        #            )
        #           embed.description = f"> **Duration:** `{format_duration(player.position)}/{format_duration(player.current.length)}`\n> **Playing:** [**{shorten(player.current.title, 23)}**]({player.current.uri})\n> **Requested by:** {player.current.requester.mention}\n"
        #          return await ctx.send(embed=embed)
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", user.id
            )
        ):
            return await ctx.fail("**User has not set their last.fm username**")

        data = await self.requester.get(
            method="user.getrecenttracks", user=conf.username
        )
        custom_embed = await self.bot.db.fetchrow(
            "SELECT * FROM lastfm.ce WHERE user_id = $1", user.id
        )
        if "error" in data:
            return await ctx.fail("Invalid username.")

        track, uzar = await asyncio.gather(
            *[
                self.requester.get(method="user.getrecenttracks", user=conf.username),
                self.requester.get(method="user.getinfo", user=conf.username),
            ]
        )

        if not track:
            return await ctx.send("No recent tracks found.")
        track_data = track["recenttracks"]["track"][0]
        artist = track_data["artist"]["#text"]
        uzr = uzar["user"]
        eggstra = await self.requester.get(
            method="track.getInfo", artist=artist, track=track_data["name"]
        )
        track_data["extra"] = eggstra["track"]
        artistUrl = f"https://last.fm/music/{artist.replace(' ', '')}"
        #    await ctx.send(track_data['name'])
        try:
            duration = int(eggstra["track"]["duration"])
        except Exception:
            duration = 0
        if custom_embed:
            lastfm_data = {
                "track": track_data["name"],
                "artist": artist,
                "user": uzr["name"],
                "duration": format_duration(duration),
                "avatar": uzr["image"][-1]["#text"],
                "track.url": track_data["url"] or None,
                "artist.url": f"https://last.fm/music/{artist.replace(' ', '')}",
                "scrobbles": uzr["playcount"],
                "track.image": track_data["image"][-1]["#text"],
                "username": conf.username,
                "artist.plays": track_data.get("extra", {})
                .get("artist", {})
                .get("playcount", 0),
                "track.plays": track_data.get("extra", {}).get("userplaycount", 0),
                # "artist.plays": track_data["extra"]["artist"]["playcount"],
                # "track.plays": track_data["extra"]["userplaycount"],
                "track.lower": track_data["name"].lower(),
                "artist.lower": artist.lower(),
                "track.hyperlink": f"[{track_data['name']}]({track_data['url']})",
                "track.hyperlink_bold": f"[**{track_data['name']}**]({track_data['url']})",
                "artist.hyperlink": f"[{artist}]({artistUrl})",
                "artist.hyperlink_bold": f"[**{artist}**]({artistUrl})",
                # "date": track_data["date"]["#text"]
            }
            # builder = EmbedBuilder(user, lastfm_data)
            # code = await builder.replace_placeholders(custom_embed["msg"])
            m = await self.bot.send_embed(
                ctx.channel, custom_embed["msg"], user=user, lastfm_data=lastfm_data
            )
            reactions = [conf.up, conf.down] or ["👍", "👎"]
            await self.bot.redis.set(
                f"lfnp:{m.id}",
                orjson.dumps(
                    {
                        "up": str(reactions[0]),
                        "down": str(reactions[1]),
                        "track": track_data["name"],
                        "artist": artist,
                    }
                ),
                ex=10000,
            )
            return await asyncio.gather(*[m.add_reaction(r) for r in reactions])
            # return await ctx.send(**embed)
            # m = await ctx.send(**embed)
            # reacts = [conf.up, conf.down] or ["👍", "👎"]
            # for reaction in reacts:
            # await m.add_reaction(reaction)
        else:
            embed = discord.Embed()
            embed.set_author(
                url=uzr["url"],
                name=f"{uzr['name']} ",
                icon_url=uzr["image"][-1]["#text"],
            )
            try:
                thumbnail_url = track_data["image"][-1]["#text"]
                embed.set_thumbnail(url=thumbnail_url)
            except KeyError:
                # No thumbnail available, so remove the thumbnail field
                pass

            embed.add_field(
                name="Track",
                value=f"** [{track_data['name']}]({track_data['url']}) ** - [{artist}]({artistUrl})",
            )
            embed.set_footer(
                text=(
                    f"Album: {track_data['album']['#text']}\nScrobbles: {uzr['playcount']}"
                )
            )
            m = await ctx.send(embed=embed)
            reacts = [conf.up, conf.down] or ["👍", "👎"]
            await self.bot.redis.set(
                f"lfnp:{m.id}",
                orjson.dumps(
                    {
                        "up": reacts[0],
                        "down": reacts[1],
                        "track": track_data["name"],
                        "artist": artist,
                    }
                ),
            )
            return await asyncio.gather(*[m.add_reaction(r) for r in reacts])

    @lastfm.command(
        name="reaction",
        aliases=["react", "reacts"],
        brief="Set a Custom reaction like and dislike for your LastFM embed",
        example=",lastfm reaction :thumbsup::skin-tone-2: :thumbsdown::skin-tone-2: ",
    )
    async def lastfm_react(self, ctx: Context, up: str = None, down: str = None):
        if up is None and down is None or up.lower() in ["reset", "clear", "disable"]:
            await self.bot.db.execute(
                """UPDATE lastfm.conf SET up = $1, down = $2 WHERE user_id = $3""",
                None,
                None,
                ctx.author.id,
            )
            return await ctx.success("**Reset** your **last.fm reactions**")
        if up is not None and down is not None:
            await self.bot.db.execute(
                "UPDATE lastfm.conf SET up = $1, down = $2 WHERE user_id = $3",
                up,
                down,
                ctx.author.id,
            )
            return await ctx.success(
                f"**Set** your **last.fm reactions** to {up} and {down}"
            )

    @lastfm.command(
        name="variables",
        brief="View all of the LastFM custom embed variables",
        example=",lastfm variables",
    )
    async def lastfm_vars(self, ctx: Context):
        embeds = []
        if not await self.bot.db.fetchrow(
            "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
        ):
            return await ctx.success(
                f"**Set your LastFM username** via `{ctx.prefix}fm set`"
            )

        for i, p in enumerate(chunks(self.vars, 10), start=1):
            embeds.append(
                discord.Embed(
                    title="LastFM Variables",
                    description="\n".join(
                        f"> `{i}.` **{item}**"
                        for i, item in enumerate(p, start=(i - 1) * 10 + 1)
                    ),
                    color=0x2B2D31,
                )
            )
        return await ctx.paginate(embeds)

    @lastfm.group(
        name="embed",
        aliases=["customembed"],
        invoke_without_command=True,
        brief="Create a custom embed for your lastfm now playing command",
        example=",lastfm embed {embed code}",
    )
    async def lastfm_embed(self, ctx: Context, *, code: str) -> discord.Embed:
        if not await self.bot.db.fetchrow(
            "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
        ):
            return await ctx.fail("You do **not** have a **Last.FM account linked**")

        if code in ["clear", "reset", "delete", "remove"]:
            await self.bot.db.execute(
                "DELETE FROM lastfm.ce WHERE user_id = $1", ctx.author.id
            )
            return await ctx.success("**Reset** your custom Last.FM embed.")

        if code in ["view", "current", "show"]:
            embed_code = await self.bot.db.fetchval(
                "SELECT msg FROM lastfm.ce WHERE user_id = $1", ctx.author.id
            )

            return await ctx.reply(
                embed=discord.Embed(description=f"```{embed_code}```")
            )

        await self.bot.db.execute(
            "INSERT INTO lastfm.ce (user_id, msg) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET msg = $2",
            ctx.author.id,
            code,
        )

        return await ctx.success("**set** your **custom Last.FM embed**")

    @lastfm_embed.command(
        name="view",
        aliases=["current", "show"],
        brief="View your lastfm custom embed code",
        example=",lastfm embed view",
    )
    async def lastfm_embed_view(self, ctx: Context):
        if embed_code := await self.bot.db.fetchval(
            "SELECT msg FROM lastfm.ce WHERE user_id = $1", ctx.author.id
        ):
            return await ctx.normal(f"```{embed_code}```")
        return await ctx.fail("You do **not** have a **custom Last.FM embed**")

    @lastfm.command(
        name="customcommand",
        aliases=["cc", "custom"],
        brief="Set a custom command for your lastfm command",
        example=",lastfm customcommand ante",
    )
    async def lastfm_customcommand(self, ctx: Context, *, command: str):
        if not await self.bot.db.fetchrow(
            "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
        ):
            return await ctx.fail("You do **not** have a **Last.FM account linked**")

        if command in ["clear", "reset", "delete", "remove"]:
            await self.bot.db.execute(
                "DELETE FROM lastfm.command WHERE user_id = $1", ctx.author.id
            )
            return await ctx.success("**Reset** your **custom Last.FM command**")

        await self.bot.db.execute(
            "INSERT INTO lastfm.command (user_id, command) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET command = $2",
            ctx.author.id,
            command,
        )
        return await ctx.success(
            f"**Set** your **custom Last.FM command** to `{command}`"
        )

    @lastfm.command(
        name="artist",
        aliases=["a"],
        brief="View information on a music artist through lastfm",
        example=",lastfm artist Juice Wrld",
    )
    async def lastfm_artist(self, ctx: Context, *, artist: str = None):
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
            )
        ):
            return await ctx.fail("You do **not** have a **Last.FM account linked**")

        if not artist:
            data = (
                await self.requester.get(
                    method="user.getrecenttracks", user=conf.username
                ),
            )
            track_data = data[0]["recenttracks"]["track"][0]
            artist = track_data["artist"]["#text"]
        data = await self.requester.get(method="artist.getinfo", artist=artist)
        if "error" in data:
            return await ctx.fail("Invalid artist.")

        artist_data = data["artist"]
        embed = discord.Embed(
            title=artist_data["name"],
            description=artist_data["bio"]["summary"],
            color=0x2B2D31,
        )
        embed.set_thumbnail(url=artist_data["image"][-1]["#text"])
        embed.set_footer(
            text=f'Listeners: {artist_data["stats"]["listeners"]} | Plays: {artist_data["stats"]["playcount"]}'
        )
        return await ctx.send(embed=embed)

    async def get_or_fetch(self, user_id: int) -> str:
        if user := self.bot.get_user(user_id):
            return user.global_name or user.name
        else:
            user = await self.bot.fetch_user(user_id)
            return user.global_name or user.name

    @lastfm.command(
        name="steal",
        aliases=["swipe"],
        brief="steal someone elses custom embed code",
        example=",lastfm steal @o_5v",
    )
    async def lastfm_steal(self, ctx: Context, user: discord.Member = commands.Author):
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", user.id
            )
        ):
            return await ctx.fail(
                "This user does **not** have a **Last.FM account linked**"
            )

        if not (
            custom_embed := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.ce WHERE user_id = $1", user.id
            )
        ):
            return await ctx.fail("User does **not** have a **custom Last.FM embed**")

        await self.bot.db.execute(
            "INSERT INTO lastfm.ce (user_id, msg) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET msg = $2",
            ctx.author.id,
            custom_embed["msg"],
        )
        return await ctx.success(f"**Swiped {user.mention}'s custom Last.FM embed**")

    async def recents_extractor(self, ctx: Context, configs: Any):  # type: ignore
        data = await asyncio.gather(
            *[
                self.requester.get(method="user.getrecenttracks", user=c.username)
                for c in configs
            ]
        )
        nulled = 0
        rows = []
        data = [
            {"username": conf.username, "user_id": conf.user_id, "data": item}
            for conf, item in zip(configs, data)
        ]
        for i, item in enumerate(data, start=1):
            if not item["data"].get("recenttracks"):
                nulled += 1
                continue
            else:
                rows.append(
                    f"> `{i-nulled}` [**{await self.get_or_fetch(item['user_id'])}**](https://last.fm/{item['username']}) - **{item['data']['recenttracks']['track'][0]['name']}**"
                )
        return rows

    @lastfm.command(
        name="recents",
        brief="View what songs were recently listened to in the server",
        example=",lastfm recents",
    )
    async def lastfm_recents(self, ctx: Context):
        configs = await self.bot.db.fetch(
            """SELECT * FROM lastfm.conf WHERE user_id = any($1::bigint[])""",
            [user.id for user in ctx.guild.members],
        )
        if not configs:
            return await ctx.fail("No Last.FM accounts found.")
        rows = await self.recents_extractor(ctx, configs)
        embed = discord.Embed(
            title="Recent tracks",
            color=0x2B2D31,
        )
        return await self.bot.dummy_paginator(ctx, embed, rows, 10)

    @lastfm.command(
        name="mostcrowns",
        brief="View users with the most crowns",
        example=",lastfm mostcrowns",
    )
    async def lastfm_mostcrowns(self, ctx: Context):
        data = await self.bot.db.fetch(
            """SELECT guild_id, user_id, artist, count(*) as plays FROM lastfm_crowns  WHERE guild_id = $1 AND user_id = any($2::bigint[]) GROUP BY guild_id, user_id, artist ORDER BY plays DESC""",
            ctx.guild.id,
            [user.id for user in ctx.guild.members],
        )
        data = [
            {
                "user_id": item["user_id"],
                "artist": item["artist"],
                "plays": item["plays"],
            }
            for item in data
        ]
        data = sorted(data, key=lambda x: x["plays"], reverse=True)
        if not data:
            return await ctx.fail("**No crowns found**")
        rows = [
            f"> `{i}.` **[{await self.get_or_fetch(item['user_id'])}](https://www.last.fm/user/{item['user_id']}) - {item['plays']} plays{' 👑' if i == 1 else ''}**"
            for i, item in enumerate(data, start=1)
        ]
        embed = discord.Embed(
            title="Most crowns",
            color=0x2B2D31,
        )
        return await self.bot.dummy_paginator(ctx, embed, rows, 10)

    @lastfm.command(
        "whoknows",
        brief="Shows what other users listen to the current track in your server",
        aliases=["similar", "wk"],
        example=",lastfm whoknows Juice Wrld",
    )
    async def lastfm_crowns(self, ctx: Context, *, artist_name: str = None):
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
            )
        ):
            return await ctx.fail("You do **not** have a **Last.FM account linked**")

        if not artist_name:
            data = await self.requester.get(
                method="user.getrecenttracks", user=conf.username
            )
            if "error" in data or not data["recenttracks"]["track"]:
                return await ctx.fail("Invalid username or no recent tracks.")
            artist_name = data["recenttracks"]["track"][0]["artist"]["#text"]

        data = [
            {
                "username": await self.get_or_fetch(int(user_id)),
                "user_id": int(user_id),
                "user": user,
                "artist": artist,
                "plays": plays,
            }
            for user_id, user, artist, plays in await self.bot.db.fetch(
                "SELECT user_id, username, artists, tracks FROM lastfm.users WHERE user_id = any($1::bigint[])",
                [user.id for user in ctx.guild.members],
            )
        ]
        for i in data:
            i["artists"] = orjson.loads(i["artist"])
            i["plays"] = sum(
                [
                    artist["plays"]
                    for artist in i["artists"]
                    if artist["name"].lower() == artist_name.lower()
                ]
            )
        data = [item for item in data if item["plays"] > 0]
        data = sorted(data, key=lambda x: x["plays"], reverse=True)
        if len(data) > 0:
            await self.bot.db.execute(
                """INSERT INTO lastfm_crowns (guild_id, artist, user_id, plays) VALUES($1,$2,$3,$4) ON CONFLICT(guild_id, artist) DO UPDATE SET user_id = $3, plays = $4""",
                ctx.guild.id,
                artist_name,
                data[0]["user_id"],
                data[0]["plays"],
            )
        embeds = []
        for i, p in enumerate(chunks(data, 10), start=1):
            description = "\n".join(
                f"> `{i}.` **[{item['username']}](https://www.last.fm/user/{item['user']}) - {item['plays']} plays{' 👑' if i == 1 else ''}**"
                for i, item in enumerate(p, start=(i - 1) * 10 + 1)
            )
            embeds.append(
                discord.Embed(
                    title=f"{artist_name} most plays",
                    description=description,
                    color=0x2B2D31,
                )
            )
        return await ctx.paginate(embeds)


async def setup(bot):
    await bot.add_cog(LastFM(bot))
