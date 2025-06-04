from discord.ext.commands import (
    group,
    has_permissions,
    command,
    CommandError,
    Cog,
    Converter,
    EmbedConverter,
)
from lib.classes import Context
from discord import TextChannel, Guild, User, File, Client, Member, Embed


class SoundCloudUserConverter(Converter):
    async def convert(self, ctx: Context, argument: str):
        try:
            user = await ctx.bot.services.soundcloud.fetch_user(argument)
        except Exception:
            raise CommandError(
                f"No **SoundCloud User** found named [{argument[:25]}](https://soundcloud.com/{argument})"
            )
        return argument


class Commands(Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    @group(
        name="soundcloud",
        invoke_without_command=True,
        description="Search a query on SoundCloud",
        example=",soundcloud purple",
    )
    async def soundcloud(self, ctx: Context, *, query: str):
        try:
            results = await self.bot.services.soundcloud.search(query)
        except Exception:
            raise CommandError(f"No results found for query `{query[:25]}`")
        contents = [
            f"{result.permalink_url} ({i}/{len(results.collection)})"
            for i, result in enumerate(results.collection, start=1)
        ]
        return await ctx.alternative_paginate(contents)

    @soundcloud.command(
        name="remove",
        description="Remove feed for new SoundCloud posts",
        example=",soundcloud remove #txt $uicideBoy$",
    )
    @has_permissions(manage_channels=True)
    async def soundcloud_remove(self, ctx: Context, channel: TextChannel, user: str):
        channels = (
            await self.bot.db.fetchval(
                """SELECT channels FROM soundcloud_notifications WHERE guild_id = $1 AND username = $2""",
                ctx.guild.id,
                user,
            )
            or []
        )
        if channel.id not in channels:
            raise CommandError(
                f"No **notification** for `{user}'s` posts found for {channel.mention}"
            )
        channels.remove(channel.id)
        if not len(channels) == 0:
            await self.bot.db.execute(
                """UPDATE soundcloud_notifications SET channels = $1 WHERE guild_id = $2 AND username = $3""",
                channels,
                ctx.guild.id,
                user,
            )
        else:
            await self.bot.db.execute(
                """DELETE FROM soundcloud_notifications WHERE guild_id = $1 AND username = $2""",
                ctx.guild.id,
                user,
            )
        return await ctx.success(
            f"**Removed** notifications for `{user}'s` posts from {channel.mention}"
        )

    @soundcloud.command(
        name="add",
        description="Add stream notifications to channel",
        example=",soundcloud add #text $uicideBoy$",
    )
    @has_permissions(manage_guild=True)
    async def soundcloud_add(
        self, ctx: Context, channel: TextChannel, username: SoundCloudUserConverter
    ):
        channels = (
            await self.bot.db.fetchval(
                """SELECT channels FROM soundcloud_notifications WHERE guild_id = $1 AND username = $2""",
                ctx.guild.id,
                username,
            )
            or []
        )
        channels.append(channel.id)
        await self.bot.db.execute(
            """INSERT INTO soundcloud_notifications (guild_id, channels, username) VALUES($1, $2, $3) ON CONFLICT(guild_id, username) DO UPDATE SET channels = excluded.channels""",
            ctx.guild.id,
            channels,
            username,
        )
        check = await self.bot.services.soundcloud.fetch_user(username)
        posts = [
            r.data
            for r in check.props.pageProps.initialStoreState.entities.tracks.values()
        ]
        if not await self.bot.redis.sismember(
            "posted_soundcloud_notifications", str(posts[0].id)
        ):
            for post in posts:
                await self.bot.redis.sadd(
                    "posted_soundcloud_notifications", str(post.id)
                )
        return await ctx.success(
            f"**Added** notifications for `{username}'s` posts to {channel.mention}"
        )

    @soundcloud.command(
        name="list", description="View all soundcloud stream notifications"
    )
    @has_permissions(manage_guild=True)
    async def soundcloud_list(self, ctx: Context):
        records = await self.bot.db.fetch(
            """SELECT username, channels FROM soundcloud_notifications WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if not records:
            raise CommandError("No **soundcloud notifications** setup")
        rows = []
        for record in records:
            for channel_id in record.channels:
                if not (channel := ctx.guild.get_channel(channel_id)):
                    continue
                rows.append(f"**{record.username}** - {channel.mention}")
        if not rows:
            raise CommandError("No **soundcloud notifications** setup")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        embed = Embed(
            color=self.bot.color, title="SoundCloud Notifications"
        ).set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        return await ctx.paginate(embed, rows)

    @soundcloud.group(
        name="message",
        description="Set a message for soundcloud notifications",
        example=",soundcloud message $uicideBoy$ {embed}{description:...}",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def soundcloud_message(
        self, ctx: Context, username: str, *, message: EmbedConverter
    ):
        try:
            await self.bot.db.execute(
                """UPDATE soundcloud_notifications SET message = $1 WHERE guild_id = $2 AND username = $3""",
                message,
                ctx.guild.id,
                username,
            )
        except Exception:
            return await ctx.fail(f"no **notification** added for `{username}'s` posts")
        return await ctx.success(
            f"**Updated** the message for `{username}'s` livestream notifications"
        )

    @soundcloud_message.command(
        name="view",
        description="View soundcloud message for new posts",
        example=",soundcloud message view $uicideBoy$",
    )
    @has_permissions(manage_guild=True)
    async def soundcloud_message_view(self, ctx: Context, username: str):
        message = await self.bot.db.fetchval(
            """SELECT message FROM soundcloud_notifications WHERE guild_id = $1""",
            ctx.guild.id,
        )
        return await ctx.send(
            embed=Embed(
                color=self.bot.color,
                title=f"{username}'s notification message",
                description=f"```{message}```",
            ).set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        )
