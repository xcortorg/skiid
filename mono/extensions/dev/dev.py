import json
import os
import secrets
from datetime import datetime
from traceback import format_exception
from typing import Optional

import aiohttp
from core.client.context import Context
from core.managers.paginator import Paginator
from core.Mono import Mono
from discord import (Embed, File, Forbidden, Guild, Member, Message,
                     TextChannel, User)
from discord.errors import HTTPException
from discord.ext.commands import (BucketType, Cog, Command, CommandError,
                                  CommandInvokeError, CommandOnCooldown,
                                  ExtensionAlreadyLoaded, ExtensionFailed,
                                  ExtensionNotFound, ExtensionNotLoaded, Group,
                                  MissingPermissions, UserNotFound, command,
                                  group, is_owner, param)
from discord.utils import format_dt


class CustomError(Exception):
    pass


class Developer(Cog):
    def __init__(self, bot: Mono):
        self.bot: Mono = bot

    async def cog_check(self: "Developer", ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    async def cog_load(self):
        self.bot.blacklist = [
            row["user_id"]
            for row in await self.bot.db.fetch(
                """
                SELECT user_id FROM blacklist
                """,
            )
        ]

    @command()
    async def me2(self: "Developer", ctx: Context) -> None:
        """
        Cleans up our messages :3
        """

        await ctx.message.delete()
        await ctx.channel.purge(
            limit=2e4, check=lambda m: m.author in (self.bot.user, ctx.author)
        )

    @group(
        name="blacklist",
        aliases=["bl"],
        invoke_without_command=True,
    )
    async def blacklist(
        self: "Developer",
        ctx: Context,
        user: Member | User,
        *,
        reason: str = param(
            converter=str,
            default="No reason provided",
            description="The reason for the blacklist.",
        ),
    ) -> None:
        """
        Prevent a user from using the bot.
        """

        if user.id in self.bot.blacklist:
            await self.bot.db.execute(
                """
                DELETE FROM blacklist
                WHERE user_id = $1
                """,
                user.id,
            )
            self.bot.blacklist.remove(user.id)
        else:
            await self.bot.db.execute(
                """
                INSERT INTO blacklist (user_id, reason)
                VALUES ($1, $2)
                """,
                user.id,
                reason,
            )
            self.bot.blacklist.append(user.id)

        await ctx.add_check()

    @blacklist.command(
        name="view",
        aliases=["check"],
    )
    async def blacklist_view(
        self: "Developer",
        ctx: Context,
        *,
        user: Member | User,
    ) -> Message:
        """
        View the reason for a user's blacklist.
        """

        if not (
            reason := await self.bot.db.fetchval(
                """
                SELECT reason
                FROM blacklist
                WHERE user_id = $1
                """,
                user.id,
            )
        ):
            return await ctx.warn(f"`{user}` is not blacklisted!")

        return await ctx.neutral(f"`{user}` was blacklisted for **{reason}**.")

    #    @command(
    #        name="traceback",
    #        aliases=["trace", "tb"],
    #    )
    #    async def traceback(
    #        self: "Developer", ctx: Context, error_code: Optional[str] = None
    #    ) -> Message:
    #        """
    #        View traceback for an error code.
    #        """
    #
    #        if not self.bot.traceback:
    #            return await ctx.warn("There are no stored tracebacks.")
    #
    #        if not error_code:
    #            error_code = list(self.bot.traceback.keys())[-1]
    #
    #        if not (error := self.bot.traceback.get(error_code)):
    #            return await ctx.warn("The provided error code does not exist!")
    #
    #        traceback: str = "".join(error["traceback"])
    #        command: Command = error["command"]
    #        user: User = error["user"]
    #        guild: Guild = error["guild"]
    #        channel: TextChannel = error["channel"]
    #        timestamp: datetime = error["timestamp"]
    #
    #        embed = Embed(
    #            title=f"Traceback for {command}",
    #            description="```py\n" + traceback + "```",
    #        )
    #        embed.add_field(
    #            name="Information",
    #            value=(
    #                f"{format_dt(timestamp)}\n"
    #                f">>> User: **{user}** (`{user.id}`)\n"
    #                f"Guild: **{guild}** (`{guild.id}`)\n"
    #                f"Channel: **{channel}** (`{channel.id}`)\n"
    #            ),
    #        )
    #
    #        return await ctx.send(embed=embed)
    #
    #

    @command(
        name="traceback",
        usage="[error id]",
        example="NrnMZEYuV5g",
        aliases=["trace"],
    )
    async def traceback(self: "Developer", ctx: Context, _id: Optional[str] = None):
        """Get the traceback of an error. If no ID is provided, shows the most recent error."""
        if _id:
            query = "SELECT * FROM traceback WHERE error_id = $1"
            params = (_id,)
        else:
            query = "SELECT * FROM traceback ORDER BY timestamp DESC LIMIT 1"
            params = ()

        error = await self.bot.db.fetchrow(query, *params)

        if not error:
            return await ctx.error(
                f"Couldn't find an error{f' for `{_id}`' if _id else ''}"
            )

        embed = Embed(
            title=f"Command: {error['command']}",
            description=(
                f"**Error ID:** `{error['error_id']}`\n"
                f"**Guild:** {self.bot.get_guild(error['guild_id']) or 'N/A'} (`{error['guild_id']}`)\n"
                f"**User:** {self.bot.get_user(error['user_id']) or 'N/A'} (`{error['user_id']}`)\n"
                f"**Timestamp:** {format_dt(error['timestamp'])}\n"
                f"```py\n{error['traceback']}```"
            ),
        )

        await ctx.send(embed=embed)

    @command(
        name="reload",
        aliases=["rl"],
    )
    async def reload(self: "Developer", ctx: Context, feature: str) -> Message:
        """
        Reload an existing feature.
        """

        try:
            await self.bot.reload_extension(feature)
        except (ExtensionNotFound, ExtensionFailed) as exception:
            traceback = "\n".join(format_exception(exception))

            return await ctx.warn(
                f"> Failed to reload `{feature}`!" f"\n```py\n{traceback}```"
            )
        except ExtensionNotLoaded:
            return await self.load(ctx, feature=feature)

        return await ctx.approve(f"Successfully reloaded `{feature}`.")

    @command(name="load")
    async def load(self: "Developer", ctx: Context, feature: str) -> Message:
        """
        Load an existing feature.
        """

        try:
            await self.bot.load_extension(feature)
        except ExtensionFailed as exception:
            traceback = "\n".join(format_exception(exception))

            return await ctx.warn(
                f"> Failed to load `{feature}`!" f"```py\n{traceback}```"
            )
        except ExtensionNotFound:
            return await ctx.warn(f"`{feature}` doesn't exist!")
        except ExtensionAlreadyLoaded:
            return await ctx.warn(f"`{feature}` is already loaded!")

        return await ctx.approve(f"Successfully loaded `{feature}`.")

    @command(name="unload")
    async def unload(self: "Developer", ctx: Context, feature: str) -> Message:
        """
        Unload an existing feature.
        """

        try:
            await self.bot.unload_extension(feature)
        except (ExtensionNotFound, ExtensionNotLoaded):
            return await ctx.warn(f"`{feature}` is not loaded!")

        return await ctx.approve(f"Successfully unloaded `{feature}`.")

    @command(name="testpaginator")  # New Command
    async def test_paginator(self: "Developer", ctx: Context) -> None:
        """
        Test the paginator with 3 sample pages.
        """
        # Create sample embeds for the paginator
        embeds = [
            Embed(
                title="Page 1", description="This is the first page.", color=0x1ABC9C
            ),
            Embed(
                title="Page 2", description="This is the second page.", color=0x3498DB
            ),
            Embed(
                title="Page 3", description="This is the third page.", color=0x9B59B6
            ),
        ]

        # Initialize the paginator with the embeds and the context as the destination
        paginator = Paginator(embeds, ctx)  # Pass as positional arguments

        # Start the paginator
        await paginator.start()

    @command(name="test_paginate")  # New Command
    async def test_paginate(self: "Developer", ctx: Context) -> None:
        """
        Test the paginate method by sending multiple embeds.
        """
        # Create sample embeds for pagination
        embeds = [
            Embed(
                title="Embed 1",
                description="Content for embed number one.",
                color=0xFF5733,
            ),
            Embed(
                title="Embed 2",
                description="Content for embed number two.",
                color=0x33FF57,
            ),
            Embed(
                title="Embed 3",
                description="Content for embed number three.",
                color=0x3357FF,
            ),
        ]

        # Optionally customize the footer for all embeds
        for embed in embeds:
            if embed.footer and embed.footer.text:
                original_footer = embed.footer.text
                embed.set_footer(text=f"{original_footer} - Paginated")

        # Use ctx.paginate to send the paginated message
        await ctx.paginate(pages=embeds)

    @command(name="test_autopaginator")  # New Command
    async def test_autopaginator(self: "Developer", ctx: Context) -> None:
        """
        Test the autopaginator by automatically splitting a long list of strings into paginated embeds.
        """
        # Sample list of strings to paginate
        descriptions = [
            "Item 1: Description of item one.",
            "Item 2: Description of item two.",
            "Item 3: Description of item three.",
            "Item 4: Description of item four.",
            "Item 5: Description of item five.",
            "Item 6: Description of item six.",
            "Item 7: Description of item seven.",
            "Item 8: Description of item eight.",
            "Item 9: Description of item nine.",
            "Item 10: Description of item ten.",
            "Item 11: Description of item eleven.",
            "Item 12: Description of item twelve.",
            "Item 13: Description of item thirteen.",
            "Item 14: Description of item fourteen.",
            "Item 15: Description of item fifteen.",
            "Item 16: Description of item sixteen.",
            "Item 17: Description of item seventeen.",
            "Item 18: Description of item eighteen.",
            "Item 19: Description of item nineteen.",
            "Item 20: Description of item twenty.",
            "Item 21: Description of item twenty one.",
            "Item 22: Description of item twenty two.",
            "Item 23: Description of item twenty three.",
            "Item 24: Description of item twenty four.",
            "Item 25: Description of item twenty five.",
            "Item 26: Description of item twenty six.",
            "Item 27: Description of item twenty seven.",
            "Item 28: Description of item twenty eight.",
            "Item 19: Description of item nineteen.",
            "Item 20: Description of item twenty.",
        ]

        # Base embed for pagination
        base_embed = Embed(
            title="Autopaginated List",
            description="Here is a list of items:",
            color=0x1ABC9C,
            timestamp=datetime.utcnow(),
        )
        base_embed.set_footer(
            text="Autopaginator Example", icon_url="https://example.com/icon.png"
        )

        # Use ctx.autopaginator to automatically paginate the list of descriptions
        await ctx.autopaginator(embed=base_embed, description=descriptions, split=4)

    @command(name="testerror")
    async def test_error(self, ctx: Context, error_type: str = "generic") -> None:
        """
        Test the error handling system, including traceback logging.
        """
        error_map = {
            "generic": CommandError("This is a test error"),
            "permission": MissingPermissions(["manage_messages"]),
            "notfound": UserNotFound("TestUser"),
            "cooldown": CommandOnCooldown(BucketType.default, 60, 0),
            "traceback": CustomError(
                "This is a custom error that will trigger traceback logging"
            ),
        }

        error = error_map.get(
            error_type, ValueError(f"Unknown test error type: {error_type}")
        )

        # Always wrap the error in CommandInvokeError to trigger traceback logging
        raise CommandInvokeError(error)

    @command(name="exportcommands", brief="owner")
    async def exportcommands(self, ctx: Context):
        """
        Export command information to a JSON file, including subgroups and subcommands.
        """
        commands_info = []

        def extract_command_info(cmd):
            """
            Recursively extract information from a command or group.
            """
            cmd_info = {
                "name": cmd.name,
                "description": cmd.help or "",
                "category": cmd.cog_name or "Uncategorized",
                "permissions": self.get_command_permissions(cmd),
                "parameters": [
                    {"name": param.name, "optional": param.default != param.empty}
                    for param in cmd.clean_params.values()
                ],
            }

            # If the command is a group, extract its subcommands
            if isinstance(cmd, Group):
                subcommands = []
                for sub in cmd.commands:
                    subcommands.append(extract_command_info(sub))
                if subcommands:
                    cmd_info["subcommands"] = subcommands

            return cmd_info

        for command in self.bot.commands:
            # Skip hidden commands if needed
            if not command.hidden:
                commands_info.append(extract_command_info(command))

        # Save to JSON file
        with open("assets/commands_export.json", "w", encoding="utf-8") as f:
            json.dump(commands_info, f, indent=4, ensure_ascii=False)

        await ctx.send(file=File("assets/commands_export.json"))

    @command()
    async def shards(self, ctx: Context):
        """
        Get info about shards
        """
        shard_info = []
        for shard_id, shard in ctx.bot.shards.items():
            shard_info.append(f"Shard {shard_id}: Latency {shard.latency*1000:.2f}ms")

        embed = Embed(title="Shard Information", description="\n".join(shard_info))
        await ctx.autopaginator(embed, shard_info, split=1)

    @group(
        name="system",
        aliases=["sys"],
        description="System commands.",
        invoke_without_command=True,
    )
    async def system(self, ctx: Context):
        return await ctx.send_help(ctx.command.qualified_name)

    @system.command(
        name="restart", aliases=["rs", "reboot"], description="restarts the bot."
    )
    async def system_restart(self, ctx: Context):
        await ctx.approve(f"Restarting bot...")
        os.system("pm2 restart 0")

    @system.command(name="pfp", aliases=["av", "changeav"])
    async def system_avatar(self, ctx: Context, *, image: str = None):
        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        elif image:
            image_url = image
        else:
            return await ctx.warn(f"Please provide an image URL or upload an image.")

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return await ctx.deny(f"Failed to fetch the image.")
                data = await resp.read()

        try:
            await self.bot.user.edit(avatar=data)
            await ctx.approve(f"Changed my **pfp** successfully!")
        except HTTPException as e:
            await ctx.deny(f"Failed to change profile picture: {e}")

    @system.command(name="banner", aliases=["bnr", "changebanner"])
    async def system_banner(self, ctx: Context, *, image: str = None):
        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        elif image:
            image_url = image
        else:
            return await ctx.warn(f"Please provide an image URL or upload an image.")

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return await ctx.deny(f"Failed to fetch the image.")
                data = await resp.read()

        try:
            await self.bot.user.edit(banner=data)
            await ctx.approve(f"Changed my **banner** successfully!")
        except HTTPException as e:
            await ctx.deny(f"Failed to change banner: {e}")

    @command(name="sync")
    async def sync(self, ctx: Context):
        """
        Sync application commands for the current guild.
        """
        await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"Commands synced for guild: {ctx.guild.name}")

    @command(name="syncall")
    async def syncall(self, ctx: Context):
        """
        Sync application commands globally.
        """
        await ctx.bot.tree.sync()
        await ctx.send("Commands synced globally.")

    @command(
        name="mutuals",
    )
    async def mutuals(self, ctx: Context, user: Member | User) -> Message:
        """
        Get shared servers with the bot and a user.
        """
        mutual_guilds = user.mutual_guilds
        if not mutual_guilds:
            return await ctx.warn(f"No mutual servers found with **{user}**.")

        guilds_per_page = 10
        pages = []

        for page, i in enumerate(range(0, len(mutual_guilds), guilds_per_page)):
            guilds_chunk = mutual_guilds[i : i + guilds_per_page]
            embed = Embed(
                title=f"Mutual Servers with {user}",
                description="\n".join(
                    f"{guild.name} (`{guild.id}`)" for guild in guilds_chunk
                ),
            )
            if len(mutual_guilds) > guilds_per_page:
                embed.set_footer(
                    text=f"Page {page+1}/{(len(mutual_guilds) + guilds_per_page - 1) // guilds_per_page} ({len(mutual_guilds)} guilds)"
                )
            pages.append(embed)

        if len(pages) > 2:
            await ctx.paginate(pages)
        else:
            for embed in pages:
                await ctx.send(embed=embed)

    @command(name="guilds", usage="guilds", extras={"example": "guilds"})
    async def guilds(self, ctx: Context):
        """
        List all guilds the bot is in.
        """
        guilds = self.bot.guilds
        if not guilds:
            return await ctx.warn("No guilds found.", reference=ctx.message)

        pages = []
        guilds_per_page = 10

        for page, i in enumerate(range(0, len(guilds), guilds_per_page)):
            guilds_chunk = guilds[i : i + guilds_per_page]
            embed = Embed(
                title="List of Guilds",
                description="\n".join(
                    f"`{i+1:02}` {guild.name} ( `{guild.id}` )"
                    for i, guild in enumerate(guilds_chunk, start=i)
                ),
            )
            if len(guilds) > guilds_per_page:
                embed.set_footer(
                    text=f"Page {page+1}/{(len(guilds) + guilds_per_page - 1) // guilds_per_page} ({len(guilds)} guilds)"
                )
            pages.append(embed)

        await ctx.paginate(pages)

    @command(name="portal", usage="[guild id]", brief="bot owner")
    async def portal(self, ctx, id: int):
        """
        Get an invite to a guild.
        """
        await ctx.message.delete()
        guild = self.bot.get_guild(id)
        if not guild:
            return await ctx.warn(f"**I am not in** `{id}`")
        for c in guild.text_channels:
            if c.permissions_for(guild.me).create_instant_invite:
                invite = await c.create_invite()
                await ctx.author.send(f"{guild.name} invite link - {invite}")
                break

    @group(
        name="donator",
        aliases=["d"],
        example="add igna",
        invoke_without_command=True,
    )
    @is_owner()
    async def donator(self: "Developer", ctx: Context):
        """Manage the donators"""
        await ctx.send_help()

    @donator.command(
        name="add",
        usage="(user)",
        example="igna",
        aliases=["a", "append"],
    )
    @is_owner()
    async def donator_add(
        self: "Developer",
        ctx: Context,
        user: User | Member,
    ):
        """Add a donator"""
        try:
            await self.bot.db.execute(
                "INSERT INTO donators (user_id) VALUES ($1)", user.id
            )
        except Exception:
            return await ctx.error(f"**{user}** is already a **donator**")

        await ctx.approve(f"Added **{user}** to the **donators**")

    @donator.command(
        name="remove",
        usage="(user)",
        example="igna",
        aliases=["delete", "del", "rm"],
    )
    @is_owner()
    async def donator_remove(self, ctx: Context, *, user: Member | User):
        """Remove a donator"""
        if not await self.bot.db.fetchval(
            "SELECT user_id FROM donators WHERE user_id = $1", user.id
        ):
            return await ctx.error(f"**{user}** isn't a **donator**")

        await self.bot.db.execute("DELETE FROM donators WHERE user_id = $1", user.id)

        return await ctx.approve(f"Removed **{user}** from the **donators**")

    @donator.command(
        name="list",
        aliases=["l"],
    )
    @is_owner()
    async def donator_list(self, ctx: Context):
        """List all the donators"""
        donators = [
            f"**{await self.bot.fetch_user(row['user_id']) or 'Unknown User'}** (`{row['user_id']}`)"
            for row in await self.bot.db.fetch(
                "SELECT user_id FROM donators",
            )
        ]
        if not donators:
            return await ctx.error("There are no **donators**")

        await ctx.paginate(
            Embed(
                title="Donators",
                description="\n".join(donators),
            )
        )

    @command(name="clearimagecache")
    async def clear_image_cache(self: "Developer", ctx: Context) -> None:
        """
        Clears the image results cache.
        """
        # Clear the image cache
        await self.bot.cache.delete(
            "GOOGLE:IMAGE:*"
        )  # Adjust this line based on your cache implementation
        await ctx.approve("Image results cache has been cleared.")

    @command(name="leaveserver")
    async def leaveguild(self, ctx: Context, guild_id: int):
        g = self.bot.get_guild(guild_id)
        await g.leave()
        return await ctx.approve(f"Left {g.name}")

    @command()
    async def dm(self, ctx: Context, user: User, *, message: str):
        """DM the user of your choice"""
        try:
            await user.send(message)
            await ctx.add_check()
        except Forbidden:
            await ctx.warn("Cant send DMs to this user")
