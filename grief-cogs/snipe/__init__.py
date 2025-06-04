from __future__ import annotations

import datetime
from collections import defaultdict, deque
from sys import getsizeof
from typing import Mapping, Optional

import discord

from grief.core import commands
from grief.core.bot import Grief
from grief.core.commands import Cog as RedCog
from grief.core.utils import chat_formatting as cf
from grief.core.utils.views import SimpleMenu as BaseMenu


class MiniMsg:
    __slots__ = (
        "channel",
        "author",
        "content",
        "embed",
        "created_at",
        "deleted_at",
        "attachment",
    )

    def __init__(self, msg: discord.Message):
        self.channel = msg.channel
        self.author = msg.author
        self.content = msg.content if msg.content else "No message content."
        self.embed = msg.embeds[0] if msg.embeds else None
        self.deleted_at = discord.utils.utcnow().timestamp()
        self.created_at = msg.created_at.timestamp()
        self.attachment = msg.attachments[0].proxy_url if msg.attachments else None


class EditMsg:
    __slots__ = (
        "channel",
        "author",
        "old_content",
        "new_content",
        "old_attachment",
        "edited_at",
    )

    def __init__(self, before: discord.Message, after: discord.Message):
        self.channel = before.channel
        self.author = before.author
        self.edited_at = discord.utils.utcnow().timestamp()
        self.old_content = before.content
        self.new_content = after.content
        self.old_attachment = (
            before.attachments[0].proxy_url if before.attachments else None
        )


class ReactionMsg:
    __slots__ = ("channel", "reactor", "emote", "reacted_at", "message")

    def __init__(self, payload: discord.RawReactionActionEvent):
        self.channel = payload.channel_id
        self.reactor = payload.user_id
        self.emote = payload.emoji
        self.reacted_at = discord.utils.utcnow().timestamp()
        self.message = f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}"


class Snipe(RedCog):
    """Snipe the last edited/deleted message."""

    def __init__(self, bot: Grief):
        self.bot = bot
        self.edit_cache = defaultdict(lambda: deque(maxlen=100))
        self.delete_cache = defaultdict(lambda: deque(maxlen=100))
        self.reaction_cache = defaultdict(lambda: deque(maxlen=100))

    @RedCog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
            return
        self.delete_cache[message.channel.id].append(MiniMsg(message))

    @RedCog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content == after.content:
            return
        if before.guild is None:
            return
        self.edit_cache[before.channel.id].append(EditMsg(before, after))

    @RedCog.listener()
    async def on_raw_reaction_remove(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        if payload.guild_id is None:
            return
        self.reaction_cache[payload.channel_id].append(ReactionMsg(payload))

    @staticmethod
    async def reply(
        ctx: commands.Context, content: str = None, **kwargs
    ) -> discord.Message:
        ref = ctx.message.to_reference(fail_if_not_exists=False)
        kwargs["reference"] = ref
        return await ctx.send(content, **kwargs)

    @staticmethod
    async def pre_check_perms(
        ctx: commands.Context, channel: discord.TextChannel
    ) -> bool:
        user_perms = channel.permissions_for(ctx.author)
        if user_perms.read_messages and user_perms.read_message_history:
            return True
        else:
            await ctx.reply(
                f"{ctx.author.name}, you don't have read access to {channel.mention}",
                mention_author=False,
            )
            return False

    def sizeof_fmt(self, num, suffix="B") -> str:
        for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
            if abs(num) < 1024.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Yi{suffix}"

    # Thanks phen
    def recursive_getsizeof(self, obj: object) -> int:
        total = 0
        if isinstance(obj, Mapping):
            for v in obj.values():
                total += self.recursive_getsizeof(v)
        else:
            total += getsizeof(obj)
        return total

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["s"])
    async def snipe(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
        index: int = None,
    ):
        """Shows the last deleted messages in a channel."""
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        message: Optional[MiniMsg] = None
        if index is None:
            # Getting last message
            for msg_obj in reversed(self.delete_cache[channel.id]):
                if msg_obj.content:
                    message = msg_obj
                    break
        else:
            try:
                message = self.delete_cache[channel.id][-index]
            except IndexError:
                return await ctx.reply("There's nothing to snipe!")
        if message:
            author = message.author
            content = list(cf.pagify(message.content))
            if content:
                description = content[0]
            embed = discord.Embed(
                description=description,
                timestamp=datetime.datetime.fromtimestamp(message.deleted_at),
                color=0x2F3136,
            )
            if message.attachment is not None:
                embed.set_image(url=message.attachment)
            if len(content) > 1:
                for page in content:
                    embed.add_field(name="Message Continued", value=page)
            embed.set_footer(
                text=f"Sniped by: {ctx.author}", icon_url=ctx.author.display_avatar.url
            )
            if author:
                embed.set_author(
                    name=f"{author} ({author.id})", icon_url=author.display_avatar.url
                )
            else:
                embed.set_author(name="Unknown Member")
            await self.reply(ctx, embed=embed, mention_author=False)
        else:
            await ctx.reply("There's nothing to snipe!")

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["su"])
    async def snipeuser(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: discord.TextChannel = None,
    ):
        """Snipe a user's past deleted messages in a channel."""
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.delete_cache[channel.id]:
            user_msgs = [
                msg
                for msg in reversed(self.delete_cache[channel.id])
                if msg.content and msg.author.id == user.id
            ]
            if user_msgs:
                embeds = []
                for message in user_msgs:
                    author = message.author
                    content = list(cf.pagify(message.content))
                    if content:
                        description = content[0]
                    embed = discord.Embed(
                        description=description,
                        timestamp=datetime.datetime.fromtimestamp(message.deleted_at),
                        color=0x2F3136,
                    )
                    if message.attachment is not None:
                        embed.set_image(url=message.attachment)
                    if len(content) > 1:
                        for page in content:
                            embed.add_field(name="Message Continued", value=page)
                    embed.set_footer(
                        text=f"Sniped by: {ctx.author}",
                        icon_url=ctx.author.display_avatar.url,
                    )
                    if author:
                        embed.set_author(
                            name=f"{author} ({author.id})",
                            icon_url=author.display_avatar.url,
                        )
                    else:
                        embed.set_author(name="Unknown Member")
                    embeds.append(embed)
                await BaseMenu(embeds, timeout=120).start(ctx)
            else:
                await ctx.reply("There's nothing to snipe!")
        else:
            await ctx.reply("There's nothing to snipe!")

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["se"])
    async def snipeembed(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Snipe all past deleted embeds in a channel.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if embs_obj := [
            msg.embed for msg in reversed(self.delete_cache[channel.id]) if msg.embed
        ]:
            if len(embs_obj) == 1:
                return await self.reply(ctx, embed=embs_obj[0])
            await BaseMenu(embs_obj, timeout=120).start(ctx)
        else:
            await ctx.reply("There's nothing to snipe!")

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["bs"])
    async def bulksnipe(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Snipe all the last deleted messages in a channel.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.delete_cache[channel.id]:
            entries = [
                msg
                for msg in reversed(self.delete_cache[channel.id])
                if msg.content or msg.attachment
            ]
            embeds = []
            for message in entries:
                author = message.author
                content = list(cf.pagify(message.content))
                if content:
                    description = content[0]
                embed = discord.Embed(
                    description=description,
                    timestamp=datetime.datetime.fromtimestamp(message.deleted_at),
                    color=0x2F3136,
                )
                if message.attachment is not None:
                    embed.set_image(url=message.attachment)
                if len(content) > 1:
                    for page in content:
                        embed.add_field(name="Message Continued", value=page)
                embed.set_footer(
                    text=f"Sniped by: {ctx.author}",
                    icon_url=ctx.author.display_avatar.url,
                )
                if author:
                    embed.set_author(
                        name=f"{author} ({author.id})",
                        icon_url=author.display_avatar.url,
                    )
                else:
                    embed.set_author(name="Unknown Member")
                embeds.append(embed)
            if len(embeds) == 1:
                return await ctx.reply(embed=embeds[0], mention_author=False)
            await BaseMenu(embeds, timeout=120).start(ctx)
        else:
            await ctx.reply("There's nothing to snipe!")

    @staticmethod
    def get_content(content: str, limit: int = 1024):
        return content if len(content) <= limit else f"{content[:limit - 3]}..."

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["es"])
    async def editsnipe(
        self,
        ctx: commands.Context,
        index: int = None,
        channel: discord.TextChannel = None,
    ):
        """Shows the last deleted messages of a channel."""
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        message: Optional[MiniMsg] = None
        if index is None:
            # Getting last message
            for msg_obj in reversed(self.edit_cache[channel.id]):
                if msg_obj.old_content:
                    message = msg_obj
                    break
        else:
            try:
                message = self.edit_cache[channel.id][-index]
            except IndexError:
                return await ctx.reply("There's nothing to snipe!")
        if message:
            author = message.author
            embed = discord.Embed(
                timestamp=datetime.datetime.fromtimestamp(message.edited_at),
                color=0x2F3136,
            )
            old_content = self.get_content(message.old_content)
            new_content = self.get_content(message.new_content)
            embed.add_field(name="Old Message:", value=old_content, inline=True)
            embed.add_field(name="New Message:", value=new_content, inline=True)
            embed.set_footer(
                text=f"Sniped by: {str(ctx.author)}",
                icon_url=ctx.author.display_avatar.url,
            )
            if message.old_attachment is not None:
                embed.set_image(url=message.old_attachment)
            if author is None:
                embed.set_author(name="Unknown Member")
            else:
                embed.set_author(
                    name=f"{author} ({author.id})", icon_url=author.display_avatar.url
                )
            await self.reply(ctx, embed=embed, mention_author=False)
        else:
            return await ctx.reply("There's nothing to snipe!")

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["eu"])
    async def editsnipeuser(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: discord.TextChannel = None,
    ):
        """Snipe a user's past edited messages in the current channel."""
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.edit_cache[channel.id]:
            user_msgs = [
                msg
                for msg in reversed(self.edit_cache[channel.id])
                if msg.old_content and msg.author.id == user.id
            ]
            if user_msgs:
                embeds = []
                for message in user_msgs:
                    author = message.author
                    embed = discord.Embed(
                        timestamp=datetime.datetime.fromtimestamp(message.edited_at),
                        color=0x2F3136,
                    )
                    old_content = self.get_content(message.old_content)
                    new_content = self.get_content(message.new_content)
                    embed.add_field(name="Old Message:", value=old_content, inline=True)
                    embed.add_field(name="New Message:", value=new_content, inline=True)
                    embed.set_footer(
                        text=f"Sniped by: {str(ctx.author)}",
                        icon_url=ctx.author.display_avatar.url,
                    )
                    if message.old_attachment is not None:
                        embed.set_image(url=message.old_attachment)
                    if author is None:
                        embed.set_author(name="Unknown Member")
                    else:
                        embed.set_author(
                            name=f"{author} ({author.id})",
                            icon_url=author.display_avatar.url,
                        )
                    embeds.append(embed)
                if len(embeds) == 1:
                    return await self.reply(ctx, embed=embeds[0], mention_author=False)
                await BaseMenu(embeds, timeout=120).start(ctx)
            else:
                await ctx.reply("There's nothing to snipe!")
        else:
            await ctx.reply("There's nothing to snipe!")

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["esb"])
    async def editsnipebulk(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """Snipe all the last edited messages in this channel."""
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.edit_cache[channel.id]:
            entries = [
                msg
                for msg in reversed(self.edit_cache[channel.id])
                if msg.old_content or msg.old_attachment
            ]
            embeds = []
            for message in entries:
                author = message.author
                embed = discord.Embed(
                    timestamp=datetime.datetime.fromtimestamp(message.edited_at),
                    color=0x2F3136,
                )
                old_content = self.get_content(message.old_content)
                new_content = self.get_content(message.new_content)
                embed.add_field(name="Old Message:", value=old_content, inline=True)
                embed.add_field(name="New Message:", value=new_content, inline=True)
                embed.set_footer(
                    text=f"Sniped by: {str(ctx.author)}",
                    icon_url=ctx.author.display_avatar.url,
                )
                if message.old_attachment is not None:
                    embed.set_image(url=message.old_attachment)
                if author is None:
                    embed.set_author(name="Unknown Member")
                else:
                    embed.set_author(
                        name=f"{author} ({author.id})",
                        icon_url=author.display_avatar.url,
                    )
                embeds.append(embed)
            if len(embeds) == 1:
                return await self.reply(ctx, embed=embeds[0], mention_author=False)
            await BaseMenu(embeds, timeout=120).start(ctx)
        else:
            await ctx.reply("There's nothing to snipe!")

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["rs"])
    async def reactionsnipe(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
        index: int = None,
    ):
        """
        Snipe a removed reaction from a message.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.reaction_cache[channel.id]:
            if index is None:
                index = len(self.reaction_cache[channel.id]) - 1
            if index < 0 or index >= len(self.reaction_cache[channel.id]):
                return await ctx.reply("Invalid index!")
            message = self.reaction_cache[channel.id][index]
            author = ctx.guild.get_member(message.reactor)
            embed = discord.Embed(
                timestamp=datetime.datetime.fromtimestamp(message.reacted_at),
                color=0x2F3136,
            )
            embed.set_thumbnail(url=message.emote.url)
            embed.add_field(
                name="Emote:", value=f"`{str(message.emote)}`", inline=False
            )
            embed.add_field(
                name="Message:",
                value=f"[`Jump To Message`]({message.message})",
                inline=False,
            )
            embed.set_footer(
                text=f"Sniped by: {str(ctx.author)}",
                icon_url=ctx.author.display_avatar.url,
            )
            embed.set_author(
                name=f"{author} ({author.id})",
                icon_url=author.display_avatar.url,
            )
            return await self.reply(ctx, embed=embed, mention_author=False)
        else:
            await ctx.reply("There's nothing to snipe!")

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["rsu"])
    async def reactsnipeuser(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: discord.TextChannel = None,
    ):
        """Snipe a remove reaction from a message by sorting user and channel."""
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.reaction_cache[channel.id]:
            user_msgs = [
                msg
                for msg in reversed(self.reaction_cache[channel.id])
                if msg.reactor == user.id
            ]
            if user_msgs:
                embeds = []
                for message in user_msgs:
                    author = ctx.guild.get_member(message.reactor)
                    embed = discord.Embed(
                        timestamp=datetime.datetime.fromtimestamp(message.reacted_at),
                        color=0x2F3136,
                    )
                    embed.set_thumbnail(url=message.emote.url)
                    embed.add_field(
                        name="Emote:", value=f"`{str(message.emote)}`", inline=False
                    )
                    embed.add_field(
                        name="Message:",
                        value=f"[`Jump To Message`]({message.message})",
                        inline=False,
                    )
                    embed.set_footer(
                        text=f"Sniped by: {ctx.author}",
                        icon_url=ctx.author.display_avatar.url,
                    )
                    embed.set_author(
                        name=f"{author} ({author.id})",
                        icon_url=author.display_avatar.url,
                    )
                    embeds.append(embed)
                await BaseMenu(embeds, timeout=120).start(ctx)
            else:
                await ctx.reply("There's nothing to snipe!")
        else:
            await ctx.reply("There's nothing to snipe!")

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["rsb"])
    async def reactsnipebulk(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """Snipe message reactions on bulk"""
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.reaction_cache[channel.id]:
            entries = [
                msg
                for msg in reversed(self.reaction_cache[channel.id])
                if msg.channel == channel.id
            ]
            embeds = []
            for message in entries:
                author = ctx.guild.get_member(message.reactor)
                embed = discord.Embed(
                    timestamp=datetime.datetime.fromtimestamp(message.reacted_at),
                    color=0x2F3136,
                )
                embed.set_thumbnail(url=message.emote.url)
                embed.add_field(
                    name="Emote:", value=f"`{str(message.emote)}`", inline=True
                )
                embed.add_field(
                    name="Message:",
                    value=f"[`Jump To Message`]({message.message})",
                    inline=True,
                )
                embed.set_footer(
                    text=f"Sniped by: {ctx.author}",
                    icon_url=ctx.author.display_avatar.url,
                )
                embed.set_author(
                    name=f"{author}",
                    icon_url=author.display_avatar.url,
                )
                embeds.append(embed)
            if len(embeds) == 1:
                return await self.reply(ctx, embed=embeds[0], mention_author=False)
            await BaseMenu(embeds, timeout=120).start(ctx)
        else:
            await ctx.reply("There's nothing to snipe!")

    @commands.is_owner()
    @commands.command()
    async def snipestats(self, ctx: commands.Context):
        """Show stats about snipe usage"""
        del_size = self.recursive_getsizeof(self.delete_cache)
        edit_size = self.recursive_getsizeof(self.edit_cache)
        reaction_size = self.recursive_getsizeof(self.reaction_cache)
        emb = discord.Embed(title="Snipe Stats", color=0x2F3136)
        emb.set_author(name=str(ctx.bot.user), icon_url=ctx.bot.user.display_avatar.url)
        emb.add_field(
            name="Delete Cache Size", value=self.sizeof_fmt(del_size), inline=False
        )
        emb.add_field(
            name="Edit Cache Size", value=self.sizeof_fmt(edit_size), inline=False
        )
        emb.add_field(
            name="Reaction Cache Size",
            value=self.sizeof_fmt(reaction_size),
            inline=False,
        )
        emb.add_field(
            name="Total Cache Size",
            value=self.sizeof_fmt(del_size + edit_size + reaction_size),
            inline=False,
        )
        emb.add_field(
            name="Cache Entries",
            value="Snipes: {}\nEdits: {}\nReactions: {}".format(
                sum(len(i) for i in self.delete_cache.values()),
                sum(len(i) for i in self.edit_cache.values()),
                sum(len(i) for i in self.reaction_cache.values()),
            ),
            inline=False,
        )
        emb.set_footer(
            text=f"Requested by: {(str(ctx.author))}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=emb)


async def setup(bot: Grief):
    await bot.add_cog(Snipe(bot))
