import random
from asyncio import sleep
from contextlib import suppress
from datetime import datetime, timezone
from io import BytesIO
from random import choice
from typing import List, Optional

import config
from bs4 import BeautifulSoup
from discord import (CategoryChannel, Color, Embed, File, Forbidden,
                     HTTPException, Invite, Member, Message, PartialMessage,
                     Reaction, Status, TextChannel, User, utils)
from discord.ext.commands import (BadArgument, BucketType, Cog, FlagConverter,
                                  MissingPermissions, Range, command, cooldown,
                                  flag, group, has_permissions,
                                  max_concurrency, param, parameter)
from discord.ext.tasks import loop
from discord.utils import (as_chunks, escape_markdown, escape_mentions, find,
                           format_dt, utcnow)
from gtts import gTTS
from loguru import logger as log
from PIL import Image, ImageOps
from tools import Bleed
from tools.client.context import Context
from tools.converters.basic import Domain as FilteredDomain
from tools.converters.embed import EmbedScript, EmbedScriptValidator
from tools.utilities import human_timedelta, shorten
from tools.utilities.shazam import Recognizer

from .snipe import Snipe
from .views.tictactoe import TicTacToe
from .views.views import RPS


class ScreenshotFlags(FlagConverter):
    delay: Optional[Range[int, 1, 10]] = flag(
        description="The amount of seconds to let the page render.",
        default=None,
    )


class Miscellaneous(Snipe, Cog):
    def __init__(self, bot: Bleed):
        super().__init__()
        self.bot = bot
        self.recognizer = Recognizer()

    @Cog.listener("on_user_update")
    async def name_history_listener(self, before: User, after: User) -> None:
        if before.name == after.name and before.global_name == after.global_name:
            return

        await self.bot.db.execute(
            """
            INSERT INTO name_history (user_id, username)
            VALUES ($1, $2)
            """,
            after.id,
            (
                before.name
                if after.name != before.name
                else (before.global_name or before.name)
            ),
        )

    @Cog.listener("on_message")
    async def check_afk(self, message: Message):
        if (ctx := await self.bot.get_context(message)) and ctx.command:
            return

        if author_afk_since := await self.bot.db.fetchval(
            """
            DELETE FROM afk
            WHERE user_id = $1
            RETURNING timestamp
            """,
            message.author.id,
        ):
            if "[afk]" in message.author.display_name.lower():
                with suppress(HTTPException):
                    await message.author.edit(
                        nick=message.author.display_name.replace("[afk]", "")
                    )

            await ctx.neutral(
                f"{message.author.mention}: Welcome back, you were away for **{human_timedelta(author_afk_since, suffix=False)}**",
                emoji="👋",
                reference=message,
            )

        bucket = self.bot.buckets.get("afk").get_bucket(message)
        if bucket.update_rate_limit():
            return

        if len(message.mentions) == 1 and (user := message.mentions[0]):
            if user_afk := await self.bot.db.fetchrow(
                """
                SELECT message, timestamp FROM afk
                WHERE user_id = $1
                """,
                user.id,
            ):
                await ctx.neutral(
                    f"{user.mention} is AFK: **{user_afk['message']}** - {human_timedelta(user_afk['timestamp'], suffix=False)} ago",
                    emoji="💤",
                )

    @command(name="afk", usage="<status>", example="sleeping...(slart)")
    async def afk(self, ctx: Context, *, status: str = "AFK"):
        """Set an AFK status for when you are mentioned"""
        status = shorten(status, 100)
        await self.bot.db.execute(
            """
            INSERT INTO afk (
                user_id,
                message,
                timestamp
            ) VALUES ($1, $2, $3)
            ON CONFLICT (user_id)
            DO NOTHING;
            """,
            ctx.author.id,
            status,
            ctx.message.created_at,
        )

        await ctx.approve(f"You're now AFK with the status: **{status}**")

    @command()
    @has_permissions(manage_guild=True)
    async def invites(self, ctx: Context) -> Message:
        """
        View all server invites.
        """

        invites = await ctx.guild.invites()
        if not invites:
            return await ctx.warn("No invites are currently present!")

        descriptions = [
            f"`{index:02}` [`{invite.code}`]({invite.url}) expires {format_dt(invite.expires_at, 'R') if invite.expires_at else '**Never**'}"
            for index, invite in enumerate(
                sorted(
                    invites,
                    key=lambda invite: invite.created_at or utcnow(),
                    reverse=False,
                ),
                start=1,
            )
        ]
        base_embed = Embed(title=f"Server Invites")
        base_embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @command(example="How to get a girlfriend")
    async def wikihow(self, ctx: Context, *, query: str):
        """
        Get answers to your question from wikihow
        """

        html = await self.bot.session.get(
            "https://www.wikihow.com/wikiHowTo", params={"search": query}
        )
        html_content = await html.text()

        soup = BeautifulSoup(html_content, "html.parser")
        searchlist = soup.find("div", attrs={"id": "searchresults_list"})
        if not searchlist:
            return await ctx.warn("Unfortunately i found nothing")

        contents = searchlist.find_all("a", attrs={"class": "result_link"})

        for content in contents:
            url = content["href"]
            if not "Category:" in url:
                title = content.find("div", attrs={"class": "result_title"})
                x = await self.bot.session.get(url)
                s = BeautifulSoup(await x.text(), "html.parser")
                steps = s.find_all("b", attrs={"class": "whb"})

                # Remove "How to" from the title
                title_text = title.text.replace("How to ", "").replace("How To ", "")

                # Create the description with steps
                description = "\n".join(
                    f"{i}- {step.text}" for i, step in enumerate(steps[:15], start=1)
                )

                # Add note about more steps if applicable
                if len(steps) > 15:
                    description += (
                        f"\n\nToo much to show, more available information @ {url}"
                    )

                embed = (
                    Embed(
                        title=title_text,
                        url=url,
                        color=config.Color.white,
                        description=description,
                    )
                    .set_author(
                        name=ctx.author.display_name, icon_url=ctx.author.display_avatar
                    )
                    .set_footer(text="Information from WikiHow")
                )
                return await ctx.reply(embed=embed)

        return await ctx.warn("Unfortunately i found nothing")

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
            timestamp=datetime.now(timezone.utc),
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
        embed.timestamp = datetime.now(timezone.utc)
        embed.set_footer(text=f"Poll ended • {ctx.guild.name} • {ctx.channel.name} •")

        await ctx.send(embed=embed)
        await poll_message.delete()

    @command(
        name="urbandictionary",
        usage="(word)",
        example="Slatt",
        aliases=["ud", "urban"],
    )
    async def urban(self, ctx: Context, *, word: str):
        """
        Gets the definition of a word/slang from Urban Dictionary
        """

        embeds = []

        # Make the request and get JSON directly
        async with self.bot.session.get(
            "http://api.urbandictionary.com/v0/define", params={"term": word}
        ) as response:
            if response.status != 200:
                return await ctx.warn("Failed to fetch definition")

            data = await response.json()

        defs = data["list"]
        if len(defs) == 0:
            return await ctx.warn(
                f"No definition found for **{word}**", reference=ctx.message
            )

        for defi in defs:
            e = (
                Embed(
                    title=defi["word"],
                    description=defi["definition"],
                    url=defi["permalink"],
                    color=config.Color.baseColor,
                )
                .set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                .add_field(name="Example", value=defi["example"], inline=False)
                .add_field(
                    name="Votes",
                    value=f"👍 `{defi['thumbs_up']} / {defi['thumbs_down']}` 👎",
                    inline=False,
                )
                .set_footer(
                    text=f"Page {defs.index(defi) + 1}/{len(defs)} of Urban Dictionary Results",
                    icon_url=ctx.author.display_avatar.url,
                )
            )
            embeds.append(e)

        await ctx.paginate(embeds)

    @command(
        aliases=["namehistory", "nh", "nicks"],
        example="johndoe",
    )
    async def names(
        self,
        ctx: Context,
        *,
        member: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View username and nickname history of a member or yourself.
        """

        names = await self.bot.db.fetch(
            """
            SELECT *
            FROM name_history
            WHERE user_id = $1
            """
            + ("" if ctx.author.id in self.bot.owner_ids else "\nAND is_hidden = FALSE")
            + "\nORDER BY changed_at DESC",
            member.id,
        )
        if not names:
            return await ctx.warn(
                f"No **logged username** or **nickname change** found"
            )

        descriptions = [
            f"`{index:02}` **{record['username']}** ({format_dt(record['changed_at'], 'R')})"
            for index, record in enumerate(names, start=1)
        ]
        base_embed = Embed(title="Name History")
        base_embed.color = config.Color.baseColor
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @command(
        usage="[choice]",
        aliases=["rockpaperscissors"],
        example="rock",
    )
    async def rps(self, ctx: Context, choice: Optional[str] = None) -> Message:
        """
        Play Rock-paper-scissors with me!
        """
        choices = {"rock": "🗿", "paper": "📰", "scissors": "✂️"}
        outcomes = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

        # If no choice provided, use the View interface
        if choice is None:
            return await RPS(ctx).start()

        choice = choice.lower()
        if choice not in choices:
            return await ctx.warn(
                "Please choose either **rock**, **paper**, or **scissors**"
            )

        bot_choice = random.choice(list(choices.keys()))

        result, color = (
            ("You win!", config.Color.approve)
            if bot_choice == outcomes[choice]
            else (
                ("We're square!", config.Color.warn)
                if choice == bot_choice
                else ("You lose!", config.Color.deny)
            )
        )

        result_emoji = (
            choices[choice]
            if choice == bot_choice or bot_choice == outcomes[choice]
            else choices[bot_choice]
        )

        embed = Embed(
            description=f"You chose `{choice}`, and I chose `{bot_choice}`. {result} {result_emoji}",
            color=color,
        )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        return await ctx.send(embed=embed)

    @group(
        name="tictactoe",
        usage="(member)",
        example="johndoe",
        aliases=["ttt"],
        invoke_without_command=True,
    )
    @cooldown(1, 5, BucketType.user)
    @max_concurrency(1, BucketType.member)
    async def tictactoe(self, ctx: Context, member: Member = None):
        """
        Play tic-tac-toe with somebody!
        """
        if not member:
            return await ctx.warn("Mention a **member** to play against!")
        if member == ctx.author:
            return await ctx.warn("You can't play against **yourself**!")
        if member.bot:
            return await ctx.warn("You can't play against **bots**!")

        await TicTacToe(ctx, member).start()

    @tictactoe.command(
        name="leaderboard",
        aliases=["lb"],
    )
    async def tictactoe_leaderboard(self, ctx: Context):
        """
        View the most tic-tac-toe wins
        """

        # Fetch top 50 players with at least 1 win
        records = await self.bot.db.fetch(
            """
            SELECT 
                user_id,
                wins
            FROM tictactoe_stats 
            WHERE wins > 0
            ORDER BY wins DESC 
            LIMIT 50
        """
        )

        if not records:
            return await ctx.warn("No **TicTacToe games** have been played yet!")

        embeds = []
        chunks = list(as_chunks(records, 10))

        for page_num, chunk in enumerate(chunks, 1):
            embed = Embed(title="Most **Tic-Tac-Toe** wins", color=config.Color.white)

            description = []
            start_idx = chunks.index(chunk) * 10 + 1

            for idx, record in enumerate(chunk, start_idx):
                user = self.bot.get_user(record["user_id"])
                username = user.name if user else f"Unknown user#{record['user_id']}"

                description.append(
                    f"`{idx:1}` **{username}** - `{record['wins']:,}` win{'s' if record['wins'] != 1 else ''}"
                )

            embed.description = "\n".join(description)
            embed.set_footer(
                text=f"Page {page_num}/{len(chunks)} ({len(records):,} entries)"
            )
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            embeds.append(embed)

        await ctx.paginate(embeds)

    @tictactoe.command(
        name="stats",
        aliases=["statistics"],
    )
    async def tictactoe_stats(self, ctx: Context, user: Optional[Member | User] = None):
        """
        View your or another user's tic-tac-toe statistics
        """
        user = user or ctx.author

        # Fetch user's stats
        stats = await self.bot.db.fetchrow(
            """
            SELECT 
                wins,
                COALESCE(games_played - wins, 0) as losses,
                games_played
            FROM tictactoe_stats 
            WHERE user_id = $1
        """,
            user.id,
        )

        if not stats:
            return await ctx.warn(
                f"{'You have' if user == ctx.author else f'**{user}** has'} **not played** any games yet!"
            )

        wins = stats["wins"]
        losses = stats["losses"]
        games = stats["games_played"]
        ratio = wins / games if games > 0 else 0

        embed = Embed(title="Tic-Tac-Toe Statistics")
        embed.description = (
            f"**Wins**: {wins:,}\n"
            f"**Losses**: {losses:,}\n"
            f"**Matches**: {games:,}\n"
            f"**Ratio**: {ratio:.1f}"
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

        await ctx.send(embed=embed)

    @command(
        name="compress",
        usage="(0-100) (attachment or url)",
        example="50 cdn.discordapp.com/...",
    )
    @cooldown(1, 5, BucketType.user)
    @has_permissions(attach_files=True)
    async def compress(
        self,
        ctx: Context,
        ratio: Optional[Range[int, 1, 100]] = 50,
        url: Optional[str] = None,
    ) -> Message:
        """
        Compress image to lower quality
        """
        # Get image URL from various sources
        if url:
            image_url = url
        elif ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        else:
            # Look for last image in channel
            async for message in ctx.channel.history(limit=10):
                if message.attachments:
                    if message.attachments[0].content_type.startswith("image/"):
                        image_url = message.attachments[0].url
                        break
                elif message.embeds:
                    for embed in message.embeds:
                        if embed.image:
                            image_url = embed.image.url
                            break
                    if "image_url" in locals():
                        break
            else:
                return await ctx.warn("No recent images found to compress")

        # Download and process the image
        async with self.bot.session.get(image_url) as response:
            if response.status != 200:
                return await ctx.warn("Failed to download the image")
            image_data = await response.read()

        try:
            with Image.open(BytesIO(image_data)) as img:
                output = BytesIO()
                img.save(
                    output, format=img.format or "PNG", quality=ratio, optimize=True
                )
                output.seek(0)

                await ctx.send(
                    file=File(
                        output,
                        filename=f"compressed.{img.format.lower() if img.format else 'png'}",
                    )
                )
        except Exception as e:
            await ctx.warn(f"Failed to compress image: {e}")

    @command(
        name="invert",
        usage="(attachment or url)",
        example="cdn.discordapp.com/...",
    )
    @cooldown(1, 5, BucketType.user)
    @has_permissions(attach_files=True)
    async def invert(self, ctx: Context, url: Optional[str] = None) -> Message:
        """
        Invert an image's colors
        """
        # Get image URL from various sources
        if url:
            image_url = url
        elif ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        else:
            # Look for last image in channel
            async for message in ctx.channel.history(limit=10):
                if message.attachments:
                    if message.attachments[0].content_type.startswith("image/"):
                        image_url = message.attachments[0].url
                        break
                elif message.embeds:
                    for embed in message.embeds:
                        if embed.image:
                            image_url = embed.image.url
                            break
                    if "image_url" in locals():
                        break
            else:
                return await ctx.send_help(ctx.command)

        # Download and process the image
        async with self.bot.session.get(image_url) as response:
            if response.status != 200:
                return await ctx.warn("Failed to download the image")
            image_data = await response.read()

        try:
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode == "RGBA":
                    # Handle transparency by separating alpha channel
                    r, g, b, a = img.split()
                    rgb_img = Image.merge("RGB", (r, g, b))
                    inverted_rgb = ImageOps.invert(rgb_img)
                    # Recombine with original alpha channel
                    r2, g2, b2 = inverted_rgb.split()
                    inverted_img = Image.merge("RGBA", (r2, g2, b2, a))
                else:
                    inverted_img = ImageOps.invert(img.convert("RGB"))

                output = BytesIO()
                inverted_img.save(output, format=img.format or "PNG")
                output.seek(0)

                await ctx.send(
                    file=File(
                        output,
                        filename=f"inverted.{img.format.lower() if img.format else 'png'}",
                    )
                )
        except Exception as e:
            await ctx.warn(f"Failed to invert image: {e}")

    @command(
        example="blee.com",
        aliases=["ss"],
    )
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def screenshot(self, ctx: Context, url: FilteredDomain) -> Message:
        """
        Get an image of a website
        """
        start_time = datetime.now()
        async with ctx.typing():
            try:
                async with ctx.bot.browser.borrow_page() as page:
                    await page.emulate_media(color_scheme="dark")
                    await page.goto(str(url), wait_until="networkidle", timeout=30000)

                    screenshot_options = {
                        "type": "png",
                    }

                    screenshot = await page.screenshot(**screenshot_options)
            except Exception as e:
                log.warning(f"Failed to get screenshot: {e}")
                return await ctx.warn(f"Failed to get screenshot")

        execution_time = (datetime.now() - start_time).total_seconds()
        embed = Embed(color=config.Color.baseColor)
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_image(url="attachment://screenshot.png")
        embed.set_footer(text=f"⏰ took {execution_time:.2f}s")

        return await ctx.send(
            embed=embed, file=File(BytesIO(screenshot), filename="screenshot.png")
        )

    @command(
        name="createembed",
        usage="<embed code>",
        example="{title: hi}",
        aliases=["ce"],
    )
    @has_permissions(manage_messages=True)
    async def createembed(self, ctx: Context, *, script: EmbedScriptValidator):
        """
        Create your own embed
        **Documentation found** [**here**](https://docs.example.bot/resources/scripting/embeds)
        """
        await script.send(
            ctx,
            bot=self.bot,
            guild=ctx.guild,
            channel=ctx.channel,
            user=ctx.author,
        )

    @command(
        name="copyembed",
        usage="(message link)",
        example=".../channels/...",
        aliases=["embedcode", "ec"],
    )
    @has_permissions(manage_messages=True)
    async def copyembed(self, ctx: Context, messagelink: Message):
        """
        Copy an existing embeds code for creating an embed
        **Documentation found** [**here**](https://docs.example.bot/resources/scripting/embeds)
        """
        result = []
        if content := messagelink.content:
            result.append(f"{{content: {content}}}")

        for embed in messagelink.embeds:
            result.append("{embed}")
            if color := embed.color:
                result.append(f"{{color: {color}}}")

            if author := embed.author:
                _author = []
                if name := author.name:
                    _author.append(name)
                if icon_url := author.icon_url:
                    _author.append(icon_url)
                if url := author.url:
                    _author.append(url)

                result.append(f"{{author: {' && '.join(_author)}}}")

            if url := embed.url:
                result.append(f"{{url: {url}}}")

            if title := embed.title:
                result.append(f"{{title: {title}}}")

            if description := embed.description:
                result.append(f"{{description: {description}}}")

            result.extend(
                f"{{field: {field.name} && {field.value} && {str(field.inline).lower()}}}"
                for field in embed.fields
            )
            if thumbnail := embed.thumbnail:
                result.append(f"{{thumbnail: {thumbnail.url}}}")

            if image := embed.image:
                result.append(f"{{image: {image.url}}}")

            if footer := embed.footer:
                _footer = []
                if text := footer.text:
                    _footer.append(text)
                if icon_url := footer.icon_url:
                    _footer.append(icon_url)

                result.append(f"{{footer: {' && '.join(_footer)}}}")

            if timestamp := embed.timestamp:
                result.append(f"{{timestamp: {str(timestamp)}}}")

        if not result:
            return await ctx.warn(
                f"Message [`{messagelink.id}`]({messagelink.jump_url}) doesn't contain an embed"
            )

        result = "\n".join(result)
        return await ctx.approve(f"Copied the **embed code**\n```{result}```")

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
            return await ctx.warn(
                "Not **enough choices** to pick from - use a comma to separate"
            )

        return await ctx.utility(
            f"I choose `{choice(choices)}`",
            emoji="🤔",
        )

    @command(
        name="shazam",
        usage="(audio file or url)",
        example="upload_a_file",
    )
    async def shazam(self, ctx: Context, url: Optional[str] = None) -> Message:
        """
        Find a song by providing video or audio
        """
        # Get audio URL from various sources
        if url:
            audio_url = url
        elif ctx.message.attachments:
            audio_url = ctx.message.attachments[0].url
        else:
            # Look for last audio file in channel
            async for message in ctx.channel.history(limit=10):
                if message.attachments:
                    if any(
                        message.attachments[0].filename.endswith(ext)
                        for ext in (".mp3", ".wav", ".m4a", ".ogg", ".mp4")
                    ):
                        audio_url = message.attachments[0].url
                        break
            else:
                return await ctx.send_help(ctx.command)

        async with ctx.typing():
            try:
                track = await self.recognizer.recognize(audio_url)
                if not track:
                    return await ctx.neutral(
                        f"{ctx.author.mention}: No **results** for [track]({audio_url})",
                        emoji="🔎",
                    )

                return await ctx.neutral(
                    f"{ctx.author.mention}: Found [**{track.song}**]({track.url}) by **{track.artist}**",
                    emoji=config.Emoji.shazam,
                    color=config.Color.shazam,
                )

            except Exception as e:
                await ctx.warn(f"Failed to analyze audio: {e}")

    @command(
        name="texttospeech", aliases=["tts"], usage="<text>", example="hey waddup hello"
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
            return await ctx.warn(f"Failed to convert text to speech: {e}")
