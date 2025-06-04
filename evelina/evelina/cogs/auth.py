import discord
import datetime

from discord.ext.commands import Cog, AutoShardedBot

from modules.styles import colors, icons, emojis
from modules.evelinabot import Evelina

class Auth(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if not self.bot.is_ready():
            return
        await guild.chunk(cache=True)
        await self.guild_change("joined", guild)
        check_blacklist = await self.bot.db.fetchrow("SELECT * FROM blacklist_server WHERE guild_id = $1", guild.id)
        if check_blacklist:
            now = datetime.datetime.now().timestamp()
            duration = check_blacklist["duration"]
            timestamp = check_blacklist["timestamp"]
            if duration is None or now < timestamp + duration:
                if channel := next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None):
                    embed = discord.Embed(color=colors.ERROR, description=f"{emojis.DENY} **{guild.name}** is blacklisted from evelina.")
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass
                try:
                    return await guild.leave()
                except Exception:
                    pass
                
        if channel := next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None):
           join_embed = (discord.Embed(color=colors.NEUTRAL, description=f"# Hi, I am Evelina!\nThe team behind Evelina is happy about your decision to use our bot!"))
           join_embed.set_author(name=f"Evelina", icon_url=icons.EVELINA, url="https://evelina.bot")
           join_embed.add_field(name="Prefix", value="Default prefix is `;`\nYou can change it by using:\n`;prefix set [new_prefix]`")
           join_embed.add_field(name="Commands", value="[`;setjail`](https://docs.evelina.bot/security/moderation)\n[`;setmute`](https://docs.evelina.bot/security/moderation)\n[`;vm setup`](https://docs.evelina.bot/server/voicemaster)")
           join_embed.add_field(name="Help", value="[`Commands`](https://evelina.bot/commands)\n[`Documentation`](https://docs.evelina.bot)\n[`Support Server`](https://discord.gg/evelina)")
           try:
               await channel.send(embed=join_embed)
           except Exception:
               pass
        return await self.owner_check(guild.owner)

    @Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        if not self.bot.is_ready():
            return
        await guild.chunk(cache=True)
        await self.guild_change("left", guild)
        #return await self.owner_check(guild.owner)

    async def guild_change(self, state: str, guild: discord.Guild):
        try:
            if state == 'joined':
                color = colors.JOINED
            elif state == 'left':
                color = colors.LEFT
            if guild.member_count is None:
                return
            embed = discord.Embed(description=f"{state.capitalize()} **{guild.name}** with **{guild.member_count}** members", color=color)
            embed.add_field(name="Guild", value=f"```{guild.name} ({guild.id})```", inline=True)
            embed.add_field(name="Owner", value=f"```{guild.owner} ({guild.owner.id})```", inline=True)
            embed.set_footer(text=f"Server count: {len(self.bot.guilds):,} - User count: {sum(g.member_count if g.member_count is not None else 0 for g in self.bot.guilds):,}")
            if state == "joined":
                adder = None
                try:
                    async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.bot_add):
                        if entry.target.id == self.bot.user.id:
                            adder = entry.user
                            break
                except Exception:
                    pass
                if adder:
                    embed.description = f"{state.capitalize()} **{guild.name}** with **{guild.member_count}** members\n> Added by: {adder} (`{adder.id}`)"
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_joinleave)
            if channel:
                await channel.send(embed=embed)
        except Exception:
            pass

    async def owner_check(self, user: discord.User):
        try:
            if len(user.mutual_guilds) == 0:
                return False
            is_owner = any(g.owner_id == user.id for g in user.mutual_guilds)
            evelina_guild = self.bot.get_guild(self.bot.logging_guild)
            evelina_role = evelina_guild.get_role(1242509393308946503)
            evelina_member = evelina_guild.get_member(user.id)
            if not evelina_member:
                return False
            if is_owner:
                if evelina_role not in evelina_member.roles:
                    await evelina_member.add_roles(evelina_role, reason="Command | Server Owner role synchronization")
                return True
            else:
                if evelina_role in evelina_member.roles:
                    await evelina_member.remove_roles(evelina_role, reason="Command | Server Owner role synchronization")
                return False
        except Exception:
            pass

async def setup(bot: AutoShardedBot) -> None:
    await bot.add_cog(Auth(bot))