from discord.ext.commands import Cog, CommandError
from discord import (
    utils,
    Guild,
    Client,
    Embed,
    File,
    Message,
    AllowedMentions,
    TextChannel,
)
from discord.ext import tasks
from DataProcessing.models.SoundCloud.User import SoundCloudUser, Data35, Data
from DataProcessing.models.Kick.channel import KickChannel
from lib.classes.database import Record
from DataProcessing.models.YouTube import FeedEntry, YouTubeChannel
import datetime


class Social_Events(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self.check_kick.start()

    def kick_variables(self, message: str, snowflake: KickChannel):
        # CHANNEL VARIABLES
        message = message.replace("{channel.name}", snowflake.slug)
        message = message.replace("{lower(channel.name)}", snowflake.slug.lower())
        message = message.replace("{upper(channel.name)}", snowflake.slug.upper())
        message = message.replace("{title(channel.name)}", snowflake.slug.title())

        message = message.replace("{channel.nickname}", str(snowflake.user.username))
        message = message.replace(
            "{lower(channel.nickname)}", str(snowflake.user.username).lower()
        )
        message = message.replace(
            "{upper(channel.nickname)}", str(snowflake.user.username).upper()
        )
        message = message.replace(
            "{title(channel.nickname)}", str(snowflake.user.username).title()
        )

        message = message.replace("{channel.id}", str(snowflake.id))

        message = message.replace(
            "{channel.avatar}", str(snowflake.user.profile_pic or "")
        )

        # POST VARIABLES
        message = message.replace("{post.id}", str(snowflake.livestream.id))

        message = message.replace(
            "{post.name}", str(snowflake.livestream.session_title)
        )
        message = message.replace(
            "{lower(post.name)}", str(snowflake.livestream.session_title).lower()
        )
        message = message.replace(
            "{upper(post.name)}", str(snowflake.livestream.session_title).upper()
        )
        message = message.replace(
            "{title(post.name)}", str(snowflake.livestream.session_title).title()
        )

        message = message.replace(
            "{post.url}", f"https://kick.com/{str(snowflake.slug)}"
        )

        message = message.replace(
            "{post.thumbnail_url}", str(snowflake.livestream.thumbnail.url or "")
        )

        return message

    def replacements(self, user: YouTubeChannel, post: FeedEntry) -> dict:
        REPLACEMENTS = {
            "{post.description}": (post.title or "")[:256],
            "{post.date}": datetime.fromisoformat(post.published),
            "{post.url}": post.link,
            "{post.media_urls}": post.media_thumbnail[0].url,
            "{lower(post.author.name)}": user.name.lower(),
            "{title(post.author.name)}": user.name.title(),
            "{upper(post.author.name)}": user.name.upper(),
            "{post.author.name}": user.name,
            "{post.author.nickname}": "",
            "{post.author.avatar}": user.avatarUrl,
            "{post.author.url}": user.url,
            "{post.stats.likes}": "",
            "{post.stats.comments}": "",
            "{post.stats.plays}": post.media_statistics.views,
            "{post.stats.shares}": "",
        }
        return REPLACEMENTS

    def youtube_variables(self, message: str, item: FeedEntry, channel: YouTubeChannel):
        for key, value in self.replacements(channel, item).items():
            message = message.replace(key, value)
        return message

    def soundcloud_variables(self, message: str, post: Data, user: Data35):
        # ARTIST VARIABLES
        message = message.replace("{channel.name}", user.permalink)
        message = message.replace("{channel.nickname}", user.username)
        message = message.replace("{channel.url}", user.permalink_url)
        message = message.replace("{channel.avatar}", user.avatar_url or "")
        message = message.replace("{channel.id}", user.id)

        message = message.replace("{post.id}", post.id)
        message = message.replace("{post.title}", post.title)
        message = message.replace("{post.thumbnail_url}", post.artwork_url or "")
        message = message.replace("{post.url}", post.permalink_url or "")

        # Handle case variations using str.replace on the entire message
        message = message.replace("{lower(post.title)}", post.title.lower())
        message = message.replace("{upper(post.title)}", post.title.upper())
        message = message.replace("{title(post.title)}", post.title.title())

        message = message.replace("{lower(channel.name)}", user.permalink.lower())
        message = message.replace("{upper(channel.name)}", user.permalink.upper())
        message = message.replace("{title(channel.name)}", user.permalink.title())

        return message

    @tasks.loop(minutes=1)
    async def check_kick(self):
        records = await self.bot.db.fetch("""SELECT username FROM kick_notifications""")
        for record in records:
            check = await self.bot.services.kick.get_channel(
                record.username, cached=False
            )
            if not check:
                continue
            if livestream := check.livestream:
                if not await self.bot.redis.sismember(
                    "posted_kick_notifications", str(livestream.id)
                ):
                    self.bot.dispatch("kick_livestream", check)
                    await self.bot.redis.sadd(
                        "posted_kick_notifications", str(livestream.id)
                    )

    @Cog.listener("on_kick_livestream")
    async def kick_notifications(self, snowflake: KickChannel):
        records = await self.bot.db.fetch(
            """SELECT guild_id, channels FROM kick_notifications WHERE username = $1""",
            snowflake.user.username,
        )
        for record in records:
            self.bot.dispatch("kick_notification_add", snowflake, record)

    @Cog.listener("on_kick_notification_add")
    async def on_kick_notification(self, snowflake: KickChannel, record: Record):
        if not (guild := self.bot.get_guild(record.guild_id)):
            return
        channels = record.channels
        to_remove = []
        for channel_id in channels:
            if not (channel := guild.get_channel(channel_id)):
                to_remove.append(channel_id)
                continue
            if record.message:
                try:
                    await self.bot.send_embed(
                        channel, self.kick_variables(record.message, snowflake)
                    )
                except Exception:
                    pass
        if to_remove:
            channels = [c for c in channels if c not in to_remove]
            await self.bot.db.execute(
                """UPDATE kick_notifications SET channels = $1 WHERE guild_id = $2 AND username = $3""",
                channels,
                record.guild_id,
                record.username,
            )

    @tasks.loop(minutes=1)
    async def check_soundcloud(self):
        records = await self.bot.db.fetch(
            """SELECT username FROM soundcloud_notifications"""
        )
        for record in records:
            check = await self.bot.services.kick.fetch_user(
                record.username, cached=False
            )
            if not check:
                continue
            posts = [
                r.data
                for r in check.props.pageProps.initialStoreState.entities.tracks.values()
            ]
            user: Data35 = (
                list(check.props.pageProps.initialStoreState.entities.users.values())[0]
            ).data
            for post in posts:
                if not await self.bot.redis.sismember(
                    "posted_soundcloud_notifications", str(post.id)
                ):
                    self.bot.dispatch("soundcloud_post", check)
                    await self.bot.redis.sadd(
                        "posted_soundcloud_notifications", str(post.id)
                    )

    @Cog.listener("on_soundcloud_post")
    async def soundcloud_notifications(self, post: Data, user: Data35):
        records = await self.bot.db.fetch(
            """SELECT guild_id, channels FROM soundcloud_notifications WHERE username = $1""",
            user.permalink,
        )
        for record in records:
            self.bot.dispatch("soundcloud_notification_add", post, user, record)

    @Cog.listener("on_soundcloud_notification_add")
    async def on_soundcloud_notification(
        self, post: Data, user: Data35, record: Record
    ):
        if not (guild := self.bot.get_guild(record.guild_id)):
            return
        channels = record.channels
        to_remove = []
        for channel_id in channels:
            if not (channel := guild.get_channel(channel_id)):
                to_remove.append(channel_id)
                continue
            if record.message:
                message = self.soundcloud_variables(record.message, post, user)
                try:
                    await self.bot.send_embed(channel, message)
                except Exception:
                    pass
        if to_remove:
            channels = [c for c in channels if c not in to_remove]
            await self.bot.db.execute(
                """UPDATE soundcloud_notifications SET channels = $1 WHERE guild_id = $2 AND username = $3""",
                channels,
                record.guild_id,
                record.username,
            )

    @tasks.loop(minutes=1)
    async def check_youtube(self):
        records = await self.bot.db.fetch(
            """SELECT username, user_id FROM youtube_notifications"""
        )
        for record in records:
            channel = await self.bot.services.youtube.get_channel(record.user_id)
            check = await self.bot.services.youtube.get_feed(record.user_id)
            for item in check.entries[:3]:
                if not await self.bot.redis.sismember(
                    "posted_youtube_notifications", str(item.yt_videoid)
                ):
                    self.bot.dispatch("youtube_livestream", item, channel)
                    await self.bot.redis.sadd(
                        "posted_youtube_notifications", str(item.yt_videoid)
                    )

    @Cog.listener("on_youtube_livestream")
    async def youtube_notifications(self, item: FeedEntry, channel: YouTubeChannel):
        records = await self.bot.db.fetch(
            """SELECT guild_id, channels FROM youtube_notifications WHERE user_id = $1""",
            channel.id,
        )
        for record in records:
            self.bot.dispatch("youtube_notification_add", item, channel)

    async def default_youtube_embed(
        self,
        channel: TextChannel,
        youtube_video: FeedEntry,
        youtube_channel: YouTubeChannel,
    ):
        embed = Embed(
            description=f"[{youtube_video.title}]({youtube_video.link})",
            timestamp=datetime.fromisoformat(youtube_video.published),
        )
        embed.set_author(
            url=youtube_video.link,
            name=youtube_video.author,
            icon_url=youtube_channel.avatarUrl,
        )
        embed.color = self.bot.color
        embed.set_thumbnail(url=youtube_video.media_thumbnail[0].url)
        return await channel.send(
            embed=embed,
            allowed_mentions=AllowedMentions.all(),
        )

    @Cog.listener("on_youtube_notification_add")
    async def on_youtube_notification(
        self, item: FeedEntry, channel: YouTubeChannel, record: Record
    ):
        if not (guild := self.bot.get_guild(record.guild_id)):
            return
        channels = record.channels
        to_remove = []
        for channel_id in channels:
            if not (post_channel := guild.get_channel(channel_id)):
                to_remove.append(channel_id)
                continue
            if record.message:
                try:
                    await self.bot.send_embed(
                        post_channel,
                        self.youtube_variables(record.message, item, channel),
                    )
                except Exception:
                    pass
            else:
                try:
                    await self.default_youtube_embed(post_channel, item, channel)
                except Exception:
                    pass
        if to_remove:
            channels = [c for c in channels if c not in to_remove]
            await self.bot.db.execute(
                """UPDATE youtube_notifications SET channels = $1 WHERE guild_id = $2 AND user_id = $3""",
                channels,
                record.guild_id,
                record.user_id,
            )


async def setup(bot: Client):
    await bot.add_cog(Social_Events(bot))
