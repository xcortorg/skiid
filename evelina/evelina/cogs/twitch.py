from datetime import datetime

from discord import Embed, TextChannel, ui
from discord.ext.commands import Cog, group, has_guild_permissions, cooldown, BucketType

from modules.styles import colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.converters import Streamers
from modules.predicates import has_premium

class Twitch(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Automatically announces streams of selected twitch streamers"

    def format_streamer_string(self, streamer: str) -> str:
        return f"[**{streamer}**](https://twitch.tv/{streamer})"

    @group(name="twitch", brief="manage server", invoke_without_command=True, case_insensitive=True)
    async def twitch(self, ctx: EvelinaContext):
        """Twitch command group"""
        return await ctx.create_pages()

    @twitch.command(name="add", brief="manage server", usage="twitch add xQc #steams @everyone")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def twitch_add(self, ctx: EvelinaContext, streamer: Streamers, channel: TextChannel, *, message: str = None):
        """Add stream notifications to channel"""
        streamer_string = self.format_streamer_string(streamer)
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_twitch WHERE guild_id = $1 AND streamer = $2", ctx.guild.id, streamer.lower())
        if res:
            return await ctx.send_warning(f"You've already have a notification for {streamer_string}")
        await self.bot.db.execute("INSERT INTO autopost_twitch (guild_id, channel_id, streamer, message) VALUES ($1, $2, $3, $4)", ctx.guild.id, channel.id, streamer.lower(), message)
        mess = f"Stream notifications for {streamer_string} has been set in {channel.mention}"
        if message:
            mess += f"\n**With message**\n```{message}```"
        return await ctx.send_success(mess)

    @twitch.command(name="remove", brief="manage server", usage="twitch remove xQc")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def twitch_remove(self, ctx: EvelinaContext, streamer: Streamers):
        """Remove stream notifications from a channel"""
        streamer_string = self.format_streamer_string(streamer)
        res = await self.bot.db.fetchrow("SELECT * FROM autopost_twitch WHERE guild_id = $1 AND streamer = $2", ctx.guild.id, streamer.lower())
        if not res:
            return await ctx.send_warning(f"There is no configured notification for {streamer_string}")
        await self.bot.db.execute("DELETE FROM autopost_twitch WHERE guild_id = $1 AND streamer = $2", ctx.guild.id, streamer.lower())
        return await ctx.send_success(f"{streamer_string} has been removed from twitch notifications")

    @twitch.command(name="list", brief="manage server", usage="twitch list")
    @has_guild_permissions(manage_guild=True)
    @has_premium()
    async def twitch_list(self, ctx: EvelinaContext):
        """View all Twitch stream notifications"""
        res = await self.bot.db.fetch("SELECT * FROM autopost_twitch WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("There is no streamer notification set for this server")
        streamers_list = [f"**{r['streamer']}** - {self.bot.get_channel(r['channel_id']).mention}\n> {r['message']}" for r in res]
        return await ctx.paginate(streamers_list,"Twitch Notifications", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    # @twitch.command(name="check", usage="twitch check xQc", cooldown=10)
    # @cooldown(1, 10, BucketType.user)
    # @has_premium()
    # async def twitch_check(self, ctx: EvelinaContext, streamer: Streamers):
    #     """Check if a streamer is currently live"""
    #     stream_data = await self.bot.twitch.fetch_stream_data(streamer)
    #     if not stream_data["is_live"]:
    #         return await ctx.send_warning(f"{self.format_streamer_string(streamer)} is currently not live")
    #     view = ui.View()
    #     view.add_item(ui.Button(label="Watch", url=f"https://twitch.tv/{streamer}", emoji="<:TWITCH:1329161415273091102>"))
    #     embed=Embed(title=f"{streamer} is now live! 🎥", description=stream_data['title'], url=f"https://twitch.tv/{streamer}", timestamp=datetime.now(), color=colors.TWITCH)
    #     embed.add_field(name="👀 Viewers", value=stream_data["viewers"], inline=True)
    #     embed.add_field(name="🎮 Game", value=stream_data["game"], inline=True)
    #     embed.set_image(url=stream_data["thumbnail_url"].format(width=640, height=360))
    #     view=view
    #     return await ctx.send(embed=embed, view=view)

async def setup(bot: Evelina):
    await bot.add_cog(Twitch(bot))