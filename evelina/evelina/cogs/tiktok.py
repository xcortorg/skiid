import os
import discord
import datetime

from discord import Embed, TextChannel
from discord.ext.commands import Cog, group, has_guild_permissions, cooldown, BucketType

from modules import config
from modules.styles import emojis, colors, icons
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import has_premium

class TikTok(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
    
    @staticmethod
    def humanize_number(value):
        if value < 1000:
            return f"**{value}**"
        elif value < 1000000:
            return f"**{value/1000:.1f}k**"
        elif value < 1000000000:
            return f"**{value/1000000:.1f}m**"
        else:
            return f"**{value/1000000000:.1f}b**"

    @group(aliases=["tt"], usage="tiktok nike", invoke_without_command=True, case_insensitive=True)
    async def tiktok(self, ctx: EvelinaContext, username: str):
        """Gets profile information on the given TikTok user"""
        async with ctx.typing():
            data = await self.bot.session.get_json(f"https://api.tempt.lol/socials/tiktok/{username}", headers={"X-API-KEY": "3BduE1OR97a55xU8Vg-IwfzXI4RoEaRXEHZxJ0Y_2fI"})
            if not data:
                return await ctx.send_warning(f"Couldn't get information about **{username}**")
            else:
                embed = (
                    discord.Embed(color=colors.TIKTOK, title=f"{data['nickname']} (@{data['unique_id']})", url=f"https://tiktok.com/@{data['unique_id']}/")
                    .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                    .set_thumbnail(url=data['avatar_thumb'])
                    .add_field(name="Hearts", value=f"{self.humanize_number(data['stats']['heart_count'])}")
                    .add_field(name="Following", value=f"{self.humanize_number(data['stats']['following_count'])}")
                    .add_field(name="Followers", value=f"{self.humanize_number(data['stats']['follower_count'])}")
                    .set_footer(text="TikTok", icon_url=icons.TIKTOK)
                )
                return await ctx.send(embed=embed)

    @tiktok.command(name="add", brief="manage server", usage="tiktok add nike #feed @everyone")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def tiktok_add(self, ctx: EvelinaContext, username: str, channel: TextChannel, *, message: str = None):
        """Create a new feed for a user"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_tiktok WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        if res:
            return await ctx.send_warning(f"You've already have a notification for **{username}**")
        await self.bot.db.execute("INSERT INTO autopost_tiktok (guild_id, channel_id, username, message) VALUES ($1, $2, $3, $4)", ctx.guild.id, channel.id, username.lower(), message)
        mess = f"TikTok notifications for **{username}** has been set in {channel.mention}"
        if message:
            mess += f"\n**With message**\n```{message}```"
        return await ctx.send_success(mess)
    
    @tiktok.command(name="remove", brief="manage server", usage="tiktok remove nike")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def tiktok_remove(self, ctx: EvelinaContext, username: str):
        """Removes an existing feed for a user"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_tiktok WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        if not res:
            return await ctx.send_warning(f"There is no notification set for **{username}**")
        await self.bot.db.execute("DELETE FROM autopost_tiktok WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        return await ctx.send_success(f"TikTok notifications for **{username}** has been removed")
    
    @tiktok.command(name="list", brief="manage server", usage="tiktok list")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def tiktok_list(self, ctx: EvelinaContext):
        """List all TikTok user feeds"""
        res = await self.bot.db.fetch("SELECT * FROM autopost_tiktok WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("There is no TikTok notification set for this server")
        tiktok_list = [f"**{r['username']}** - {self.bot.get_channel(r['channel_id']).mention}\n> {r['message']}" for r in res]
        return await ctx.paginate(tiktok_list,"TikTok Notifications", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @tiktok.command(name="check", usage="tiktok check nike", cooldown=10)
    @cooldown(1, 10, BucketType.user)
    @has_premium()
    async def tiktok_check(self, ctx: EvelinaContext, username: str):
        """Get the latest video from a user"""
        video = await self.bot.social.fetch_tiktok_video(username)
        if not video:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Watch Video", url=video['share_url'], emoji=emojis.TIKTOK))
        embed = Embed(
            title=f"{username} uploaded a new video! 🎥",
            description=video['desc'],
            url=video['share_url'],
            timestamp=datetime.datetime.now(),
            color=colors.TIKTOK
        )
        embed.set_footer(text="TikTok", icon_url=icons.TIKTOK)
        file_url = video['video']['play_addr']['url_list'][0] if video['video'] and 'play_addr' in video['video'] else None
        if file_url:
            file = discord.File(fp=await self.bot.getbyte(file_url), filename="evelinatiktok.mp4")
            return await ctx.send(embed=embed, file=file, view=view)
        else:
            return await ctx.send(embed=embed, view=view)
        
async def setup(bot: Evelina):
    await bot.add_cog(TikTok(bot))