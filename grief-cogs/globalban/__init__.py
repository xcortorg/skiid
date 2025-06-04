from logging import getLogger
from typing import List, Optional, Union

import discord

from grief.core import Config, commands
from grief.core.bot import Grief
from grief.core.utils import chat_formatting as chat
from grief.core.utils.menus import DEFAULT_CONTROLS, menu

from .converters import ActionReason, MemberID

logger = getLogger("grief.globalban")


class GlobalBan(commands.Cog):
    """Hardban users to make sure they remain banned."""

    def get_avatar_url(self, user: Union[discord.User, discord.Member]) -> str:
        if discord.version_info.major == 1:
            return user.avatar_url
        return user.display_avatar.url

    def __init__(self, bot: Grief):
        self.bot: Grief = bot
        self.config = Config.get_conf(
            self, identifier=0x33039392, force_registration=True
        )
        self.config.register_global(**{"banned": [], "reasons": {}})
        self.config.register_guild(**{"banned": []})

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def globalban(
        self,
        ctx: commands.Context,
        user: MemberID,
        *,
        reason: Optional[ActionReason] = None,
    ) -> None:
        """Ban a user globally from all servers grief is in."""
        if not reason:
            reason = f"Global ban by {ctx.author} (ID: {ctx.author.id})"
        async with self.config.banned() as f:
            if user.id not in f:
                f.append(user.id)
        old_conf = await self.config.reasons()
        old_conf[user.id] = reason
        await self.config.reasons.set(old_conf)
        banned_guilds: List[discord.Guild] = []
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=reason)
            except (discord.HTTPException, discord.Forbidden):
                await guild.leave()
            finally:
                banned_guilds.append(guild)
        await ctx.reply(
            embed=discord.Embed(
                description=f"Banned {user} from {len(banned_guilds)}/{len(self.bot.guilds)} guilds."
            )
        )

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def globalkick(
        self,
        ctx: commands.Context,
        user: MemberID,
        *,
        reason: Optional[ActionReason] = None,
    ) -> None:
        """Kick a user globally from all servers grief is in."""
        if not reason:
            reason = f"Global kick by {ctx.author} (ID: {ctx.author.id})"
        async with self.config.banned() as f:
            if user.id not in f:
                f.append(user.id)
        old_conf = await self.config.reasons()
        old_conf[user.id] = reason
        await self.config.reasons.set(old_conf)
        banned_guilds: List[discord.Guild] = []
        for guild in self.bot.guilds:
            try:
                await guild.kick(user, reason=reason)
            finally:
                banned_guilds.append(guild)
        await ctx.reply(
            embed=discord.Embed(
                description=f"Kicked {user} from {len(banned_guilds)}/{len(self.bot.guilds)} guilds."
            )
        )

    @commands.command()
    @commands.is_owner()
    async def globalunban(
        self,
        ctx: commands.Context,
        user: MemberID,
        *,
        reason: Optional[ActionReason] = None,
    ) -> None:
        """Unban a user globally from all servers grief is in."""
        if not reason:
            reason = f"Global unban by {ctx.author} (ID: {ctx.author.id})"
        async with self.config.banned() as f:
            if user.id in f:
                f.remove(user.id)
        unbanned_guilds: List[discord.Guild] = []
        couldnt_unban: List[discord.Guild] = []
        for guild in self.bot.guilds:
            try:
                await guild.unban(user, reason=reason)
            except (discord.HTTPException, discord.Forbidden):
                couldnt_unban.append(guild)
            finally:
                unbanned_guilds.append(guild)
        await ctx.reply(
            embed=discord.Embed(
                description=f"Unbanned {user} from {len(unbanned_guilds)}/{len(self.bot.guilds)} guilds."
            )
        )

    @commands.command()
    @commands.guildowner()
    @commands.guild_only()
    async def hardban(
        self,
        ctx: commands.Context,
        user: MemberID,
        *,
        reason: Optional[ActionReason] = None,
    ) -> None:
        """Hard ban a user from current server."""
        if user.id in self.bot.owner_ids:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: You cannot hardban the bot owner.",
                color=0x313338,
            )
            return await ctx.reply(embed=embed, mention_author=False)
        if not reason:
            reason = f"Hard ban by {ctx.author} (ID: {ctx.author.id})"
        async with self.config.guild(ctx.guild).banned() as f:
            if user.id not in f:
                f.append(user.id)
        try:
            await ctx.guild.ban(user, reason=reason)
        except (discord.HTTPException, discord.Forbidden):
            embed = discord.Embed(
                description=f"> Couldn't hardban {user}.", color=0x313338
            )
            await ctx.reply(embed=embed, mention_author=False)
        embed = discord.Embed(description=f"> Hard banned {user}.", color=0x313338)
        return await ctx.reply(embed=embed, mention_author=False)

    @commands.command()
    @commands.guildowner()
    @commands.guild_only()
    async def hardunban(
        self,
        ctx: commands.Context,
        user: MemberID,
        *,
        reason: Optional[ActionReason] = None,
    ) -> None:
        """Unban a hard banned user from current server."""
        if not reason:
            reason = f"Hard unban by {ctx.author} (ID: {ctx.author.id})"
        async with self.config.guild(ctx.guild).banned() as f:
            if user.id in f:
                f.remove(user.id)
        try:
            await ctx.guild.unban(user, reason=reason)
        except (discord.HTTPException, discord.Forbidden):
            return await ctx.reply(
                embed=discord.Embed(description="Couldn't unban {user}.")
            )
        await ctx.reply(embed=discord.Embed(description=f"Unbanned {user}."))

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def listglobalban(self, ctx: commands.Context) -> None:
        """List all global banned users."""
        message: str = ""
        pages: List[str] = []
        async with self.config.banned() as ff:
            if len(ff) == 0:
                return await ctx.send("No user has been globally banned.")
            for x in ff:
                x = await self.bot.get_or_fetch_user(x)
                message += f"{str(x)} - ({x.id})"
        for page in chat.pagify(message):
            pages.append(page)
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @commands.command()
    @commands.guildowner()
    @commands.guild_only()
    async def listhardban(self, ctx: commands.Context) -> None:
        """List all hard banned users."""
        message: str = ""
        pages: List[str] = []
        async with self.config.guild(ctx.guild).banned() as ff:
            if len(ff) == 0:
                return await ctx.send("No user has been hard banned.")
            for x in ff:
                x = await self.bot.get_or_fetch_user(x)
                message += f"{str(x)} - ({x.id})"
        for page in chat.pagify(message):
            pages.append(page)
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """
        Ban global banned users auto-fucking-matically
        """
        global_banned = await self.config.banned()
        guild_banned = await self.config.guild(guild).banned()
        global_reason = (await self.config.reasons()).get(user.id)

        if user.id in global_banned:
            try:
                await guild.ban(
                    user,
                    reason=(
                        global_reason
                        if global_reason
                        else "User cannot be unbanned. Global ban enforced for this user."
                    ),
                )
            except (discord.HTTPException, discord.Forbidden) as e:
                logger.exception(e)
        if user.id in guild_banned:
            try:
                await guild.ban(user, reason="Hard banned by bot owner.")
            except (discord.HTTPException, discord.Forbidden) as e:
                logger.exception(e)
                if not guild.me.guild_permissions.ban_members:
                    await guild.leave()
                await guild.ban(user)
            except discord.HTTPException:
                await guild.leave()

    @commands.Cog.listener()
    async def on_guild_role_update(
        self, before: discord.Role, after: discord.Role
    ) -> None:
        if not after.is_bot_managed():
            return
        if after.members and after.members[0].id != self.bot.user.id:
            return
        if not after.guild.me.guild_permissions.administrator:
            logger.info(
                f"Leaving {after.guild.name}/{after.guild.id} as they removed administrator permission from me."
            )
            try:
                await after.guild.leave()
            except discord.NotFound:
                return

    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if after.id != self.bot.user.id:
            return
        if not after.guild_permissions.administrator:
            logger.info(
                f"Leaving {after.guild.name}/{after.guild.id} as they removed administrator permission from me."
            )
            try:
                await after.guild.leave()
            except discord.NotFound:
                return

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """
        Automatically unban a bot owner.
        """

        if user.id in self.bot.owner_ids:
            try:
                await guild.unban(
                    user,
                    reason="User cannot be banned. Kick Grief to ban this user.",
                )
            except (discord.HTTPException, discord.Forbidden) as e:
                logger.exception(e)
        if not guild.me.guild_permissions.administrator:
            await guild.leave()

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """
        Ban global banned users auto-fucking-matically
        """
        global_banned = await self.config.banned()
        guild_banned = await self.config.guild(guild).banned()
        global_reason = (await self.config.reasons()).get(user.id)

        if user.id in global_banned:
            try:
                await guild.ban(
                    user,
                    reason=(
                        global_reason
                        if global_reason
                        else "User cannot be unbanned. Global ban enforced for this user."
                    ),
                )
            except (discord.HTTPException, discord.Forbidden) as e:
                logger.exception(e)

        if user.id in guild_banned:
            try:
                await guild.ban(user, reason="Hard banned by bot owner.")
            except (discord.HTTPException, discord.Forbidden) as e:
                logger.exception(e)
                if not guild.me.guild_permissions.administrator:
                    await guild.leave()
                await guild.ban(user)
            except discord.HTTPException:
                await guild.leave()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        global_banned = await self.config.banned()
        guild = member.guild
        if member.id in global_banned:
            try:
                await guild.ban(
                    member,
                    reason="User cannot be unbanned. Kick Grief to unban this user.",
                )
            except (discord.HTTPException, discord.Forbidden):
                await guild.leave()
        if not guild.me.guild_permissions.administrator:
            await guild.leave()


async def setup(bot: Grief):
    cog = GlobalBan(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)
