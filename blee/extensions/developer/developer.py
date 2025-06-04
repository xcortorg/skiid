import subprocess
from traceback import format_exception
from typing import Optional

from discord import Embed, Member, Message, User
from discord.ext.commands import (Cog, ExtensionAlreadyLoaded, ExtensionFailed,
                                  ExtensionNotFound, ExtensionNotLoaded,
                                  command, group)
from discord.utils import format_dt
from tools import Bleed
from tools.client.context import Context


class CustomError(Exception):
    pass


class Developer(Cog):
    def __init__(self, bot: Bleed):
        self.bot: Bleed = bot

    async def cog_check(self: "Developer", ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @command(
        name="traceback",
        usage="[error id]",
        example="NrnMZEYuV5g",
        aliases=["trace"],
    )
    async def traceback(self: "Developer", ctx: Context, _id: Optional[str] = None):
        """
        Get the traceback of an error.
        If no ID is provided, shows the most recent error.
        """
        if _id:
            query = "SELECT * FROM traceback WHERE error_id = $1"
            params = (_id,)
        else:
            query = "SELECT * FROM traceback ORDER BY timestamp DESC LIMIT 1"
            params = ()

        error = await self.bot.db.fetchrow(query, *params)

        if not error:
            return await ctx.warn(
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

    @command(name="sync")
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

    @command()
    async def restart(self, ctx: Context):
        """
        Restart the bot using PM2.
        """
        await ctx.prompt("Are you sure you wish to restart the bot?")
        try:
            # Add shell=True to handle the command through shell
            # and capture output for better error handling
            result = subprocess.run(
                "pm2 restart blee",
                shell=True,
                check=True,
                capture_output=True,
                text=True,
            )
            await ctx.approve("Bot is restarting...")
        except subprocess.CalledProcessError as e:
            await ctx.warn(
                f"Failed to restart bot:\n```\n{e.stderr or 'Unknown error'}```"
            )

    @group(
        name="donator",
        aliases=["d"],
        example="add fiji",
        invoke_without_command=True,
    )
    async def donator(self: "Developer", ctx: Context):
        """Manage the donators"""
        await ctx.send_help()

    @donator.command(
        name="add",
        usage="(user)",
        example="fiji",
        aliases=["a", "append"],
    )
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
            return await ctx.warn(f"**{user}** is already a **donator**")

        await ctx.approve(f"Added **{user}** to the **donators**")

    @donator.command(
        name="remove",
        usage="(user)",
        example="fiji",
        aliases=["delete", "del", "rm"],
    )
    async def donator_remove(self, ctx: Context, *, user: Member | User):
        """Remove a donator"""
        if not await self.bot.db.fetchval(
            "SELECT user_id FROM donators WHERE user_id = $1", user.id
        ):
            return await ctx.warn(f"**{user}** isn't a **donator**")

        await self.bot.db.execute("DELETE FROM donators WHERE user_id = $1", user.id)

        return await ctx.approve(f"Removed **{user}** from the **donators**")

    @donator.command(
        name="list",
        aliases=["l"],
    )
    async def donator_list(self, ctx: Context):
        """List all the donators"""
        donators = [
            f"**{await self.bot.fetch_user(row['user_id']) or 'Unknown User'}** (`{row['user_id']}`)"
            for row in await self.bot.db.fetch(
                "SELECT user_id FROM donators",
            )
        ]
        if not donators:
            return await ctx.warn("There are no **donators**")

        # Create list of embeds for pagination
        embeds = []
        donators_per_page = 10

        for i in range(0, len(donators), donators_per_page):
            chunk = donators[i : i + donators_per_page]
            embed = Embed(title="Donators", description="\n".join(chunk))
            if len(donators) > donators_per_page:
                embed.set_footer(
                    text=f"Page {i//donators_per_page + 1}/{(len(donators) + donators_per_page - 1) // donators_per_page}"
                )
            embeds.append(embed)

        await ctx.paginate(embeds)
