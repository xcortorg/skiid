import discord
import datetime

from discord import Embed, TextChannel
from discord.ext.commands import Cog, group, has_guild_permissions, cooldown, BucketType

from modules.styles import emojis, colors, icons
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import has_premium

class Youtube(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(name="youtube", invoke_without_command=True, case_insensitive=True)
    async def youtube(self, ctx: EvelinaContext):
        """Manage YouTube notifications"""
        return await ctx.create_pages()
    
    @youtube.command(name="add", brief="manage server", usage="youtube add PewDiePie #videos @everyone")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def youtube_add(self, ctx: EvelinaContext, username: str, channel: TextChannel, *, message: str = None):
        """Enable post notifications for a channel"""
        channel_id = await self.bot.social.fetch_youtube_channel(username)
        if not channel_id:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_youtube WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if res:
            return await ctx.send_warning(f"You've already have a notification for **{username}**")
        await self.bot.db.execute("INSERT INTO autopost_youtube (guild_id, channel_id, username, message) VALUES ($1, $2, $3, $4)", ctx.guild.id, channel.id, username, message)
        mess = f"YouTube notifications for **{username}** has been set in {channel.mention}"
        if message:
            mess += f"\n**With message**\n```{message}```"
        return await ctx.send_success(mess)
    
    @youtube.command(name="remove", brief="manage server", usage="youtube remove PewDiePie")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def youtube_remove(self, ctx: EvelinaContext, username: str):
        """Disable post notifications for a channel"""
        channel_id = await self.bot.social.fetch_youtube_channel(username)
        if not channel_id:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_youtube WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        if not res:
            return await ctx.send_warning(f"There is no notification set for **{username}**")
        await self.bot.db.execute("DELETE FROM autopost_youtube WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"YouTube notifications for **{username}** has been removed")
    
    @youtube.command(name="list", brief="manage server", usage="youtube list")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def youtube_list(self, ctx: EvelinaContext):
        """View all YouTube post notifications"""
        res = await self.bot.db.fetch("SELECT * FROM autopost_youtube WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("There is no YouTube notification set for this server")
        youtube_list = [f"**{r['channel_id']}** - {self.bot.get_channel(r['channel_id']).mention}\n> {r['message']}" for r in res]
        return await ctx.paginate(youtube_list,"YouTube Notifications", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @youtube.command(name="check", usage="youtube check PewDiePie", cooldown=10)
    @cooldown(1, 10, BucketType.user)
    @has_premium()
    async def youtube_check(self, ctx: EvelinaContext, *, username: str):
        """Get the latest video from a channel"""
        channel_id = await self.bot.social.fetch_youtube_channel(username)
        if not channel_id:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        video = await self.bot.social.fetch_youtube_video(channel_id)
        if not video:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Watch Video", url=f"https://youtube.com/watch?v={video['video_id']}", emoji=emojis.YOUTUBE))
        embed = Embed(
            title=f"{username} uploaded a new video! 🎥",
            description=video['title'],
            url=f"https://youtube.com/watch?v={video['video_id']}",
            timestamp=datetime.datetime.now(),
            color=colors.YOUTUBE
        )
        embed.set_image(url=video['thumbnails'][3]['url'].format(width=640, height=360) if video['thumbnails'] else None)
        embed.set_footer(text="YouTube", icon_url=icons.YOUTUBE)
        return await ctx.send(embed=embed, view=view)

async def setup(bot: Evelina):
    await bot.add_cog(Youtube(bot))