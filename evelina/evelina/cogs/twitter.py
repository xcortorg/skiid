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

class Twitter(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(name="twitter", aliases=["x"], usage="twitter nike", invoke_without_command=True, case_insensitive=True)
    async def twitter(self, ctx: EvelinaContext, username: str):
        """Gets profile information on the given Twitter user"""
        data = await self.bot.session.get_json(f"https://api.evelina.bot/twitter/user?username={username.lower()}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        if data['username'] == None:
            return await ctx.send_warning(f"Account **{username}** is suspended or doesn't exist")
        original_date_str = data.get('created_at')
        if original_date_str:
            date_obj = datetime.datetime.strptime(original_date_str, '%a %b %d %H:%M:%S %z %Y')
            formatted_date_str = date_obj.strftime('%d %b. %Y %H:%M')
        else:
            formatted_date_str = "N/A"
        embed = (
            discord.Embed(
                color=colors.TWITTER,
                title=f"{data['full_name']} (@{data['username']}){' ' + emojis.CHECKMARK if data['is_verified'] else ''}",
                url=f"https://twitter.com/{data['username']}/",
                description=data['bio']
            )
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            .set_thumbnail(url=data['profile_pic'])
            .add_field(name="Tweets", value=f"{data['posts']:,}")
            .add_field(name="Following", value=f"{data['following']:,}")
            .add_field(name="Followers", value=f"{data['followers']:,}")
            .set_footer(text=f"{formatted_date_str}", icon_url=icons.TWITTER)
        )
        return await ctx.send(embed=embed)
    
    @twitter.command(name="add", brief="manage server", usage="twitter add nike #feed @everyone")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def twitter_add(self, ctx: EvelinaContext, username: str, channel: TextChannel, *, message: str = None):
        """Create feed for new tweets from a user"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_twitter WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        if res:
            return await ctx.send_warning(f"You've already have a notification for [**{username}**](https://x.com/{username})")
        
        await self.bot.db.execute("INSERT INTO autopost_twitter (guild_id, channel_id, username, message) VALUES ($1, $2, $3, $4)", ctx.guild.id, channel.id, username.lower(), message)
        mess = f"Twitter notifications for [**{username}**](https://x.com/{username}) has been set in {channel.mention}"
        if message:
            mess += f"\n**With message**\n```{message}```"
        return await ctx.send_success(mess)

    @twitter.command(name="remove", brief="manage server", usage="twitter remove nike")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def twitter_remove(self, ctx: EvelinaContext, username: str):
        """Remove feed for new tweets"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_twitter WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        if not res:
            return await ctx.send_warning(f"There is no notification set for [**{username}**](https://x.com/{username})")
        await self.bot.db.execute("DELETE FROM autopost_twitter WHERE guild_id = $1 AND username = $2", ctx.guild.id, username.lower())
        return await ctx.send_success(f"Twitter notifications for [**{username}**](https://x.com/{username}) has been removed")
    
    @twitter.command(name="list", brief="manage server", usage="twitter list")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def twitter_list(self, ctx: EvelinaContext):
        """View list of every Twitter feed"""
        res = await self.bot.db.fetch("SELECT * FROM autopost_twitter WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("There is no Twitter notification set for this server")
        twitter_list = [f"[**{r['username']}**](https://x.com/{r['username']}) - {self.bot.get_channel(r['channel_id']).mention}\n> {r['message']}" for r in res]
        return await ctx.paginate(twitter_list,"Twitter Notifications", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @twitter.command(name="check", usage="twitter check nike")
    @cooldown(1, 10, BucketType.user)
    @has_premium()
    async def twitter_check(self, ctx: EvelinaContext, username: str):
        """Get the latest tweet from a user"""
        tweet = await self.bot.social.fetch_twitter_post(username)
        if not tweet:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View Tweet", url=f"https://x.com/{username}/status/{tweet['tweet_id']}", emoji=emojis.TWITTER))
        embed = Embed(
            title=f"{username} tweeted! 🐦",
            description=tweet['text'],
            url=f"https://x.com/{username}/status/{tweet['tweet_id']}",
            timestamp=datetime.datetime.now(),
            color=colors.TWITTER
        )
        embed.set_image(url=tweet['media']['photo'][0]['media_url_https'] if tweet['media'] and 'photo' in tweet['media'] else None)
        embed.set_footer(text="Twitter", icon_url=icons.TWITTER)
        file_url = tweet['media']['video'][0]['variants'][4]['url'] if tweet['media'] and 'video' in tweet['media'] else None
        if file_url:
            file = discord.File(fp=await self.bot.getbyte(file_url), filename="evelinatweet.mp4")
            return await ctx.send(embed=embed, file=file, view=view)
        else:
            return await ctx.send(embed=embed, view=view)

async def setup(bot: Evelina):
    await bot.add_cog(Twitter(bot))