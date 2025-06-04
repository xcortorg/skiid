# Standard library imports
import colorsys
from io import BytesIO
from random import choice
from asyncio import sleep
from typing import Optional, Union, Literal

# Third-party imports
from discord import (
    Message,
    utils,
    File,
    Color as DiscordColor,
    Member,
    User,
    app_commands,
    Embed,
)
from discord.ext.commands import (
    command,
    Cog,
    group,
    max_concurrency,
    cooldown,
    parameter,
    CommandError,
    BucketType,
    has_permissions,
    flag,
    hybrid_command,
    Range,
)
from discord.utils import utcnow, as_chunks
from gtts import gTTS
from loguru import logger as log

from shazamio import Shazam as ShazamClient
from shazamio.schemas.models import SongSection as ShazamSongSection
from shazamio.serializers import Serialize as ShazamSerialize

from yarl import URL

import rembg

# Local imports
import config
from config import Color
from system import Marly
from system.base.context import Context
from system.base.embed import EmbedScriptValidator
from system.tools.converters import (
    PartialAttachment,
    DomainConverter as FilteredDomain,
    CustomFlagConverter,
    CustomColorConverter,
    dominant,
)
from extensions.utility.afk import afk
from extensions.utility.snipe import Snipe
from system.tools.quote import Quotes
from system.tools.converters import image as imagetools


class ScreenshotFlags(CustomFlagConverter):
    delay: Optional[Range[int, 1, 10]] = flag(
        description="The amount of seconds to let the page render.",
        default=None,
    )
    full_page: Optional[bool] = flag(
        description="Whether or not to take  screenshot of the entire page.",
        default=None,
    )


class Utility(afk, Snipe, Cog):
    """
    Utility commands
    """
    shazamio: ShazamClient


    def __init__(self, bot: "Marly"):
        self.bot = bot
        self.quotes = Quotes(self.bot)

        self.shazamio = ShazamClient()

    @command(aliases=("recognize",))
    @cooldown(1, 1, BucketType.user)
    async def shazam(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.music_fallback,
        ),
    ) -> Message:
        """
        Recognize a song from an attachment
        """

        if attachment.format not in ("audio", "video"):
            raise CommandError("The file must be an audio or video format")

        async with ctx.typing():
            try:
                data = await self.shazamio.recognize(attachment.buffer)
            except Exception:
                raise CommandError("An error occurred while recognizing the song")

        output = ShazamSerialize.full_track(data)
        if not (track := output.track):
            raise CommandError(
                f"No tracks were found from [`{attachment.filename}`](<{attachment.url}>)"
            )

        return await ctx.embed(
            description=f"Found **[{track.title}]({URL(f'https://google.com/search?q={track.title} by {track.subtitle}')})** "
            f"by [**{track.subtitle}**](<{URL(f'https://google.com/search?q={track.subtitle}')}>)",
            image=track.sections[0].meta_pages[-1].image,
            color=config.Color.shazam,
            reference=ctx.message,
            footer={
                "text": "Shazam",
                "icon_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Shazam_icon.svg/84px-Shazam_icon.svg.png?20201029024040",
            },
        )

    @command()
    async def invert(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.imageonly_fallback,
        ),
    ):
        """
        Invert an image
        """
        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an **image** or **gif**")

        return await ctx.send(file=await imagetools.invert(attachment.buffer))

    @command(
        name="rotate",
        usage="(degree) (attachment or url or member)",
        example="90",
    )
    @cooldown(1, 5, BucketType.user)
    @has_permissions(attach_files=True)
    async def rotate(
        self,
        ctx: Context,
        degrees: int = parameter(description="Degrees to rotate (0-360)", default=90),
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.imageonly_fallback,
        ),
    ) -> Message:
        """
        Rotate an image by specified degrees
        """
        if not 0 <= degrees <= 360:
            raise CommandError("Degrees must be between **0** and **360**")

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an **image** or **gif**")

        return await ctx.send(file=await imagetools.rotate(attachment.buffer, degrees))

    @command()
    async def compress(
        self,
        ctx: Context,
        quality: int = parameter(
            description="Quality (100=best, 1=most compressed)", default=85
        ),
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.imageonly_fallback,
        ),
    ):
        """
        Compress an image with specified quality
        """

        if quality < 1 or quality > 100:
            raise CommandError("**Quality** must be between 1 and 100")

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an **image** or **gif**")

        return await ctx.send(
            file=await imagetools.compress(attachment.buffer, quality)
        )

    @command(
        name="texttospeech", aliases=["tts"], usage="<text>", example="yoo whats good"
    )
    @cooldown(1, 5, BucketType.user)
    @has_permissions(attach_files=True)
    async def texttospeech(self, ctx: Context, *, text: str) -> Message:
        """
        Convert text to speech
        """
        try:
            buffer = BytesIO()
            tts = gTTS(text=text, lang="en")
            tts.write_to_fp(buffer)
            buffer.seek(0)

            return await ctx.send(file=File(buffer, filename="tts.mp3"))

        except Exception as e:
            raise CommandError(f"Failed to convert text to speech: {e}")

    @hybrid_command(example="google.com --delay 5", aliases=["ss"])
    @cooldown(1, 5, BucketType.user)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def screenshot(
        self, ctx: Context, url: FilteredDomain, *, flags: ScreenshotFlags
    ) -> Message:
        """
        Capture a screenshot of a webpage.
        """

        async with ctx.typing():
            try:
                async with ctx.bot.browser.borrow_page() as page:
                    await page.goto(str(url), wait_until="load", timeout=30000)

                    if flags.delay:
                        await sleep(flags.delay)

                    screenshot_options = {
                        "full_page": flags.full_page,
                        "type": "png",
                        "animations": "disabled",
                    }

                    screenshot = await page.screenshot(**screenshot_options)
            except Exception as e:
                log.error(f"Failed to capture screenshot of {url}: {e}")
                raise CommandError("Failed to capture screenshot")

        return await ctx.send(file=File(BytesIO(screenshot), filename="screenshot.jpg"))

    @command(
        name="color",
        usage="<hex, random, member, or role color>",
        example="ffffff",
        aliases=[
            "colour",
        ],
    )
    @cooldown(1, 3, BucketType.user)
    async def color(self, ctx: Context, *, hex: CustomColorConverter):
        """
        Show a hex code's color in an embed
        """
        if hex is None:
            return await ctx.send_help(ctx.command)

        hex_color = str(hex).replace("#", "")
        color_url = f"https://www.color-hex.com/color/{hex_color}"

        return await ctx.embed(
            url=color_url,
            color=hex,
            author={
                "name": f"Showing color: #{hex_color}",
                "url": color_url,
            },
            thumbnail=f"https://place-hold.it/250x219/"
            + str(hex).replace("#", "")
            + "/?text=%20",
            image=f"https://api.alexflipnote.dev/color/image/gradient/{hex_color}",
            fields=[
                {
                    "name": "HEX",
                    "value": f"[`#{hex_color.upper()}`]({color_url})",
                    "inline": True,
                },
                {
                    "name": "RGB Value",
                    "value": f"`{hex.r},{hex.g},{hex.b}`",
                    "inline": True,
                },
                {
                    "name": "HSL Value",
                    "value": "`"
                    + ", ".join(
                        f"{int(value * (360 if index == 0 else 100))}%"
                        for index, value in enumerate(
                            colorsys.rgb_to_hls(*[x / 255.0 for x in hex.to_rgb()])
                        )
                    )
                    + "`",
                    "inline": True,
                },
            ],
            reference=ctx.message,
        )

    @command(
        name="randomhex",
    )
    @cooldown(1, 3, BucketType.user)
    async def randomhex(self, ctx: Context) -> Message:
        """
        Generate a random hex (color)
        """
        color = DiscordColor.random()
        return await self.color(ctx, hex=color)

    @command(
        aliases=["hex"],
        usage="hex (url or attachment or member)",
        example="jonny",
    )
    async def dominant(
        self,
        ctx: Context,
        user: Optional[Union[Member, User]] = None,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.imageonly_fallback,
        ),
    ) -> Message:
        """
        Get the dominant color of an image or user
        """

        if user:
            url = str(user.display_avatar.url)
        else:
            if attachment.format not in ("image", "gif"):
                raise CommandError("The file must be an image or gif")
            url = attachment.url

        async with ctx.typing():
            try:
                dominant_color = await dominant(ctx.bot.session, url)
            except Exception as e:
                raise CommandError(f"Failed to get dominant color: {e}")

        return await self.color(ctx, hex=dominant_color)

    @command(
        name="createembed",
        usage="<embed code>",
        example="{title: hi}",
        aliases=["ce"],
        customdescription=f"**Documentation Found** [**here**]({config.Marly.DOCS_URL}/resources/scripting/embeds)\n **Embed Builder** [**here**]({config.Marly.EMBED_BUILDER_URL})",
    )
    @has_permissions(manage_messages=True)
    async def createembed(self, ctx: Context, *, script: EmbedScriptValidator):
        """
        Create your own embed
        """
        # Pass all context variables that might be needed for variable resolution
        kwargs = {
            "bot": self.bot,
            "guild": ctx.guild,
            "channel": ctx.channel,
            "user": ctx.author,
            "member": ctx.author,  # Add member alias for user
            "message": ctx.message,
        }

        # Check for {reference} in the script
        if "{reference}" in str(script):
            kwargs["reference"] = ctx.message

        # Send with context
        await script.send(ctx, **kwargs)

    @command(
        name="choose",
        usage="(choices)",
        example="yes, no",
    )
    async def choose(self, ctx: Context, *, choices: str) -> Message:
        """
        Give me choices and I will pick for you
        """

        if not (choices := choices.split(", ")):
            raise CommandError(
                "Not **enough choices** to pick from - use a comma to separate"
            )

        return await ctx.utility(
            f" I choose `{choice(choices)}`",
            emoji="🤔",
        )

    @command(
        name="quickpoll",
        example="yall fw bbws?",
    )
    async def quickpoll(self, ctx: Context, *, question: str):
        """
        Create a quick poll
        """
        await ctx.message.add_reaction("⬆️")
        await ctx.message.add_reaction("⬇️")

    @command(
        name="poll",
        usage="[duration] <question>",
        example="15s Am I gay?",
    )
    @cooldown(1, 5, BucketType.user)
    async def poll(self, ctx: Context, seconds: Optional[int] = 20, *, question: str):
        """
        Create a short poll
        """
        embed = Embed(
            description=f"{ctx.author.mention} started a poll that will end after **{seconds}** second(s)!\n**Question:** {question}",
            timestamp=utcnow(),
        )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_footer(
            text=f"Guild: {ctx.guild.name} • Channel: {ctx.channel.name} • "
        )

        poll_message = await ctx.send(embed=embed)
        await poll_message.add_reaction("👍")
        await poll_message.add_reaction("👎")

        await sleep(seconds)

        poll_message = await ctx.channel.fetch_message(poll_message.id)
        thumbs_up = utils.get(poll_message.reactions, emoji="👍")
        thumbs_down = utils.get(poll_message.reactions, emoji="👎")

        embed.add_field(
            name="Results",
            value=f"👍 `{thumbs_up.count - 1}` / 👎 `{thumbs_down.count - 1}`",
            inline=False,
        )
        embed.timestamp = utcnow()
        embed.set_footer(text=f"Poll ended • {ctx.guild.name} • {ctx.channel.name} •")

        await ctx.send(embed=embed)
        await poll_message.delete()

    @command(
        aliases=["ai", "ask", "chatgpt", "gpt"],
    )
    async def gemini(self, ctx: Context, *, question: str) -> Optional[Message]:
        """
        Ask AI a question.
        """

        async with ctx.typing():
            response = await self.bot.session.post(
                URL.build(
                    scheme="https",
                    host="generativelanguage.googleapis.com",
                    path="/v1/models/gemini-pro:generateContent",
                    query={
                        "key": config.Apis.GEMINI,
                    },
                ),
                json={"contents": [{"parts": [{"text": question}]}]},
            )

            if not (data := await response.json()):
                raise CommandError("No response was found for that question!")

            if not (content := data.get("candidates", [])[0].get("content")) or not (
                parts := content.get("parts")
            ):
                raise CommandError("No response was found for that question!")

        await ctx.reply(parts[0]["text"])

    @hybrid_command()
    @cooldown(1, 5, BucketType.user)
    @max_concurrency(1, BucketType.channel, wait=True)
    async def transparent(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """
        make an image transparent
        """
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                output = rembg.remove(attachment.buffer)
                return await ctx.send(
                    file=File(BytesIO(output), filename="transparent.png")
                )
            except Exception as e:
                raise CommandError(f"Failed to process image: {e}")
