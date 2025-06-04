import discord
import datetime

from discord import Embed, TextChannel
from discord.ext.commands import Cog, group, has_guild_permissions, cooldown, BucketType

from modules import config
from modules.styles import emojis, colors, icons
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import has_premium

class Instagram(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(aliases=["ig"], usage="instagram nike", invoke_without_command=True, case_insensitive=True)
    async def instagram(self, ctx: EvelinaContext, username: str):
        """Gets profile information on the given Instagram user"""
        data = await self.bot.session.get_json(f"https://api.evelina.bot/instagram/user?username={username.lower()}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        embed = (
            discord.Embed(color=colors.INSTAGRAM, title=f"{data['full_name']} (@{data['username']}){' ' + emojis.CHECKMARK if data['is_verified'] else ''}", url=f"https://instagram.com/{data['username']}/", description=data['bio'])
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            .set_thumbnail(url=data['profile_pic'])
            .add_field(name="Posts", value=f"{data['posts']:,}")
            .add_field(name="Following", value=f"{data['following']:,}")
            .add_field(name="Followers", value=f"{data['followers']:,}")
            .set_footer(text="Instagram", icon_url=icons.INSTAGRAM)
        )
        return await ctx.send(embed=embed)
    
    @instagram.command(name="add", brief="manage server", usage="instagram add nike #feed @everyone")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def instagram_add(self, ctx: EvelinaContext, username: str, channel: TextChannel, *, message: str = None):
        """Create a new feed for a user"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_instagram WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        if res:
            return await ctx.send_warning(f"You've already have a notification for [**{username}**](https://instagram.com/{username})")
        await self.bot.db.execute("INSERT INTO autopost_instagram (guild_id, channel_id, username, message) VALUES ($1, $2, $3, $4)", ctx.guild.id, channel.id, username.lower(), message)
        mess = f"Instagram notifications for [**{username}**](https://instagram.com/{username}) has been set in {channel.mention}"
        if message:
            mess += f"\n**With message**\n```{message}```"
        return await ctx.send_success(mess)
    
    @instagram.command(name="remove", brief="manage server", usage="instagram remove nike")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def instagram_remove(self, ctx: EvelinaContext, username: str):
        """Removes an existing feed for a user"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_instagram WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        if not res:
            return await ctx.send_warning(f"There is no notification set for [**{username}**](https://instagram.com/{username})")
        await self.bot.db.execute("DELETE FROM autopost_instagram WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        return await ctx.send_success(f"Instagram notifications for [**{username}**](https://instagram.com/{username}) has been removed")

    @instagram.command(name="list", brief="manage server", usage="instagram list")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def instagram_list(self, ctx: EvelinaContext):
        """View list of every Instagram feed"""
        res = await self.bot.db.fetch("SELECT * FROM autopost_instagram WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("There is no Instagram notification set for this server")
        instagram_list = [f"[**{r['username']}**](https://instagram.com/{r['username']}) - {self.bot.get_channel(r['channel_id']).mention}\n> {r['message']}" for r in res]
        return await ctx.paginate(instagram_list,"Instagram Notifications", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @instagram.command(name="check", usage="instagram check nike")
    @cooldown(1, 10, BucketType.user)
    @has_premium()
    async def instagram_check(self, ctx: EvelinaContext, username: str):
        """Get the latest post from a user"""
        post = await self.bot.social.fetch_instagram_post(username)
        if not post:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View Post", url=f"https://instagram.com/p/{post['code']}", emoji=emojis.INSTAGRAM))
        embed = Embed(
            title=f"{username} posted! 📸",
            description=post['caption']['text'] if 'caption' in post else None,
            url=f"https://instagram.com/p/{post['code']}",
            timestamp=datetime.datetime.now(),
            color=colors.INSTAGRAM
        )
        files = []
        post_details = await self.bot.social.fetch_instagram_post_details(post['code'])
        if post_details:
            if post_details['is_video']:
                file_url = post_details['video_url'] if 'video_url' in post_details else None
                if file_url:
                    file = discord.File(fp=await self.bot.getbyte(file_url), filename="evelinainstagram.mp4")
                    files.append(file)
            else:
                file_url = post_details['image_versions']['items'][0]['url'] if 'image_versions' in post_details else None
                if file_url:
                    file = discord.File(fp=await self.bot.getbyte(file_url), filename="evelinainstagram.png")
                    files.append(file)
        embed.set_footer(text="Instagram", icon_url=icons.INSTAGRAM)
        if files:
            return await ctx.send(embed=embed, files=files, view=view)
        else:
            return await ctx.send(embed=embed, view=view)

async def setup(bot: Evelina):
    await bot.add_cog(Instagram(bot))