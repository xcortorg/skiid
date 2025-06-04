import datetime
from asyncpg import UndefinedTableError
import discord
import config
import os

from logging import getLogger
from main import Evict

from discord.ext.commands import Cog
from discord.ext import tasks
from discord import (
    abc,
    Embed,
    Guild,
    HTTPException,
    Message,
    Member,
    User
)

from discord.ui import View, Button

from aiohttp import ClientError
from typing import cast
from contextlib import suppress

log = getLogger(__name__)

class Listeners(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.avatar_stats = {}
        self.cleanup_interval = 3600
        self.clear_old_stats.start()
        self.update_topgg_stats.start()
        self.topgg_auth = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEyMDM1MTQ2ODQzMjY4MDU1MjQiLCJib3QiOnRydWUsImlhdCI6MTczNjE4MTU1OH0.KJfJoppRkU9SPTflDlgijj1GAGSBEOrHfPRMNc3M6tc"

    async def upload_to_cdn(self, file_data: bytes, user_id: int, avatar_hash: str, file_extension: str) -> str:
        """
        Upload an insert the avatar to EvictCDN.
        """
        directory = f"/root/cdn.evict.bot/cdn_root/images/avatars/{user_id}"
        file_path = f"{directory}/{avatar_hash}.{file_extension}"
        avatar_url = f"https://cdn.evict.bot/images/avatars/{user_id}/{avatar_hash}.{file_extension}"

        try:
            os.makedirs(directory, exist_ok=True)
            with open(file_path, "wb") as file:
                file.write(file_data)

            await self.bot.db.execute(
                    """
                    INSERT INTO avatar_history 
                    (user_id, avatar_url, timestamp) 
                    VALUES ($1, $2, $3)
                    """,
                    user_id, 
                    avatar_url, 
                    datetime.datetime.utcnow()
                )

        except Exception as e:
            log.error(f"Failed to upload avatar for user {user_id}: {e}")
            return ""

        return avatar_url

    async def store_avatar_hash(self, user_id: int, avatar_hash: str, bunny_url: str) -> None:
        """
        Store avatar hash for the user in the database.
        """
        try:
            await self.bot.db.execute(
                """
                INSERT INTO avatar_history 
                (user_id, avatar_url, timestamp)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id, avatar_url) DO NOTHING
                """,
                user_id,
                bunny_url
            )
        
        except Exception as e:
            log.error(f"Failed to store avatar hash for user {user_id}: {e}")

    @Cog.listener()
    async def on_user_update(self, before: User, after: User) -> None:
        """
        Event listener for user avatar updates.
        """
        if before.avatar == after.avatar or before.avatar is None or after.default_avatar == after.avatar.url:
            return

        enabled = await self.bot.db.fetchval(
            """
            SELECT enabled 
            FROM avatar_history_settings 
            WHERE user_id = $1
            """,
            before.id
        )
        
        if not enabled:
            return
        
        log.info(f"Processing avatar update for user {before.id}")
        
        try:
            stored_avatar = await self.bot.db.fetchrow(
                """
                SELECT avatar_hash, avatar_url 
                FROM avatar_current 
                WHERE user_id = $1
                """,
                before.id
            )
            
            if after.avatar:
                avatar_bytes = await after.avatar.read()
                file_extension = "gif" if after.avatar.is_animated() else "png"
                avatar_hash = str(after.avatar.key)
                
                avatar_url = await self.upload_to_cdn(
                    avatar_bytes,
                    after.id,
                    avatar_hash,
                    file_extension
                )
                
                if avatar_url:
                    if stored_avatar:
                        await self.store_avatar_hash(after.id, stored_avatar['avatar_hash'], stored_avatar['avatar_url'])
                    
                    await self.bot.db.execute(
                        """
                        INSERT INTO avatar_current (user_id, avatar_hash, avatar_url)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id) DO UPDATE 
                        SET avatar_hash = $2, avatar_url = $3, last_updated = NOW()
                        """,
                        after.id,
                        avatar_hash,
                        avatar_url
                    )
                    
                    if after.id not in self.avatar_stats:
                        self.avatar_stats[after.id] = {"changes": 0, "total_size": 0}
                    self.avatar_stats[after.id]["changes"] += 1
                    self.avatar_stats[after.id]["total_size"] += len(avatar_bytes)
                    
            log.info(f"Successfully processed avatar update for user {before.id}")
            
        except Exception as e:
            log.error(f"Failed to process avatar for user {before.id}: {e}")

    @Cog.listener()
    async def on_user_update(self, before: User, after: User) -> None:
        """
        Event listener for user avatar updates.
        """
        if (before.avatar == after.avatar or 
            before.avatar is None or 
            after.default_avatar == after.avatar):
            return

        enabled = await self.bot.db.fetchval(
            """
            SELECT enabled 
            FROM avatar_history_settings 
            WHERE user_id = $1
            """,
            before.id
        )
        
        if not enabled:
            return

        log.info(f"Processing avatar update for user {before.id}")
        
        try:
            stored_avatar = await self.bot.db.fetchrow(
                """
                SELECT avatar_hash, avatar_url 
                FROM avatar_current 
                WHERE user_id = $1
                """,
                before.id
            )
            
            if after.avatar:
                avatar_bytes = await after.avatar.read()
                file_extension = "gif" if after.avatar.is_animated() else "png"
                avatar_hash = str(after.avatar.key)
                
                avatar_url = await self.upload_to_cdn(
                    avatar_bytes,
                    after.id,
                    avatar_hash,
                    file_extension
                )
                
                if avatar_url:
                    if stored_avatar:
                        await self.store_avatar_hash(after.id, stored_avatar['avatar_hash'], stored_avatar['avatar_url'])
                    
                    await self.bot.db.execute(
                        """
                        INSERT INTO avatar_current (user_id, avatar_hash, avatar_url)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id) DO UPDATE 
                        SET avatar_hash = $2, avatar_url = $3, last_updated = NOW()
                        """,
                        after.id,
                        avatar_hash,
                        avatar_url
                    )
                    
                    if after.id not in self.avatar_stats:
                        self.avatar_stats[after.id] = {"changes": 0, "total_size": 0}
                    self.avatar_stats[after.id]["changes"] += 1
                    self.avatar_stats[after.id]["total_size"] += len(avatar_bytes)
                    
            log.info(f"Successfully processed avatar update for user {before.id}")
            
        except Exception as e:
            log.error(f"Failed to process avatar for user {before.id}: {e}")

    @tasks.loop(hours=1)
    async def clear_old_stats(self):
        """
        Periodically clear avatar stats to prevent memory bloat.
        """
        self.avatar_stats.clear()

    @Cog.listener("on_guild_join")
    async def guild_join_logger(self, guild: Guild):
        await self.log_guild_event(guild, "joined")

    @Cog.listener("on_guild_remove")
    async def guild_leave_logger(self, guild: Guild):
        await self.log_guild_event(guild, "left")

    async def log_guild_event(self, guild: Guild, event_type: str) -> Message:
        """
        Log guild join or leave events to a channel.
        """
        channel = self.bot.get_channel(config.LOGGER.GUILD_JOIN_LOGGER)
        if not channel:
            return

        cache_key = f"guild_stats:{guild.id}"
        stats = await self.bot.redis.get(cache_key)
        
        if not stats:
            guild_data = {
                'members': [{'bot': m.bot} for m in guild.members],
                'member_count': guild.member_count
            }
            
            stats = await self.bot.process_data(
                'guild_data',
                guild_data
            )
            await self.bot.redis.set(cache_key, stats, ex=300)

        icon = f"[icon]({guild.icon.url})" if guild.icon else "N/A"
        splash = f"[splash]({guild.splash.url})" if guild.splash else "N/A"
        banner = f"[banner]({guild.banner.url})" if guild.banner else "N/A"

        embed = Embed(
            timestamp=datetime.datetime.now(),
            description=f"Evict has {'joined' if event_type == 'joined' else 'left'} a guild."
        )
        embed.set_thumbnail(url=guild.icon)
        embed.set_author(name=guild.name, url=guild.icon)
        
        fields = {
            "Owner": f"{guild.owner.mention}\n{guild.owner}",
            "Members": (
                f"**Users:** {stats['user_count']} ({stats['user_percentage']:.2f}%)\n"
                f"**Bots:** {stats['bot_count']} ({stats['bot_percentage']:.2f}%)\n"
                f"**Total:** {guild.member_count}"
            ),
            "Information": (
                f"**Verification:** {guild.verification_level}\n"
                f"**Boosts:** {guild.premium_subscription_count} (level {guild.premium_tier})\n"
                f"**Large:** {'yes' if guild.large else 'no'}"
            ),
            "Design": f"{icon}\n{splash}\n{banner}",
            f"Channels ({len(guild.channels)})": (
                f"**Text:** {len(guild.text_channels)}\n"
                f"**Voice:** {len(guild.voice_channels)}\n"
                f"**Categories:** {len(guild.categories)}"
            ),
            "Counts": (
                f"**Roles:** {len(guild.roles)}/250\n"
                f"**Emojis:** {len(guild.emojis)}/{guild.emoji_limit * 2}\n"
                f"**Stickers:** {len(guild.stickers)}/{guild.sticker_limit}"
            )
        }
        
        for name, value in fields.items():
            embed.add_field(name=name, value=value)

        embed.set_footer(text=f"Guild ID: {guild.id}")
        if guild.banner:
            embed.set_image(url=guild.banner)

        view = None
        if guild.vanity_url_code:
            view = View()
            view.add_item(Button(label="Invite", url=f"https://discord.gg/{guild.vanity_url_code}"))

        return await channel.send(embed=embed, view=view, silent=True)

    @Cog.listener("on_guild_join")
    async def join_message(self, guild: Guild) -> Message:
        """
        Set a custom join message upon bot join.
        """
        embed = Embed(
            title="Getting Started With Evict",
            description=(
                "Hey! Thanks for your interest in **evict bot**. "
                "The following will provide you with some tips on how to get started with your server!"
            ),
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.add_field(
            name="**Prefix 🤖**",
            value=(
                "The most important thing is my prefix. "
                f"It is set to `;` by default for this server and it is also customizable, "
                "so if you don't like this prefix, you can always change it with `prefix` command!"
            ),
            inline=False,
        )

        embed.add_field(
            name="**Documentation and Help 📚**",
            value=(
                "You can always visit our [documentation](https://docs.evict.bot)"
                " and view the list of commands that are available [here](https://evict.bot/commands)"
                " - and if that isn't enough, feel free to join our [Support Server](https://discord.gg/evict) for extra assistance!"
            ),
        )

        await self.bot.notify(guild, embed=embed)
        try:
            await guild.owner.send(embed=embed)
        except discord.Forbidden:
            pass

    @Cog.listener("on_guild_join")
    async def blacklist_check(self, guild: Guild) -> None:
        """
        Check if a server or server owner is blacklisted upon join.
        """
        guild_blacklisted = cast(
            bool,
            await self.bot.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM guildblacklist
                    WHERE guild_id = $1
                )
                """,
                guild.id,
            ),
        )
        
        owner_blacklisted = cast(
            bool,
            await self.bot.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM blacklist
                    WHERE user_id = $1
                )
                """,
                guild.owner_id,
            ),
        )
        if guild_blacklisted or owner_blacklisted:
            with suppress(HTTPException):
                await guild.leave()
            return

    @Cog.listener("on_guild_channel_create")
    async def jail(self, channel: abc.GuildChannel):
        """
        Set jail permissions when a new channel is created.
        """
        cache_key = f"jail_role:{channel.guild.id}"
        role_id = await self.bot.redis.get(cache_key)
        
        if role_id is None:
            check = await self.bot.db.fetchrow(
                """
                SELECT role_id 
                FROM mod 
                WHERE guild_id = $1
                """,
                channel.guild.id
            )
            if not check:
                return
                
            role_id = check['role_id']
            await self.bot.redis.set(cache_key, role_id, ex=300)

        if role_id is None:
            return

        role = channel.guild.get_role(int(role_id))
        if not role:
            return

        try:
            perms = await self.bot.process_data(
                'jail_permissions',
                channel.id,
                role.id
            )
            
            await channel.set_permissions(
                role,
                reason="overwriting permissions for jail role",
                **perms
            )
        except Exception as e:
            log.error(f"Failed to set jail permissions: {e}")

    @Cog.listener("on_member_join")
    async def join_jail(self, member: Member):
        """
        Rejail a member upon member join.
        """
        cache_key = f"jail_member:{member.guild.id}:{member.id}"
        is_jailed = await self.bot.redis.get(cache_key)
        
        if is_jailed is None:
            check = await self.bot.db.fetchrow(
                """
                SELECT * FROM jail 
                WHERE guild_id = $1 
                AND user_id = $2
                """,
                member.guild.id, member.id
            )
            is_jailed = bool(check)
            await self.bot.redis.set(cache_key, int(is_jailed), ex=300)
            
        if not is_jailed:
            return
            
        role_id = await self.bot.redis.get(f"jail_role:{member.guild.id}")
        if role_id is None:
            chec = await self.bot.db.fetchrow(
                """
                SELECT role_id 
                FROM mod 
                WHERE guild_id = $1
                """,
                member.guild.id
            )
            if not chec:
                return
                
            role_id = chec['role_id']
            await self.bot.redis.set(f"jail_role:{member.guild.id}", role_id, ex=300)
            
        try:
            role = member.guild.get_role(int(role_id))
            if role:
                await self.bot.process_data('add_role', member, role, reason="jailed before leaving")
        except (discord.Forbidden): # 
            pass
    
    @Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} cog has been loaded")

    @tasks.loop(minutes=30)
    async def update_topgg_stats(self):
        url = f"https://top.gg/api/bots/{self.bot.user.id}/stats"
        headers = {"Authorization": self.topgg_auth}
        payload = {
            "server_count": len(self.bot.guilds),
            "user_count": sum(g.member_count for g in self.bot.guilds)
        }
        
        try:
            async with self.bot.session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    log.error(f"Failed to update Top.gg stats: {resp.status}")
        except ClientError as e:
            log.error(f"Failed to update Top.gg stats: {e}")

    @update_topgg_stats.before_loop
    async def before_update_topgg_stats(self):
        await self.bot.wait_until_ready()