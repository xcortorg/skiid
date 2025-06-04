import colorsys
from asyncio import sleep
from io import BytesIO
from itertools import groupby
from random import choice
from re import compile, finditer
from time import sleep, time
from typing import Annotated, Dict, List, Literal, Optional, Union, cast

import config
from config import Emoji as EMOJIS
from discord import ActivityType, ButtonStyle, Color, Embed
from discord import Emoji as DiscordEmoji
from discord import (File, Guild, HTTPException, Interaction, Member, Message,
                     NotFound, PartialEmoji, RateLimited, Status, Streaming,
                     User, ui, utils)
from discord.ext.commands import (BucketType, Cog, Command, FlagConverter,
                                  Group, Range, command, cooldown, flag, group,
                                  has_permissions, max_concurrency)
from discord.ui import Button, View
from discord.utils import (as_chunks, escape_markdown, escape_mentions, find,
                           format_dt, utcnow)
from humanize import ordinal
from PIL import Image
from psutil import Process
from tools import Bleed
from tools.client.context import Context
from tools.client.views import EmojiButtons
from tools.converters.basic import Emoji, EmojiFinder, ImageFinder
from tools.converters.color import CustomColorConverter
from tools.utilities import Plural, human_join, human_timedelta
from tools.utilities.image import dominant
from tools.utilities.image import resize as resize_image
from tools.utilities.regex import ALL_EMOJI, DISCORD_EMOJI
from tools.utilities.shazam import Recognizer
from wand.image import Image as WandImage


class Information(Cog):
    def __init__(self, bot: Bleed) -> None:
        self.bot: Bleed = bot
        self.color_cache: Dict[str, Color] = {}
        self.emoji_stats_task = bot.loop.create_task(self.update_emoji_stats())
        self.emoji_stats_cache: Dict[tuple[int, str], int] = {}

    def cog_unload(self):
        self.emoji_stats_task.cancel()

    async def update_emoji_stats(self):
        """
        Background task to update emoji stats every 60 seconds
        """
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                if self.emoji_stats_cache:
                    # Prepare batch query
                    query = """
                        INSERT INTO emoji_stats (guild_id, emoji_id, uses)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (guild_id, emoji_id)
                        DO UPDATE SET uses = emoji_stats.uses + $3
                    """

                    # Execute all updates in a transaction
                    async with self.bot.db.acquire() as conn:
                        async with conn.transaction():
                            for (
                                guild_id,
                                emoji_id,
                            ), uses in self.emoji_stats_cache.items():
                                await conn.execute(query, guild_id, emoji_id, uses)

                    # Clear the cache after successful update
                    self.emoji_stats_cache.clear()

            except Exception as e:
                print(f"Error updating emoji stats: {e}")

            await sleep(60)

    @Cog.listener()
    async def on_message(self, message: Message):
        if not message.guild or message.author.bot:
            return

        matches = ALL_EMOJI.finditer(message.content)
        for match in matches:
            emoji_id = match.group("id") or match.group(0)
            cache_key = (message.guild.id, str(emoji_id))
            self.emoji_stats_cache[cache_key] = (
                self.emoji_stats_cache.get(cache_key, 0) + 1
            )

    @command(
        name="botinfo",
        aliases=["bi", "about"],
    )
    async def botinfo(self, ctx: Context) -> Message:
        """
        View the bot's information
        """
        return await ctx.send(f"No")

    @command(
        name="ping",
    )
    async def ping(self, ctx: Context) -> Message:
        """
        View the bot's latency
        """

        start = time()
        message = await ctx.send(content="ping...")
        finished = (time() - start) * 1000

        return await message.edit(
            content=f"it took `{int(self.bot.latency * 1000)}ms` to ping **{choice(config.ping_responses)}** (edit: `{finished:.1f}ms`)"
        )

    @command(
        name="uptime",
        aliases=["boot"],
    )
    async def uptime(self, ctx: Context) -> Message:
        """
        View the bot's uptime
        """

        return await ctx.channel.neutral(
            f"**{self.bot.user.display_name}** has been up for: **{human_timedelta(self.bot.uptime, suffix=False)}**",
            emoji="⏰",
        )

    @command(
        name="help",
        aliases=["commands", "h"],
        usage="command",
        example="ban",
        notes="h -simple",
    )
    async def help(self, ctx: Context, *, command: str = None) -> Message:
        """
        View command information
        """
        if command == "-simple":
            embed = Embed(description="")
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )

            for cog_name, cog in self.bot.cogs.items():
                if getattr(cog, "hidden", False):
                    continue

                commands = [
                    cmd for cmd in cog.get_commands() if not cmd.hidden and cmd.enabled
                ]

                if not commands:
                    continue

                command_list = ", ".join(
                    f"{cmd.name}{'*' if isinstance(cmd, Group) else ''}"  # Fixed order of operations
                    for cmd in commands
                )
                embed.add_field(
                    name=f"__**{cog_name}**__", value=command_list, inline=False
                )
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            embed.set_footer(text=f"{len(self.bot.commands)} commands")
            return await ctx.send(embed=embed)

        if not command:
            return await ctx.send(
                f"{ctx.author.mention}: <https://example.bot/help>, join the discord server @ <https://example.bot/discord>"
            )

        command_obj: Command | Group = self.bot.get_command(command)
        if not command_obj:
            return await ctx.warn(f"Command `{command}` does **not** exist")

        embeds = []
        commands_list = []
        if isinstance(command_obj, Group):
            commands_list.append(command_obj)
            for subcmd_name, subcmd in command_obj.all_commands.items():
                if subcmd not in commands_list:
                    commands_list.append(subcmd)
        else:
            commands_list = [command_obj]

        for index, command in enumerate(commands_list):
            embed = Embed(
                color=config.Color.info,
                title=(
                    ("Group Command: " if isinstance(command, Group) else "Command: ")
                    + command.qualified_name
                ),
                description=command.help,
            )
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )

            embed.add_field(
                name="**Aliases**",
                value=(
                    ", ".join(a for a in command.aliases) if command.aliases else "n/a"
                ),
                inline=True,
            )
            embed.add_field(
                name="**Parameters**",
                value=(
                    ", ".join(param.replace("_", " ") for param in command.clean_params)
                    if command.clean_params
                    else "n/a"
                ),
                inline=True,
            )

            embed.add_field(
                name="**Information**",
                value=(
                    " ".join(
                        [
                            (
                                f"\n{config.Emoji.cooldown} {int(command._buckets._cooldown.per)} seconds"
                                if command._buckets._cooldown
                                else ""
                            ),
                            (
                                f"\n{config.Emoji.warn} {', '.join(perm.replace('_', ' ').title() for perm in command.permissions)}{' & ' + command.brief if command.brief else ''}"
                                if command.permissions is not None
                                else (
                                    f"\n{config.Emoji.warn} {command.brief}"
                                    if command.brief
                                    else ""
                                )
                            ),
                            (
                                f"\n{config.Emoji.notes} {command.notes}"
                                if command.notes
                                else ""
                            ),
                        ]
                    ).strip()
                    or "n/a"
                ),
                inline=True,
            )

            embed.add_field(
                name="Usage",
                value=(
                    "```\n"
                    + (
                        f"Syntax: {ctx.prefix}{command.qualified_name} "
                        + (
                            command.usage
                            or " ".join(
                                [
                                    (
                                        f"<{name}>"
                                        if param.default == param.empty
                                        else f"({name})"
                                    )
                                    for name, param in command.clean_params.items()
                                ]
                            )
                        )
                    )
                    + "\n"
                    + (
                        f"Example: {ctx.prefix}{command.qualified_name} {command.example}"
                        if command.example
                        else ""
                    )
                    + "```"
                ),
                inline=False,
            )

            embed.set_footer(
                text=(
                    f"Page  {index + 1}/{len(commands_list)} ({len(commands_list)} {'Page ' if len(commands_list) == 1 else 'Page '}) ∙ Module: {command.cog_name.lower() if command.cog_name else 'n/a'}"
                    if isinstance(command_obj, Group)
                    else f"Module: {command.cog_name.lower() if command.cog_name else 'n/a'}"
                ),
            )

            embeds.append(embed)

        await ctx.paginate(embeds)

    @command(
        name="roleinfo",
        example="Friends",
        aliases=["rinfo", "ri"],
    )
    async def roleinfo(self, ctx: Context, *, role: str = None):
        """
        View information about a role
        """
        try:
            if role is None:
                role = ctx.author.top_role
            elif role.startswith("<@&") and role.endswith(">"):
                role_id = int(role[3:-1])
                role = ctx.guild.get_role(role_id)
            else:
                role_lower = role.lower()
                role = find(lambda r: r.name.lower() == role_lower, ctx.guild.roles)

            if not role:
                if role is None:
                    role = ctx.author.top_role
                else:
                    await ctx.warn(
                        f"I was unable to find a role with the name: **{role}**",
                    )
                    return

            embed = Embed(title=role.name, color=role.color)

            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )

            embed.add_field(
                name="Role ID",
                value=f"`{role.id}`",
                inline=True,
            )
            embed.add_field(
                name="Guild",
                value=f"{ctx.guild.name} (`{ctx.guild.id}`)",
                inline=True,
            )
            embed.add_field(
                name="Color",
                value=f"`{role.color}`",
                inline=True,
            )
            if role.icon:
                embed.set_thumbnail(url=role.icon)
            embed.add_field(
                name="Creation Date",
                value=(
                    format_dt(role.created_at, style="f")
                    + " **("
                    + format_dt(role.created_at, style="R")
                    + ")**"
                ),
                inline=False,
            )

            members = role.members
            if members:
                member_list = ", ".join([member.name[:10] for member in members[:7]])
                embed.add_field(
                    name=f"{len(members)} Member(s)",
                    value=member_list + ("..." if len(members) > 7 else ""),
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Members",
                    value="No members in this role",
                    inline=False,
                )

            embed.color = role.color

            return await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.warn(f"An error occurred: {str(e)}", reference=ctx.message)

    @command()
    async def status(self, ctx: Context) -> Message:
        """
        View the bot's status
        """

        return await ctx.send(
            f"{ctx.author.mention}: experiencing issues? check your shards status on https://example.bot/status"
        )

    @command(
        name="donate",
        aliases=["donation", "support"],
    )
    async def donate(self, ctx: Context) -> Message:
        """
        Donate to the bot's hosting expenses
        """
        embed = Embed(
            title="DONATE",
            description=(
                ":new: **Donator perks** have changed to **tier subscriptions**! "
                f"Join our Discord Server **[here]({config.Bleed.support})** to learn more about "
                "**donator perks** or on how to invite the bot to your server.\n\n"
                "**Donation methods (not for donator perks)**\n"
                "**Bitcoin**: `0000000000000000000000000000000000000000`\n"
                "**Ethereum**: `0x0000000000000000000000000000000000000000`\n"
                "**Litecoin**: `0000000000000000000000000000000000000000`\n\n"
            ),
        )
        embed.set_footer(
            text=f"All payments go directly to the bot for hosting, API expenses and more",
            icon_url="https://cdn.discordapp.com/emojis/1302331257916493834.webp?size=128&quality=lossless",
        )

        return await ctx.send(embed=embed)

    @command(
        name="avatar",
        usage="<member>",
        example="johndoe",
        aliases=["av", "avi", "pfp", "ab", "ag"],
        notes="User ID available",
    )
    async def avatar(self, ctx: Context, *, user: Member | User = None):
        """
        View a user avatar
        """
        user = user or ctx.author

        embed = Embed(
            url=user.display_avatar.url,
            title=f"{user.name}'s avatar",
            color=user.top_role.color,
        )
        embed.set_image(url=user.display_avatar)

        if user.id != ctx.author.id:
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )

        await ctx.send(embed=embed)

    @command(
        name="banner",
        usage="<member>",
        example="johndoe",
        notes="User ID available",
    )
    async def banner(self, ctx: Context, *, user: Member | User = None):
        """
        Get the banner of a member or yourself
        """
        user = user or ctx.author
        user = await self.bot.fetch_user(user.id)

        if not user.banner:
            return await ctx.warn(
                f"You don't have a **banner** set!"
                if user == ctx.author
                else f"**{user.mention}** doesn't have a **banner** set!"
            )

        url = user.banner.url
        embed = Embed(url=url, title=f"{user.name}'s banner")
        if isinstance(user, Member):
            embed.color = user.top_role.color
        embed.set_image(url=url)

        if user.id != ctx.author.id:
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            embed.color = ctx.author.top_role.color

        await ctx.send(embed=embed)

    @command(
        name="serverinfo",
        usage="<guild>",
        example="1115389989..",
        aliases=[
            "guildinfo",
            "sinfo",
            "ginfo",
            "si",
            "gi",
        ],
    )
    async def serverinfo(self, ctx: Context, *, guild: Guild = None) -> Message:
        """
        View information about a guild
        """

        guild = guild or ctx.guild

        embed = Embed(
            title=guild.name,
            description=(
                "Server created on "
                + (
                    format_dt(guild.created_at, style="D")
                    + "("
                    + format_dt(guild.created_at, style="R")
                    + ")"
                )
                + f"\n__{guild.name}__ is on bot shard ID: **{guild.shard_id}/{self.bot.shard_count}**"
            ),
            timestamp=utcnow(),
            color=config.Color.white,
        )
        embed.set_thumbnail(url=guild.icon)

        embed.add_field(
            name="**Owner**",
            value=(guild.owner or guild.owner_id),
            inline=True,
        )
        embed.add_field(
            name="**Members**",
            value=(
                f"**Total:** {guild.member_count:,}\n"
                f"**Humans:** {len([m for m in guild.members if not m.bot]):,}\n"
                f"**Bots:** {len([m for m in guild.members if m.bot]):,}"
            ),
            inline=True,
        )
        embed.add_field(
            name="**Information**",
            value=(
                f"**Verification:** {guild.verification_level.name.title()}\n"
                f"**Boosts:** {guild.premium_subscription_count:,} (level {guild.premium_tier})"
            ),
            inline=True,
        )
        embed.add_field(
            name="**Design**",
            value=(
                f"**Banner:** "
                + (f"[Click here]({guild.banner})\n" if guild.banner else "N/A\n")
                + f"**Splash:** "
                + (f"[Click here]({guild.splash})\n" if guild.splash else "N/A\n")
                + f"**Icon:** "
                + (f"[Click here]({guild.icon})\n" if guild.icon else "N/A\n")
            ),
            inline=True,
        )
        embed.add_field(
            name=f"**Channels ({len(guild.channels)})**",
            value=f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Category:** {len(guild.categories)}\n",
            inline=True,
        )
        embed.add_field(
            name="**Counts**",
            value=(
                f"**Roles:** {len(guild.roles)}/250\n"
                f"**Emojis:** {len(guild.emojis)}/{guild.emoji_limit}\n"
                f"**Boosters:** {len(guild.premium_subscribers):,}\n"
            ),
            inline=True,
        )
        embed.set_footer(text=f"Guild ID: {guild.id}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        return await ctx.send(embed=embed)

    @command()
    async def bots(self, ctx: Context) -> Message:
        """
        View all bots in the server.
        """
        members = list(
            filter(
                lambda member: member.bot,
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.warn(f"**{ctx.guild}** doesn't have any **bots!**")

        # Create list of embeds instead of descriptions
        pages = []
        chunks = [members[i : i + 10] for i in range(0, len(members), 10)]

        for index, chunk in enumerate(chunks):
            embed = Embed(
                color=config.Color.baseColor,
                title="**List of bots**",
                description="\n".join(
                    f"`{members.index(member) + 1:02}` **{member.display_name}#{member.discriminator}**"
                    for member in chunk
                ),
            )
            embed.set_author(
                name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar
            )
            embed.set_footer(
                text=f"page {index + 1}/{len(chunks)} ({len(members)} entries)"
            )
            pages.append(embed)

        return await ctx.paginate(pages=pages)

    @command(
        name="color",
        usage="<hex, random, member, or role color>",
        example="ffffff",
        aliases=[
            "colour",
        ],
    )
    async def color(self, ctx: Context, *, hex: CustomColorConverter = Color(0)):
        """
        Show a hex code's color in an embed
        """
        hex_color = str(hex).replace("#", "")
        color_url = f"https://www.color-hex.com/color/{hex_color}"
        embed = Embed(color=hex, url=color_url)
        embed.set_author(name=f"Showing hex code: #{hex_color}", url=color_url)
        embed.set_thumbnail(
            url=(
                "https://place-hold.it/250x219/"
                + str(hex).replace("#", "")
                + "/?text=%20"
            )
        )

        embed.add_field(
            name="RGB Value",
            # 194, 231, 70
            value=", ".join(str(value) for value in hex.to_rgb()),
            inline=True,
        )
        embed.add_field(
            name="HSL Value",
            value=", ".join(
                f"{int(value * (360 if index == 0 else 100))}%"
                for index, value in enumerate(
                    colorsys.rgb_to_hls(*[x / 255.0 for x in hex.to_rgb()])
                )
            ),
            inline=True,
        )
        return await ctx.reply(embed=embed)

    @command(
        name="randomhex",
    )
    async def randomhex(self, ctx: Context) -> Message:
        """
        Generate a random hex (color)
        """
        color = Color.random()
        return await self.color(ctx, hex=color)

    @command(
        usage="(url or attachment or member)",
        example="johndoe",
        aliases=["dominant"],
    )
    async def hex(
        self, ctx: Context, target: Optional[Member | User | str] = None
    ) -> Message:
        """
        Grab the most dominant color from an image
        """
        url = None

        try:
            # Check if target is a member/user
            if isinstance(target, (Member, User)):
                url = str(target.display_avatar.url)
            # If target is a string, validate it as a URL
            elif isinstance(target, str):
                # Basic URL validation
                if target.startswith(("http://", "https://")):
                    url = target
                else:
                    return await ctx.warn(
                        "Could not convert **url or attachment or member** into `Member or URL`"
                    )

            if url is None:
                # Check message attachments first
                if ctx.message.attachments:
                    url = str(ctx.message.attachments[0].url)
                else:
                    # Look for the last image in the channel
                    async for message in ctx.channel.history(limit=50):
                        # Check attachments
                        if message.attachments:
                            for attachment in message.attachments:
                                if (
                                    attachment.content_type
                                    and "image" in attachment.content_type
                                ):
                                    url = str(attachment.url)
                                    break
                        # Check embeds
                        if not url and message.embeds:
                            for embed in message.embeds:
                                if embed.image:
                                    url = str(embed.image.url)
                                    break
                                elif embed.thumbnail:
                                    url = str(embed.thumbnail.url)
                                    break
                        if url:
                            break

                    # If no image found, show help
                    if not url:
                        return await ctx.send_help(ctx.command)

            # Check cache before processing
            if url in self.color_cache:
                return await self.color(ctx, hex=self.color_cache[url])

            # Get the dominant color
            try:
                color = await dominant(self.bot.session, url)
                self.color_cache[url] = color  # Cache the result

                # Limit cache size to prevent memory issues
                if len(self.color_cache) > 1000:  # Adjust size as needed
                    self.color_cache.pop(next(iter(self.color_cache)))

                return await self.color(ctx, hex=color)
            except Exception as e:
                return await ctx.warn(f"Failed to process image: {str(e)}")

        except Exception as e:
            return await ctx.warn(f"An error occurred: {str(e)}")

    @group(
        name="emoji",
        usage="(subcommand) <args>",
        aliases=["emote", "e"],
        example="🔥",
        invoke_without_command=True,
    )
    async def emoji(self, ctx: Context, *, emoji: EmojiFinder):
        """
        Returns a large emoji or server emote
        """
        try:
            async with ctx.typing():
                # Fetch the emoji data
                async with self.bot.session.get(emoji.url, timeout=5) as response:
                    if response.status != 200:
                        return await ctx.warn("Failed to fetch emoji")
                    image_data = await response.read()

                # Resize the image to 256x256 while maintaining quality
                processed_data = await resize_image(image_data, (256, 256))

                # Create file object from processed data
                file = File(
                    processed_data,
                    filename=f"emoji.{'gif' if emoji.animated else 'png'}",
                )

                return await ctx.send(file=file, reference=ctx.message)

        except Exception as e:
            await ctx.warn(f"Failed to process emoji: {str(e)}")

    @emoji.command(
        name="addmany",
        usage="(emojis)",
        example="hella_emotes_here",
        aliases=["am"],
    )
    @has_permissions(manage_emojis=True)
    @max_concurrency(1, BucketType.guild)
    async def emoji_add_many(self, ctx: Context, *, emojis: str = None):
        """
        Bulk add emojis to the server
        """
        if not emojis:
            return await ctx.warn("Please provide some emojis to add!")

        #        # Debug: Print the raw input
        #        print(f"Raw emoji input: {emojis}")

        if len(ctx.guild.emojis) >= ctx.guild.emoji_limit:
            return await ctx.warn(
                f"This server has reached its emoji limit ({ctx.guild.emoji_limit})"
            )

        matches = list(finditer(DISCORD_EMOJI, emojis))
        if not matches:
            return await ctx.warn(
                "No valid Discord emojis found! Make sure you're using custom emojis, not Unicode emojis.\n"
                "Example: `:emoji_name:`"
            )

        existing_emoji_ids = {emoji.id for emoji in ctx.guild.emojis}
        emojis = []

        for match in matches:
            emoji_id = int(match.group("id"))
            if emoji_id not in existing_emoji_ids:
                emojis.append(
                    Emoji(
                        name=match.group("name"),
                        url="https://cdn.discordapp.com/emojis/"
                        + match.group("id")
                        + (".gif" if match.group("animated") else ".png"),
                        id=emoji_id,
                        animated=bool(match.group("animated")),
                    )
                )

        if not emojis:
            return await ctx.warn(
                "All provided emojis either already exist in this server or are invalid!"
            )

        available_slots = ctx.guild.emoji_limit - len(ctx.guild.emojis)
        if len(emojis) > available_slots:
            await ctx.warn(
                f"Only adding the first {available_slots} emojis due to server limit"
            )
            emojis = emojis[:available_slots]

        emojis_added = []
        failed = []

        async with ctx.typing():
            for emoji in emojis:
                try:
                    image = await emoji.read()
                    new_emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=image,
                        reason=f"{ctx.author}: Emoji added (bulk)",
                    )
                    emojis_added.append(new_emoji)

                except RateLimited as error:
                    await ctx.warn(
                        f"Rate limited for **{error.retry_after:.2f} seconds**"
                        + (
                            f", stopping at {len(emojis_added)} emojis"
                            if emojis_added
                            else ""
                        )
                    )
                    break

                except HTTPException as e:
                    failed.append(emoji.name)
                    print(f"Failed to add emoji {emoji.name}: {str(e)}")
                    continue

        response = []
        if emojis_added:
            response.append(
                f"Successfully added **{Plural(len(emojis_added)):new emote}**"
            )
        if failed:
            response.append(f"Failed to add: {', '.join(failed)}")

        if response:
            await ctx.approve("\n".join(response))
        else:
            await ctx.warn("No **emojis** were added to the server")

    @emoji.group(
        name="remove",
        usage="(emoji)",
        example="🦮",
        aliases=["delete", "del"],
        invoke_without_command=True,
    )
    @has_permissions(manage_emojis=True)
    async def emoji_remove(self, ctx: Context, *, emoji: DiscordEmoji):
        """Remove an emoji from the server"""
        if emoji.guild_id != ctx.guild.id:
            return await ctx.warn("That **emoji** isn't in this server")

        await emoji.delete(reason=f"{ctx.author}: Emoji deleted")
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Removed [**{emoji.name}**]({emoji.url}) from the server",
            emoji=emoji,
        )

    @emoji.command(
        name="stats",
        usage="(emote)",
        example="🔥",
        aliases=["usage", "uses"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_stats(self, ctx: Context, emote: EmojiFinder = None):
        """
        Show top ten most used emotes
        """
        if emote:
            query = "SELECT uses FROM emoji_stats WHERE guild_id = $1 AND emoji_id = $2"
            record = await self.bot.db.fetchrow(
                query, ctx.guild.id, str(emote.id or emote)
            )
            uses = record["uses"] if record else 0

            embed = Embed()
            embed.set_author(
                name=f"Emoji Statistics", icon_url=ctx.author.display_avatar.url
            )
            embed.description = (
                f"{emote} has been used **{uses:,}** times in this server"
            )
            return await ctx.send(embed=embed)

        query = """
            SELECT emoji_id, uses 
            FROM emoji_stats 
            WHERE guild_id = $1 
            ORDER BY uses DESC
        """
        records = await self.bot.db.fetch(query, ctx.guild.id)

        if not records:
            return await ctx.warn("No emoji **statistics** for this server")

        valid_records = []
        for record in records:
            emoji_id = record["emoji_id"]

            # Handle unicode emojis
            if not emoji_id.isdigit():
                valid_records.append(record)
                continue

            # Handle custom emojis
            try:
                emoji = self.bot.get_emoji(int(emoji_id))
                if emoji:
                    valid_records.append(record)
            except:
                continue

            # Stop if we have 10 valid emojis
            if len(valid_records) == 10:
                break

        if not valid_records:
            return await ctx.warn("No active emoji statistics found for this server")

        total_uses = sum(record["uses"] for record in valid_records)

        description = []
        for index, record in enumerate(valid_records, 1):
            emoji_id = record["emoji_id"]
            uses = record["uses"]
            uses_per_day = round(uses / 30)  # Assuming 30 days of data
            percentage = (uses / total_uses) * 100

            # Get emoji object (we know it exists from filtering above)
            if emoji_id.isdigit():
                emoji = self.bot.get_emoji(int(emoji_id))
            else:
                emoji = emoji_id

            description.append(
                f"`{index}` {emoji} has **{uses}** with **{uses_per_day}** use{'s' if uses_per_day != 1 else ''} a day `[{percentage:.1f}%]`"
            )

        embed = Embed(
            title="Emote Leaderboard",
            description="**Top 10**\n" + "\n".join(description),
        )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

    @emoji.command(
        name="add",
        usage="(emoji or url) <name>",
        example=" cdn.discordapp.com/emojis/768...png mommy",
        aliases=["create", "copy"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_add(
        self,
        ctx: Context,
        emoji: DiscordEmoji | PartialEmoji | ImageFinder | int | None,
        *,
        name: str = None,
    ):
        """
        Downloads emote and adds to server
        """
        if not name and not (isinstance(emoji, (Emoji, PartialEmoji))):
            return await ctx.warn("Missing **name** for server emote")

        if not emoji:
            try:
                emoji = await ImageFinder.search(ctx, history=False)
            except Exception:
                return await ctx.send_help()

        if isinstance(emoji, Emoji) and emoji.guild_id == ctx.guild.id:
            return await ctx.warn("That **emoji** is already in this server")

        if type(emoji) in (Emoji, PartialEmoji):
            name = name or emoji.name
        elif isinstance(emoji, int):
            emoji = f"https://cdn.discordapp.com/emojis/{emoji}.png"

        if len(name) < 2:
            return await ctx.warn("Emote name needs to be **2 characters** or **more**")
        name = name[:32].replace(" ", "_")

        response = await self.bot.session.get(
            emoji if isinstance(emoji, str) else emoji.url
        )
        image = await response.read()

        try:
            emoji = await ctx.guild.create_custom_emoji(
                name=name, image=image, reason=f"{ctx.author}: Emoji added"
            )
        except RateLimited as error:
            return await ctx.warn(
                f"Please try again in **{error.retry_after:.2f} seconds**"
            )
        except HTTPException:
            if len(ctx.guild.emojis) == ctx.guild.emoji_limit:
                return await ctx.warn(
                    f"The maximum amount of **emojis** has been reached (`{ctx.guild.emoji_limit}`)"
                )
            return await ctx.warn(
                f"Failed to add **emote** [`:{emoji.name}:`]({response.url})"
            )

        await ctx.approve(
            f"Added **emote** [`:{emoji.name}:`]({emoji.url})",
        )

    @emoji.command(
        name="removemany",
        usage="(emotes)",
        example="hella_emotes_here",
        aliases=["rm", "deletemany", "dm"],
    )
    @has_permissions(manage_emojis=True)
    @max_concurrency(1, BucketType.guild)
    async def emoji_remove_many(self, ctx: Context, *, emojis: str = None):
        """Bulk remove emotes from the current server"""
        if not emojis:
            return await ctx.warn(
                "Missing emojis to **bulk remove** - separate your emotes with a space!"
            )

        # Extract emoji IDs from the input
        matches = list(finditer(DISCORD_EMOJI, emojis))
        if not matches:
            return await ctx.warn("No valid **emojis** found to **bulk remove**!")

        # Filter emojis that belong to this server
        guild_emojis = []
        for match in matches:
            emoji_id = int(match.group("id"))
            emoji = ctx.guild.get_emoji(emoji_id)
            if emoji:
                guild_emojis.append(emoji)

        if not guild_emojis:
            return await ctx.warn("None of those **emojis** are from this server!")

        emojis_removed = []
        async with ctx.typing():
            for emoji in guild_emojis:
                try:
                    await emoji.delete(reason=f"{ctx.author}: Emoji removed (bulk)")
                    emojis_removed.append(emoji)
                except (HTTPException, NotFound):
                    await ctx.warn(f"Failed to remove **emote**: {emoji.name}")
                    continue

        await ctx.approve(
            f"Removed **{Plural(len(emojis_removed)):emote}** from the server"
        )

    @emoji.command(
        name="removeduplicates",
        aliases=["rmdups"],
        example="hella_emotes_here",
    )
    @has_permissions(manage_emojis=True)
    @cooldown(1, 120, BucketType.guild)
    async def emoji_remove_duplicates(self, ctx: Context):
        """
        Remove duplicates of emotes
        """
        emojis = ctx.guild.emojis
        if not emojis:
            return await ctx.warn("This server has no emojis!")

        emoji_map = {}
        for emoji in emojis:
            key = (emoji.name.lower(), emoji.animated)
            if key not in emoji_map:
                emoji_map[key] = []
            emoji_map[key].append(emoji)

        duplicates = {
            key: emojis[1:] for key, emojis in emoji_map.items() if len(emojis) > 1
        }

        if not duplicates:
            return await ctx.warn("No duplicate emojis found in this server!")

        total_duplicates = sum(len(dupes) for dupes in duplicates.values())

        confirmation = await ctx.confirm(
            f"Found **{total_duplicates}** duplicate{'s' if total_duplicates != 1 else ''} "
            f"across **{len(duplicates)}** unique emoji name{'s' if len(duplicates) != 1 else ''}.\n"
            "Would you like to remove them?"
        )

        if not confirmation:
            return await ctx.warn("Duplicate removal cancelled.")

        removed = []
        failed = []

        async with ctx.typing():
            for key, dupes in duplicates.items():
                emoji_name = key[0]
                for emoji in dupes:
                    try:
                        await emoji.delete(
                            reason=f"{ctx.author}: Removing duplicate emoji"
                        )
                        removed.append(emoji)
                    except HTTPException as e:
                        failed.append(emoji.name)
                        print(
                            f"Failed to remove duplicate emoji {emoji.name}: {str(e)}"
                        )
                        continue

        response = []
        if removed:
            response.append(
                f"Successfully removed **{Plural(len(removed)):duplicate emoji}**"
            )
        if failed:
            response.append(f"Failed to remove: {', '.join(failed)}")

        if response:
            await ctx.approve("\n".join(response))
        else:
            await ctx.warn("No **emojis** were removed")

    @emoji.command(
        name="rename",
        usage="(emoji) (new name)",
        example="🦮 daddy",
        aliases=["editname"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_rename(self, ctx: Context, emoji: EmojiFinder, *, new_name: str):
        """
        Renames emote to the new name provided
        """
        try:
            if isinstance(emoji, Emoji):
                guild_emoji = ctx.guild.get_emoji(emoji.id)
            else:
                guild_emoji = emoji

            if not guild_emoji or guild_emoji.guild_id != ctx.guild.id:
                return await ctx.warn(
                    f"**{emoji}** has to be **a part** of this server"
                )

            new_name = new_name.strip().replace(" ", "_")[:32]

            if len(new_name) < 2:
                return await ctx.warn("Emoji name must be at least 2 characters long")

            if new_name == guild_emoji.name:
                return await ctx.warn("That's already the emoji's name")

            old_name = guild_emoji.name

            await guild_emoji.edit(name=new_name, reason=f"{ctx.author}: Emoji renamed")

            await ctx.approve(
                f"Renamed emoji from [`:{old_name}:`]({emoji.url}) to **{new_name}**"
            )

        except Exception:
            return await ctx.warn(f"Failed to rename **{emoji}**")

    @emoji.command(
        name="information",
        aliases=["i", "info"],
        example="discordapp.com/channels/...",
    )
    @has_permissions(manage_emojis=True)
    async def emojiinfo(
        self, ctx: Context, potential_emoji: Union[Message, PartialEmoji, EmojiFinder]
    ) -> Message:
        """
        Display information about an emoji.
        """
        if isinstance(potential_emoji, Message):
            match = DISCORD_EMOJI.match(potential_emoji.content)
            if not match:
                return await ctx.warn("No emoji found in the message")
            emoji = PartialEmoji.from_dict(
                {
                    "animated": bool(match.group("animated")),
                    "name": match.group("name"),
                    "id": int(match.group("id")),
                }
            )
        elif isinstance(potential_emoji, (PartialEmoji, EmojiFinder)):
            emoji = potential_emoji
        else:
            return await ctx.warn("Invalid emoji provided")

        discord_emoji = self.bot.get_emoji(emoji.id)

        guild = discord_emoji.guild if discord_emoji else None

        created_at = utils.snowflake_time(emoji.id)

        emoji_url = f"{emoji.url.split('?')[0]}?size=4096&quality=lossless"

        embed = Embed(title=f"{emoji.name}", color=config.Color.info)
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        embed.add_field(name="ID", value=f"`{emoji.id}`", inline=True)
        embed.add_field(
            name="Guild", value=f"`{guild.name}`" if guild else "`Unknown`", inline=True
        )
        embed.add_field(
            name="Image URL",
            value=f"[**Click here to open the image**]({emoji_url})",
            inline=False,
        )

        # Add usage stats if available
        if guild and guild.id == ctx.guild.id:
            query = "SELECT uses FROM emoji_stats WHERE guild_id = $1 AND emoji_id = $2"
            record = await self.bot.db.fetchrow(query, ctx.guild.id, str(emoji.id))
            if record:
                embed.add_field(
                    name="Server Usage",
                    value=f"`{record['uses']:,}` times",
                    inline=True,
                )

        # Set the high quality image
        embed.set_image(url=emoji_url)

        return await ctx.send(embed=embed)

    @command(
        aliases=["whois", "uinfo", "info", "ui"],
        example="@johndoe",
        notes="User ID available",
    )
    async def userinfo(self, ctx: Context, *, user: Member | User = None):
        """
        View information about a member or yourself
        """
        user = user or ctx.author

        if isinstance(user, Member):
            color = user.top_role.color
        else:
            color = config.Color.baseColor

        embed = Embed(color=color)
        embed.title = f"{user} ({user.id})"
        embed.description = ""
        embed.set_thumbnail(url=user.display_avatar)

        # badgest bitch !
        if not user.bot:
            badges: List[str] = []

            if isinstance(user, User) and user.banner:
                badges.extend([EMOJIS.BADGES.NITRO, EMOJIS.BADGES.BOOST])

            elif user.display_avatar.is_animated():
                badges.append(EMOJIS.BADGES.NITRO)

            if EMOJIS.BADGES.BOOST not in badges:
                for guild in user.mutual_guilds:
                    member = guild.get_member(user.id)
                    if not member:
                        continue

                    if member.premium_since:
                        if EMOJIS.BADGES.NITRO not in badges:
                            badges.append(EMOJIS.BADGES.NITRO)

                        badges.append(EMOJIS.BADGES.BOOST)
                        break

            for flag in user.public_flags:
                if flag[1] and (badge := getattr(EMOJIS.BADGES, flag[0].upper(), None)):
                    badges.append(badge)

            if badges:
                embed.description = " ".join(badges) + "\n"

        created_at_field = (
            f"**Created:** {format_dt(user.created_at, 'D')}"
            f" ({format_dt(user.created_at, 'R')})"
        )

        if isinstance(user, Member) and user.joined_at:
            created_at_field += (
                f"\n**Joined:** {format_dt(user.joined_at, 'D')}"
                f" ({format_dt(user.joined_at, 'R')})"
            )

        if isinstance(user, Member) and user.premium_since:
            created_at_field += (
                f"\n**Boosted:** {format_dt(user.premium_since, 'D')}"
                f" ({format_dt(user.premium_since, 'R')})"
            )

        embed.add_field(
            name="**Dates**",
            value=created_at_field,
            inline=False,
        )

        if isinstance(user, Member) and user.joined_at:
            join_pos = sorted(
                user.guild.members,
                key=lambda member: member.joined_at or utcnow(),
            ).index(user)

            if roles := user.roles[1:]:
                embed.add_field(
                    name=f"**Roles ({len(roles)})**",
                    value=", ".join(role.mention for role in list(reversed(roles))[:5])
                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else ""),
                    inline=False,
                )

            if (voice := user.voice) and voice.channel:
                members = len(voice.channel.members) - 1
                phrase = (
                    "**Streaming inside**"
                    if voice.self_stream
                    else "**In voice chat:**"
                )
                embed.description += f"{phrase} {voice.channel.mention} " + (
                    f"with {Plural(members):other}" if members else "by themselves"
                )

            for activity_type, activities in groupby(
                user.activities,
                key=lambda activity: activity.type,
            ):
                activities = list(activities)

                if activities and isinstance(activities[0], Streaming):
                    embed.description += "\n Streaming " + human_join(
                        [
                            f"[**{activity.name}**]({activity.url})"
                            for activity in activities
                            if isinstance(activity, Streaming)
                        ],
                        final="and",
                    )
                elif activity_type == ActivityType.playing:
                    embed.description += "\n Playing " + human_join(
                        [f"**{activity.name}**" for activity in activities],
                        final="and",
                    )
                elif activity_type == ActivityType.watching:
                    embed.description += "\n Watching " + human_join(
                        [f"**{activity.name}**" for activity in activities],
                        final="and",
                    )
                elif activity_type == ActivityType.competing:
                    embed.description += "\n Competing in " + human_join(
                        [f"**{activity.name}**" for activity in activities],
                        final="and",
                    )

            footer_text = f"Join Position: {join_pos + 1} ∙ {len(user.mutual_guilds)} Mutual Servers"
        else:
            footer_text = f"{len(user.mutual_guilds)} Mutual Servers"

        embed.set_footer(
            text=footer_text,
            icon_url=user.display_avatar,
        )

        return await ctx.send(embed=embed)
