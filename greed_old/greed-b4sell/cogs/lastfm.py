import asyncio
import datetime
from typing import Generator, List
from PIL import Image
from io import BytesIO
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import aiohttp
from io import BytesIO
import discord
import orjson
from discord.ext import commands, menus
from typing import Any, Union
from tool.important import Context  # type: ignore
from tool.greed import Greed  # type: ignore
from tool.emotes import EMOJIS
from PIL import ImageDraw, ImageFont
from tool.worker import offloaded
import requests
from PIL import ImageOps
import hashlib
import urllib.parse
from config import Authorization


@offloaded
def generate_collage(track_info):
    size = 300
    collage_size = 900
    padding = 2
    text_height = 20

    total_size = collage_size + padding * 4
    collage = Image.new("RGB", (total_size, total_size), color="black")

    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except:
        try:
            font_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]  # Linux
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, 15)
                    break
                except:
                    continue
        except:
            font = ImageFont.load_default()

    with requests.Session() as session:
        for i, info in enumerate(track_info):
            try:
                x = (i % 3) * (size + padding) + padding
                y = (i // 3) * (size + padding) + padding

                response = session.get(info["url"], timeout=5)
                if response.status_code == 200:
                    try:
                        image_data = BytesIO(response.content)
                        img = Image.open(image_data).convert("RGB")

                        img_w, img_h = img.size
                        ratio = min(size / img_w, size / img_h)
                        new_size = (int(img_w * ratio), int(img_h * ratio))

                        img = img.resize(new_size, Image.Resampling.LANCZOS)

                        new_img = Image.new("RGB", (size, size), "black")
                        paste_x = (size - new_size[0]) // 2
                        paste_y = (size - new_size[1]) // 2
                        new_img.paste(img, (paste_x, paste_y))

                        collage.paste(new_img, (x, y))

                        draw = ImageDraw.Draw(collage)
                        text = f"{shorten(info['title'], 30)} {info['plays']}"

                        text_width = draw.textlength(text, font=font)
                        text_x = x + (size - text_width) / 2
                        text_y = y + size - text_height - 5

                        bg_padding = 6
                        draw.rectangle(
                            [
                                text_x - bg_padding,
                                text_y - bg_padding / 2,
                                text_x + text_width + bg_padding,
                                text_y + text_height + bg_padding / 2,
                            ],
                            fill="black",
                        )

                        outline_color = "black"
                        for adj in range(-1, 2):
                            for adj2 in range(-1, 2):
                                draw.text(
                                    (text_x + adj, text_y + adj2),
                                    text,
                                    font=font,
                                    fill=outline_color,
                                )
                        draw.text((text_x, text_y), text, font=font, fill="white")

                    except Exception as e:
                        print(f"Error processing image {i}: {e}")
                        draw = ImageDraw.Draw(collage)
                        draw.rectangle(
                            [x, y, x + size, y + size],
                            fill="#2F3136",
                            outline="#202225",
                        )

            except Exception as e:
                print(f"Error fetching image {i}: {e}")
                draw = ImageDraw.Draw(collage)
                draw.rectangle(
                    [x, y, x + size, y + size], fill="#2F3136", outline="#202225"
                )

    try:
        final_collage = ImageOps.expand(collage, border=2, fill="#202225")

        output = BytesIO()
        final_collage.save(output, format="PNG", quality=95, optimize=True)
        output.seek(0)
        return output
    except Exception as e:
        print(f"Error in final processing: {e}")
        return None


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

    async def start(self, ctx, *, channel=None, wait=False):  # type: ignore
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

    @discord.ui.button(emoji=EMOJIS["pages_previous"], style=discord.ButtonStyle.grey)
    async def before_page(self, interaction, button):  # type: ignore
        if self.current_page == self._source.get_max_pages() - 1:
            return await interaction.response.defer()
        if self.current_page == 0:
            await self.show_page(self._source.get_max_pages() - 1)
        else:
            await self.show_checked_page(self.current_page - 1)
        # await interaction.response.defer()

    @discord.ui.button(emoji=EMOJIS["next"], style=discord.ButtonStyle.grey)
    async def next_page(self, interaction, button):  # type: ignore
        if self.current_page == self._source.get_max_pages() - 1:
            return await interaction.response.defer()
        if self.current_page == self._source.get_max_pages() - 1:
            await self.show_page(0)
        else:
            await self.show_checked_page(self.current_page + 1)

    @discord.ui.button(emoji=EMOJIS["stop"], style=discord.ButtonStyle.grey)
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


class LastFMLoginView(discord.ui.View):
    def __init__(self, ctx, username=None):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.username = username
        self.value = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        try:
            await self.message.edit(view=self)
        except:
            pass

    @discord.ui.button(label="OAuth Login", style=discord.ButtonStyle.green)
    async def oauth_login(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                "This is not your login choice.", ephemeral=True
            )

        self.value = "oauth"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Username Only", style=discord.ButtonStyle.gray)
    async def username_only(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                "This is not your login choice.", ephemeral=True
            )

        self.value = "username"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                "This is not your login choice.", ephemeral=True
            )

        self.value = "cancel"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class LastFM(commands.Cog):
    def __init__(self, bot: Greed):
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
        if message.author.bot:
            return
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
                            self.bot.get_command("lf np"), user=message.author
                        )

    @commands.hybrid_group(
        name="lastfm",
        aliases=["lf"],
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
        example=",lastfm set yurrion",
    )
    async def set(self, ctx: Context, *, username: str = None):
        if username is None:
            return await ctx.fail("Please provide a LastFM username.")

        if await self.bot.redis.get(f"lfindex:{ctx.author.id}"):
            return await ctx.fail("You are already setting your last.fm username.")

        # Validate username first
        req = await self.bot.session.get(f"https://www.last.fm/user/{username}")
        if req.status == 404:
            return await ctx.fail("Invalid username.")

        # Create and send the confirmation view
        embed = discord.Embed(
            title="LastFM Login Options",
            description=(
                "Please choose how you want to connect your LastFM account:\n\n"
                "**OAuth Login**: Full integration with LastFM. This allows:\n"
                "• Scrobbling tracks while playing music in voice channels\n"
                "• Loving/unloving tracks directly from Discord\n"
                "• Access to more LastFM features\n\n"
                "**Username Only**: Basic integration. Only allows viewing your LastFM stats."
            ),
            color=0x2B2D31,
        )

        view = LastFMLoginView(ctx, username)
        view.message = await ctx.send(embed=embed, view=view)

        await view.wait()

        if view.value == "cancel":
            return await ctx.fail("LastFM setup cancelled.")
        elif view.value == "oauth":
            return await self.lastfm_login_cmd(ctx)
        elif view.value == "username":
            if session_key := await self.bot.db.fetchval(
                "SELECT session_key FROM lastfm.conf WHERE user_id = $1", ctx.author.id
            ):
                await self.bot.db.execute(
                    "UPDATE lastfm.conf SET session_key = NULL WHERE user_id = $1",
                    ctx.author.id,
                )
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
            await self.bot.redis.set(f"lfindex:{ctx.author.id}", "1", ex=60)
            await ctx.success(
                f"Successfully set your Last.fm username to **{username}**."
            )

            try:
                await self.index_user(ctx.author.id, artists, tracks)
                await self.bot.redis.delete(f"lfindex:{ctx.author.id}")
            except Exception as e:
                await self.bot.redis.delete(f"lfindex:{ctx.author.id}")
                await ctx.fail(f"Failed to index your Last.fm data: {e}")

    @lastfm.command(
        name="login", brief="Login to LastFM using OAuth", example=",lastfm login"
    )
    async def lastfm_login_cmd(self, ctx: Context):
        """Login to LastFM using OAuth authentication"""
        try:
            if not hasattr(Authorization, "LastFM"):
                return await ctx.fail(
                    "LastFM authorization is not properly configured."
                )
            tracking_id = hashlib.md5(
                f"{ctx.author.id}{datetime.datetime.now().timestamp()}".encode()
            ).hexdigest()

            # Store tracking ID in Redis with a 30-minute expiration
            await self.bot.redis.set(
                f"lastfm:auth:{tracking_id}",
                str(ctx.author.id),
                ex=1800,  # 30 minutes expiration
            )

            callback_url = f"{Authorization.LastFM.cb_url}?tracking_id={tracking_id}"

            auth_url = (
                f"https://www.last.fm/api/auth/?"
                f"api_key={Authorization.LastFM.api_key}&"
                f"cb={urllib.parse.quote(callback_url)}"
            )

            embed = discord.Embed(
                title="LastFM Authentication",
                description=(
                    f"Click [here]({auth_url}) to authenticate with LastFM\n\n"
                ),
                color=0x2B2D31,
            )

            try:
                await ctx.author.send(embed=embed)
                return await ctx.success("Check your DMs for the login link!")
            except discord.Forbidden:
                return await ctx.fail(
                    "I couldn't send you a DM. Please enable DMs from server members."
                )

        except Exception as e:
            return await ctx.fail(f"An error occurred: {str(e)}")

    @lastfm.command(
        name="refresh", brief="Refresh your lastFM data", example=",lastfm refresh"
    )
    async def lastfm_refresh(self, ctx: Context):
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
            )
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )
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
        aliases=["fm", "np"],
        brief="Show what song is currently playing through your linked LastFM account",
        example=",lastfm nowplaying",
    )
    async def nowplaying(self, ctx: Context, *, user: discord.Member = None):
        if user is None:
            user = ctx.author

        # Check if the user is in a voice channel and scrobbling
        if user.voice and user.voice.channel:
            music_events = self.bot.get_cog("MusicEvents")
            if music_events and hasattr(music_events, "lastfm_now_playing_users"):
                guild_id = ctx.guild.id
                if (
                    guild_id in music_events.lastfm_now_playing_users
                    and user.id in music_events.lastfm_now_playing_users[guild_id]
                ):
                    # User is in a voice channel and scrobbling, redirect to queue nowplaying
                    music_commands = self.bot.get_cog("MusicCommands")
                    if music_commands and hasattr(music_commands, "queue_nowplaying"):
                        return await music_commands.queue_nowplaying(ctx)

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
            return await ctx.fail("No recent tracks found.")
        if not track["recenttracks"]["track"]:
            return await ctx.fail("No recent tracks found.")
        track_data = track["recenttracks"]["track"][0]
        artist = track_data["artist"]["#text"]
        uzr = uzar["user"]
        eggstra = await self.requester.get(
            method="track.getInfo", artist=artist, track=track_data["name"]
        )
        track_data["extra"] = eggstra.get("track", {})
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
            return await asyncio.gather(
                *[m.add_reaction(r) for r in reacts if r is not None]
            )

    @lastfm.command(
        name="collage",
        aliases=["lc"],
        brief="Generate a Last.FM collage",
        example=",lastfm collage [timespan]",
    )
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def lastfm_recentartists(
        self, ctx: commands.Context, timespan: str = "overall"
    ):
        user = ctx.author
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", user.id
            )
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

        period_map = {
            "7d": "7day",
            "1m": "1month",
            "3m": "3month",
            "6m": "6month",
            "1y": "12month",
            "overall": "overall",
            "lifetime": "overall",
            "alltime": "overall",
        }

        period = period_map.get(timespan.lower(), "overall")

        if period not in period_map.values():
            return await ctx.fail(
                "Invalid timespan. Valid options are 7d, 1m, 3m, 6m, 1y, and lifetime."
            )

        data = await self.requester.get(
            method="user.gettoptracks",
            user=conf.username,
            limit=9,  # Only request what we need
            period=period,
        )
        message = await ctx.normal("Generating collage...")

        if "error" in data:
            return await ctx.fail("Invalid username.")

        tracks = data.get("toptracks", {}).get("track", [])
        if not tracks:
            return await ctx.fail("No tracks found for this timespan.")

        default_image_url = "https://images-ext-1.discordapp.net/external/YawEMwFRVUV20mHDlBf8IXRcqTOUbOGcUwUfmeYIsww/https/lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png"

        # Process tracks directly from the top tracks response
        track_info = []
        for track in tracks[:9]:  # Limit to 9 tracks
            # Get album info to fetch higher quality images
            album_data = await self.requester.get(
                method="track.getInfo",
                track=track["name"],
                artist=track["artist"]["name"],
                username=conf.username,
            )

            # Try to get image from album info first, then fallback to track images
            image_url = None
            if "track" in album_data and "album" in album_data["track"]:
                images = album_data["track"]["album"].get("image", [])
                image_url = next(
                    (
                        img.get("#text")
                        for img in images
                        if img.get("size") == "large" and img.get("#text")
                    ),
                    None,
                )

            if not image_url:
                image_url = next(
                    (
                        img.get("#text")
                        for img in track.get("image", [])
                        if img.get("size") == "large" and img.get("#text")
                    ),
                    None,
                )

            track_info.append(
                {
                    "url": image_url or default_image_url,
                    "title": f"{track['artist']['name']} - {track['name']}",
                    "plays": f"({track['playcount']} plays)",
                }
            )

        # Fill remaining slots if needed
        while len(track_info) < 9:
            track_info.append(
                {"url": default_image_url, "title": "No track", "plays": ""}
            )

        # Generate the collage with text
        collage = await generate_collage(track_info)
        file = discord.File(collage, "top_tracks_collage.png")

        timespan_display = (
            timespan.lower() if timespan.lower() != "overall" else "all time"
        )
        embed = discord.Embed(
            title=f"{user.display_name}'s Top Tracks - {timespan_display}",
            color=0x2B2D31,
        ).set_image(url="attachment://top_tracks_collage.png")

        await message.edit(content=None, attachments=[file], embed=embed)

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
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

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
        example=",lastfm customcommand sudosql",
    )
    async def lastfm_customcommand(self, ctx: Context, *, command: str):
        if not await self.bot.db.fetchrow(
            "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

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
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

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
        example=",lastfm steal @sudosql",
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

    @lastfm.group(
        name="whoknows",
        brief="Shows what other users listen to the current track in your server",
        aliases=["similar", "wk"],
        example=",lastfm whoknows Juice Wrld",
        invoke_without_command=True,
    )
    async def lastfm_whoknows(self, ctx: Context, *, artist_name: str = None):
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
            )
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )
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
            try:
                if isinstance(i["artist"], str):
                    i["artists"] = orjson.loads(i["artist"])
                else:
                    i["artists"] = []
                i["plays"] = sum(
                    artist["plays"]
                    for artist in i["artists"]
                    if artist["name"].lower() == artist_name.lower()
                )
            except (orjson.JSONDecodeError, TypeError, KeyError):
                i["artists"] = []
                i["plays"] = 0
        data = [item for item in data if item["plays"] > 0]
        data = sorted(data, key=lambda x: x["plays"], reverse=True)
        if len(data) > 0:
            await self.bot.db.execute(
                """INSERT INTO lastfm_crowns (guild_id, artist, user_id, plays) 
                VALUES($1,$2,$3,$4) ON CONFLICT(guild_id, artist) 
                DO UPDATE SET user_id = $3, plays = $4""",
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

    @lastfm_whoknows.command(
        name="global",
        brief="Shows what other users listen to the current track globally",
        example=",lastfm whoknows global Juice Wrld",
    )
    async def lastfm_whoknows_global(self, ctx: Context, *, artist_name: str = None):
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
            )
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

        if not artist_name:
            data = await self.requester.get(
                method="user.getrecenttracks", user=conf.username
            )
            if "error" in data or not data["recenttracks"]["track"]:
                return await ctx.fail("Invalid username or no recent tracks.")
            artist_name = data["recenttracks"]["track"][0]["artist"]["#text"]

        async with ctx.typing():
            users_data = await self.bot.db.fetch(
                "SELECT user_id, username, artists FROM lastfm.users WHERE username IS NOT NULL"
            )

            async def process_user(user_data):
                user_id, username, artists = user_data
                try:
                    if isinstance(artists, str):
                        artists = orjson.loads(artists)
                    elif isinstance(artists, bytes):
                        artists = orjson.loads(artists)
                    elif artists is None:
                        return None
                    
                    plays = sum(
                        artist["plays"]
                        for artist in artists
                        if artist["name"].lower() == artist_name.lower()
                    )
                    if plays > 0:
                        user = self.bot.get_user(user_id) or await self.bot.fetch_user(
                            user_id
                        )
                        return {
                            "user_id": user_id,
                            "username": user.display_name if user else "Unknown",
                            "plays": plays,
                        }
                except (TypeError, ValueError, orjson.JSONDecodeError) as e:
                    print(f"Error processing user {user_id}: {e}")
                return None

            data = await asyncio.gather(
                *[process_user(user_data) for user_data in users_data]
            )
            data = [item for item in data if item]

            data.sort(key=lambda x: x["plays"], reverse=True)

            if data:
                await self.bot.db.execute(
                    """INSERT INTO lastfm_crowns (guild_id, artist, user_id, plays) 
                    VALUES($1,$2,$3,$4) ON CONFLICT(guild_id, artist) 
                    DO UPDATE SET user_id = $3, plays = $4""",
                    ctx.guild.id,
                    artist_name,
                    data[0]["user_id"],
                    data[0]["plays"],
                )

            embeds = []
            for i, chunk in enumerate(chunks(data, 10), start=1):
                description = "\n".join(
                    f"> `{i}.` **[{item['username']}](https://www.last.fm/user/{item['user_id']}) - {item['plays']} plays{' 👑' if i == 1 else ''}**"
                    for i, item in enumerate(chunk, start=(i - 1) * 10 + 1)
                )
                embeds.append(
                    discord.Embed(
                        title=f"{artist_name} most plays",
                        description=description,
                    )
                )

            if not embeds:
                return await ctx.fail("No plays found for this artist.")

            return await ctx.paginate(embeds)

    @lastfm.command(
        name="topartists",
        aliases=["ta"],
        brief="View the top artists of a user",
        example=",lastfm topartists",
    )
    async def lastfm_topartists(self, ctx: Context, user: discord.Member = None):
        user = user or ctx.author
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", user.id
            )
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

        data = await self.requester.get(method="user.gettopartists", user=conf.username)
        if "error" in data:
            return await ctx.fail("Invalid username.")

        artists = [
            f"> `{i+1}.` **{artist['name']}** - {artist['playcount']} plays"
            for i, artist in enumerate(data["topartists"]["artist"])
        ]
        embeds = []
        for i, chunk in enumerate(chunks(artists, 10), start=1):
            embeds.append(
                discord.Embed(
                    title=f"{conf.username}'s top artists",
                    description="\n".join(chunk),
                    color=0x2B2D31,
                ).set_thumbnail(
                    url=user.avatar.url if user else ctx.author.default_avatar.url
                )
            )
        if not embeds:
            return await ctx.fail("No artists found.")

        return await ctx.paginate(embeds)

    @lastfm.command(
        name="toptracks",
        aliases=["tt"],
        brief="View the top tracks of a user",
        example=",lastfm toptracks",
    )
    async def lastfm_toptracks(self, ctx: Context, user: discord.Member = None):
        user = user or ctx.author
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", user.id
            )
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

        data = await self.requester.get(method="user.gettoptracks", user=conf.username)
        if "error" in data:
            return await ctx.fail("Invalid username.")

        tracks = [
            f"> `{i+1}.` **{track['name']}** - {track['playcount']} plays"
            for i, track in enumerate(data["toptracks"]["track"])
        ]
        embeds = []
        for i, chunk in enumerate(chunks(tracks, 10), start=1):
            embeds.append(
                discord.Embed(
                    title=f"{conf.username}'s top tracks",
                    description="\n".join(chunk),
                    color=0x2B2D31,
                ).set_thumbnail(
                    url=user.avatar.url if user else ctx.author.default_avatar.url
                )
            )
        if not embeds:
            return await ctx.fail("No tracks found.")

        return await ctx.paginate(embeds)

    @lastfm.command(
        name="topalbums",
        aliases=["tal"],
        brief="View the top albums of a user",
        example=",lastfm topalbums",
    )
    async def lastfm_topalbums(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", user.id
            )
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

        data = await self.requester.get(method="user.gettopalbums", user=conf.username)
        if "error" in data:
            return await ctx.fail("Invalid username.")

        albums = [
            f"> `{i+1}.` **{album['name']}** - {album['playcount']} plays"
            for i, album in enumerate(data["topalbums"]["album"])
        ]
        embeds = []
        for i, chunk in enumerate(chunks(albums, 10), start=1):
            embeds.append(
                discord.Embed(
                    title=f"{conf.username}'s top albums",
                    description="\n".join(chunk),
                    color=0x2B2D31,
                ).set_thumbnail(
                    url=user.avatar.url if user else ctx.author.default_avatar.url
                )
            )
        if not embeds:
            return await ctx.fail("No albums found.")

        return await ctx.paginate(embeds)

    @commands.command(
        name="fm",
        brief="View the last song you listened to on LastFM",
        example=",fm",
        aliases=["np"]
    )
    async def fm(self, ctx: Context, user: discord.Member = None):
        return await self.nowplaying(ctx, user=user)

    @commands.command(
        name="whoknows",
        aliases=["wk"],
        brief="Shows what other users listen to the current track in your server",
        example=",wk Juice Wrld",
    )
    async def wk(self, ctx: Context, *, artist_name: str = None):
        return await self.lastfm_whoknows(ctx, artist_name=artist_name)

    @commands.command(
        name="globalwhoknows",
        brief="Shows what other users listen to the current track globally",
        example=",globalwhoknows Juice Wrld",
        aliases=["gwk", "globalwk"],
    )
    async def globalwhoknows(self, ctx: Context, *, artist_name: str = None):
        try:
            return await self.lastfm_whoknows_global(ctx, artist_name=artist_name)
        except orjson.JSONDecodeError:
            return await ctx.fail("An error occurred while processing the data. Please try again later.")

    @lastfm.command(
        name="taste",
        brief="Compare your music taste with another user",
        example=",lastfm taste @user [period]",
    )
    async def lastfm_taste(
        self, ctx: Context, member: discord.Member, period: str = "overall"
    ):
        if member.id == ctx.author.id:
            return await ctx.fail("You cannot compare your taste with yourself")

        configs = await self.bot.db.fetch(
            """SELECT * FROM lastfm.conf WHERE user_id = any($1::bigint[])""",
            [ctx.author.id, member.id],
        )

        if len(configs) != 2:
            return await ctx.fail(
                f"{'You' if not any(c.user_id == ctx.author.id for c in configs) else member.display_name} does not have a LastFM account linked"
            )

        period_map = {
            "7d": "7day",
            "1m": "1month",
            "3m": "3month",
            "6m": "6month",
            "1y": "12month",
            "overall": "overall",
            "lifetime": "overall",
            "alltime": "overall",
        }

        period = period_map.get(period.lower(), "overall")

        if period not in period_map.values():
            return await ctx.fail(
                "Invalid period. Valid options are: 7d, 1m, 3m, 6m, 1y, and overall"
            )

        async with ctx.typing():
            tasks = [
                self.requester.get(
                    method="user.gettopartists",
                    user=conf.username,
                    period=period,
                    limit=1000,
                )
                for conf in configs
            ]

            data = await asyncio.gather(*tasks)

            artists_data = []
            for i, response in enumerate(data):
                if "error" in response:
                    return await ctx.fail(
                        f"Failed to fetch data for {configs[i].username}"
                    )

                artists = {}
                for artist in response["topartists"]["artist"]:
                    artists[artist["name"]] = int(artist["playcount"])
                artists_data.append(artists)

            user1_artists = set(artists_data[0].keys())
            user2_artists = set(artists_data[1].keys())
            common_artists = user1_artists & user2_artists

            comparisons = []
            for artist in common_artists:
                plays1 = artists_data[0][artist]
                plays2 = artists_data[1][artist]
                if plays1 > plays2:
                    comparisons.append((artist, plays1, plays2))

            comparisons.sort(key=lambda x: x[1] - x[2], reverse=True)

            if not comparisons:
                return await ctx.fail("No common artists found in the specified period")

            formatted_comparisons = []
            for artist, plays1, plays2 in comparisons[:14]:
                name = artist[:15] + "..." if len(artist) > 15 else artist.ljust(15)
                formatted_comparisons.append(f"{name} {plays1:,} > {plays2:,}")

            description = (
                f"You both have {len(common_artists):,} artists in common\n\n"
                f"```\n"
                f"{chr(10).join(formatted_comparisons)}\n"
                f"```"
            )

            embed = discord.Embed(
                title=f"Taste comparison - {ctx.author.display_name} v {member.display_name}",
                description=description,
                color=0x2B2D31,
            )

            return await ctx.send(embed=embed)

    @commands.command(
        name="taste",
        brief="Compare your music taste with another user",
        example=",taste @user [period]",
    )
    async def taste(
        self, ctx: Context, member: discord.Member, period: str = "overall"
    ):
        return await self.lastfm_taste(ctx, member, period)

    @lastfm.command(
        name="milestone",
        brief="See what track your given number scrobble was",
        example=",lastfm milestone 1000",
    )
    async def lastfm_milestone(self, ctx: Context, number: int):
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", ctx.author.id
            )
        ):
            return await ctx.fail(
                "You do **not** have a **Last.FM account linked** to link an account do ,lf set"
            )

        if number <= 0:
            return await ctx.fail("Please provide a positive number")

        # Get user info to check total scrobbles
        user_info = await self.requester.get(method="user.getinfo", user=conf.username)

        if "error" in user_info:
            return await ctx.fail("Failed to fetch user information")

        total_scrobbles = int(user_info["user"]["playcount"])

        if number > total_scrobbles:
            return await ctx.fail(
                f"You only have {total_scrobbles:,} scrobbles in total"
            )

        # Calculate the page and index
        page_size = 200  # Last.fm API returns max 200 tracks per page
        page = (total_scrobbles - number) // page_size + 1
        index = (total_scrobbles - number) % page_size

        async with ctx.typing():
            try:
                # Fetch the specific page of recent tracks
                recent_tracks = await self.requester.get(
                    method="user.getrecenttracks",
                    user=conf.username,
                    limit=page_size,
                    page=page,
                )

                if "error" in recent_tracks:
                    return await ctx.fail("Failed to fetch track information")

                tracks = recent_tracks["recenttracks"]["track"]

                if not tracks or len(tracks) <= index:
                    return await ctx.fail("Could not find the track for this milestone")

                milestone_track = tracks[index]

                # Get additional track info
                track_info = await self.requester.get(
                    method="track.getInfo",
                    artist=milestone_track["artist"]["#text"],
                    track=milestone_track["name"],
                    username=conf.username,
                )

                # Create embed
                embed = discord.Embed(
                    title=f"Milestone #{number:,}",
                    description=f"**[{milestone_track['name']}]({milestone_track['url']})** by **[{milestone_track['artist']['#text']}](https://www.last.fm/music/{milestone_track['artist']['#text'].replace(' ', '+')})** was your {number:,} scrobble",
                    color=0x2B2D31,
                )

                # Add album if available
                if "album" in milestone_track and milestone_track["album"]["#text"]:
                    embed.add_field(
                        name="Album",
                        value=milestone_track["album"]["#text"],
                        inline=True,
                    )

                # Add date if available
                if "date" in milestone_track and milestone_track["date"]["#text"]:
                    embed.add_field(
                        name="Date", value=milestone_track["date"]["#text"], inline=True
                    )

                # Add thumbnail if available
                if milestone_track["image"] and milestone_track["image"][-1]["#text"]:
                    embed.set_thumbnail(url=milestone_track["image"][-1]["#text"])

                # Add user info in footer
                embed.set_footer(
                    text=f"{conf.username} • Total Scrobbles: {total_scrobbles:,}",
                    icon_url=ctx.author.display_avatar.url,
                )

                return await ctx.send(embed=embed)

            except Exception as e:
                return await ctx.fail(f"An error occurred: {str(e)}")

    @commands.command(
        name="milestone",
        brief="See what track your given number scrobble was",
        example=",milestone 1000",
    )
    async def milestone(self, ctx: Context, number: int):
        return await self.lastfm_milestone(ctx, number)

    async def index_user(
        self, user_id: int, artists_data: dict, tracks_data: dict
    ) -> None:
        """Index a user's LastFM data into the database"""
        try:
            if artists_data:
                records = [
                    {"name": artist["name"], "plays": int(artist["playcount"])}
                    for artist in artists_data["topartists"]["artist"]
                ]
                await self.bot.db.execute(
                    """INSERT INTO lastfm.users (user_id, artists) 
                    VALUES ($1, $2) ON CONFLICT (user_id) 
                    DO UPDATE SET artists = $2""",
                    user_id,
                    orjson.dumps(records).decode(),
                )

            if tracks_data:
                records = [
                    {"name": track["name"], "plays": int(track["playcount"])}
                    for track in tracks_data["toptracks"]["track"]
                ]
                await self.bot.db.execute(
                    """INSERT INTO lastfm.users (user_id, tracks) 
                    VALUES ($1, $2) ON CONFLICT (user_id) 
                    DO UPDATE SET tracks = $2""",
                    user_id,
                    orjson.dumps(records).decode(),
                )

        except Exception as e:
            raise Exception(f"Failed to index LastFM data: {str(e)}")


async def setup(bot):
    await bot.add_cog(LastFM(bot))
