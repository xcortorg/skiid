import datetime

import discord
from discord.ext import commands


class Bot(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @commands.Cog.listener("on_guild_join")
    async def gblacklist_check(self, guild: discord.Guild):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM gblacklist WHERE guild_id = {}".format(guild.id)
        )
        if check is not None:
            await guild.leave()

    #   @commands.Cog.listener('on_guild_join')
    #  async def gwhitelist_check(self, guild: discord.Guild):
    #     check = await self.bot.db.fetchrow("SELECT * FROM gwhitelist WHERE guild_id = {}".format(guild.id))
    #    if check is None:
    #       await guild.leave()

    @commands.Cog.listener("on_guild_join")
    async def member_count(self, guild: discord.Guild):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM gwhitelist WHERE guild_id = {}".format(guild.id)
        )
        check1 = await self.bot.db.fetchrow(
            "SELECT * FROM mwhitelist WHERE guild_id = {}".format(guild.id)
        )
        if check1:
            return
        if check is not None:
            return
        if guild.member_count < 50:
            try:
                await guild.leave()
            except discord.NotFound:
                return

    @commands.Cog.listener("on_guild_join")
    async def join_log(self, guild: discord.Guild):
        channel_id = 1209198176008015932
        channel = self.bot.get_channel(channel_id)

        icon = f"[icon]({guild.icon.url})" if guild.icon is not None else "N/A"
        splash = f"[splash]({guild.splash.url})" if guild.splash is not None else "N/A"
        banner = f"[banner]({guild.banner.url})" if guild.banner is not None else "N/A"
        embed = discord.Embed(
            color=self.bot.color,
            timestamp=datetime.datetime.now(),
            description=f"resent has joined a guild.",
        )
        embed.set_thumbnail(url=guild.icon)
        embed.set_author(name=guild.name, url=guild.icon)
        embed.add_field(name="Owner", value=f"{guild.owner.mention}\n{guild.owner}")
        embed.add_field(
            name="Members",
            value=f"**Users:** {len(set(i for i in guild.members if not i.bot))} ({((len(set(i for i in guild.members if not i.bot)))/guild.member_count) * 100:.2f}%)\n**Bots:** {len(set(i for i in guild.members if i.bot))} ({(len(set(i for i in guild.members if i.bot))/guild.member_count) * 100:.2f}%)\n**Total:** {guild.member_count}",
        )
        embed.add_field(
            name="Information",
            value=f"**Verification:** {guild.verification_level}\n**Boosts:** {guild.premium_subscription_count} (level {guild.premium_tier})\n**Large:** {'yes' if guild.large else 'no'}",
        )
        embed.add_field(name="Design", value=f"{icon}\n{splash}\n{banner}")
        embed.add_field(
            name=f"Channels ({len(guild.channels)})",
            value=f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Categories** {len(guild.categories)}",
        )
        embed.add_field(
            name="Counts",
            value=f"**Roles:** {len(guild.roles)}/250\n**Emojis:** {len(guild.emojis)}/{guild.emoji_limit*2}\n**Stickers:** {len(guild.stickers)}/{guild.sticker_limit}",
        )
        embed.set_footer(text=f"Guild ID: {guild.id}")
        if guild.banner:
            embed.set_image(url=guild.banner)
        try:
            await channel.send(embed=embed)
        except:
            return

    @commands.Cog.listener("on_guild_remove")
    async def leave_log(self, guild: discord.Guild):
        channel_id = 1209198176008015932
        channel = self.bot.get_channel(channel_id)

        icon = f"[icon]({guild.icon.url})" if guild.icon is not None else "N/A"
        splash = f"[splash]({guild.splash.url})" if guild.splash is not None else "N/A"
        banner = f"[banner]({guild.banner.url})" if guild.banner is not None else "N/A"
        embed = discord.Embed(
            color=self.bot.color,
            timestamp=datetime.datetime.now(),
            description=f"resent has left a guild.",
        )
        embed.set_thumbnail(url=guild.icon)
        embed.set_author(name=guild.name, url=guild.icon)
        embed.add_field(name="Owner", value=f"{guild.owner.mention}\n{guild.owner}")
        embed.add_field(
            name="Members",
            value=f"**Users:** {len(set(i for i in guild.members if not i.bot))} ({((len(set(i for i in guild.members if not i.bot)))/guild.member_count) * 100:.2f}%)\n**Bots:** {len(set(i for i in guild.members if i.bot))} ({(len(set(i for i in guild.members if i.bot))/guild.member_count) * 100:.2f}%)\n**Total:** {guild.member_count}",
        )
        embed.add_field(
            name="Information",
            value=f"**Verification:** {guild.verification_level}\n**Boosts:** {guild.premium_subscription_count} (level {guild.premium_tier})\n**Large:** {'yes' if guild.large else 'no'}",
        )
        embed.add_field(name="Design", value=f"{icon}\n{splash}\n{banner}")
        embed.add_field(
            name=f"Channels ({len(guild.channels)})",
            value=f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Categories** {len(guild.categories)}",
        )
        embed.add_field(
            name="Counts",
            value=f"**Roles:** {len(guild.roles)}/250\n**Emojis:** {len(guild.emojis)}/{guild.emoji_limit*2}\n**Stickers:** {len(guild.stickers)}/{guild.sticker_limit}",
        )
        embed.set_footer(text=f"Guild ID: {guild.id}")
        if guild.banner:
            embed.set_image(url=guild.banner)
        try:
            await channel.send(embed=embed)
        except:
            return

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        channel_id = 1230950895303262269
        channel = self.bot.get_channel(channel_id)
        embed = discord.Embed(
            description=f"Text command ``{ctx.command.qualified_name}`` has been ran in ``{ctx.guild} ({ctx.guild.id})`` by ``{ctx.author} ({ctx.author.id})`` with message id: ``{ctx.message.id}``.",
            color=self.bot.color,
        )
        try:
            await channel.send(embed=embed)
        except:
            return

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error: commands.CommandError):
        channel_id = 1234770331131056149
        channel = self.bot.get_channel(channel_id)
        embed = discord.Embed(
            description=f"Text command ``{ctx.command.qualified_name}`` has ran into an error in ``{ctx.guild} ({ctx.guild.id})`` by ``{ctx.author} ({ctx.author.id})`` with message id: ``{ctx.message.id}``. \n\n **Error: {error}**",
            color=self.bot.color,
        )
        try:
            await channel.send(embed=embed)
        except:
            return

    """@commands.Cog.listener('on_guild_role_update')
    async def perms_check1(self, before: discord.Role, after: discord.Role, guild: discord.Guild) -> None:
        check = await self.bot.db.fetchrow("SELECT * FROM mwhitelist WHERE guild_id = {}".format(guild.id))
        guild_ids = await self.bot.db.fetch("SELECT guild_id FROM mwhitelist")
        if guild_ids: return
        if check: return
        if not after.is_bot_managed():
            return
        if after.members and after.members[0].id != self.bot.user.id:
            return
        if not after.guild.me.guild_permissions.administrator:
           await after.guild.leave()
           return

    @commands.Cog.listener('on_member_update')
    async def perms_check2(self, before: discord.Member, after: discord.Member) -> None:
        check1 = await self.bot.db.fxetchrow("SELECT * FROM mwhitelist WHERE guild_id = {}".format(after.guild.id))
        if check1: return
        if not after.guild_permissions.administrator:
             try: await after.guild.leave()
             except: return"""


async def setup(bot: commands.AutoShardedBot) -> None:
    await bot.add_cog(Bot(bot))
