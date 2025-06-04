from datetime import datetime

import asyncpg
import discord
from config import color, emoji
from discord.ext import commands
from system.base.context import Context


class Skullboard(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.user_reactions = {}
        self.skull_messages = {}

    @commands.group(
        description="Showcase your funny messages in your guild",
        aliases=["sk", "starboard"],
    )
    @commands.has_permissions(manage_channels=True)
    async def skullboard(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @skullboard.command(name="emoji", description="Set the skullboard emoji")
    @commands.has_permissions(manage_channels=True)
    async def skullboard_emoji(self, ctx, emoji: str):
        guild_id = ctx.guild.id
        existing = await self.client.pool.execute(
            "SELECT * FROM skullboard WHERE guild_id = $1", guild_id
        )

        if existing:
            await self.client.pool.execute(
                "UPDATE skullboard SET emoji = $1 WHERE guild_id = $2", emoji, guild_id
            )
        else:
            await self.client.pool.execute(
                "INSERT INTO skullboard (guild_id, emoji) VALUES ($1, $2)",
                guild_id,
                emoji,
            )

        await ctx.agree(f"**Set** the skullboard emoji to: {emoji}")

    @skullboard.command(
        name="channel", description="Set the skullboard channel", aliases=["chnnel"]
    )
    @commands.has_permissions(manage_channels=True)
    async def skullboard_channel(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            await ctx.warn("**Mention** a channel")
            return

        await self.client.pool.execute(
            "INSERT INTO skullboard (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        await ctx.agree(f"**Set** the skullboard channel to: {channel.mention}")

    @skullboard.command(name="count", description="Set the skullboard reaction count")
    @commands.has_permissions(manage_channels=True)
    async def skullboard_count(self, ctx, count: int):
        guild_id = ctx.guild.id
        existing = await self.client.pool.execute(
            "SELECT * FROM skullboard WHERE guild_id = $1", guild_id
        )

        if existing:
            await self.client.pool.execute(
                "UPDATE skullboard SET reaction_count = $1 WHERE guild_id = $2",
                count,
                guild_id,
            )
        else:
            await self.client.pool.execute(
                "INSERT INTO skullboard (guild_id, reaction_count) VALUES ($1, $2)",
                guild_id,
                count,
            )

        await ctx.agree(f"**Set** the skullboard count to: {count}")

    @skullboard.command(name="clear", description="Clear all skullboard settings")
    @commands.has_permissions(manage_channels=True)
    async def skullboard_clear(self, ctx: Context):
        await self.client.pool.execute(
            "DELETE FROM skullboard WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all skullboard settings")

    @skullboard.command(name="remove", description="Remove the skullboard channel")
    @commands.has_permissions(manage_channels=True)
    async def skullboard_remove(self, ctx):
        existing = await self.client.pool.fetchrow(
            "SELECT channel_id FROM skullboard WHERE guild_id = $1", ctx.guild.id
        )
        if existing:
            await self.client.pool.execute(
                "DELETE FROM skullboard WHERE guild_id = $1", ctx.guild.id
            )
            await ctx.agree("**Removed** the skullboard channel")
        else:
            await ctx.deny("A channel isn't **set**")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        guild_id = reaction.message.guild.id
        settings = await self.client.pool.fetchrow(
            "SELECT emoji, channel_id, reaction_count FROM skullboard WHERE guild_id = $1",
            guild_id,
        )

        emoji = settings["emoji"] if settings else "💀"
        channel_id = settings["channel_id"] if settings else None
        reaction_count = settings["reaction_count"] if settings else 1

        if str(reaction.emoji) == emoji:
            message_id = reaction.message.id
            user_id = user.id

            if message_id in self.user_reactions:
                if user_id in self.user_reactions[message_id]:
                    return
            else:
                self.user_reactions[message_id] = set()

            self.user_reactions[message_id].add(user_id)
            reaction_total = len(self.user_reactions[message_id])

            if reaction_total >= reaction_count:
                channel = self.client.get_channel(channel_id)

                if channel is None:
                    return

                embed = discord.Embed(
                    description=f"### **[#{reaction.message.channel.name}]({reaction.message.jump_url})**\n {reaction.message.content}",
                    color=color.default,
                )
                user_pfp = (
                    reaction.message.author.avatar.url
                    if reaction.message.author.avatar
                    else reaction.message.author.default_avatar.url
                )
                embed.set_author(name=reaction.message.author.name, icon_url=user_pfp)

                if reaction.message.reference:
                    ref_message = await reaction.message.channel.fetch_message(
                        reaction.message.reference.message_id
                    )
                    embed.add_field(
                        name="",
                        value=f"**[Replying]({ref_message.jump_url})** to {reaction.message.author.mention}",
                        inline=False,
                    )

                if reaction.message.attachments:
                    embed.set_image(url=reaction.message.attachments[0].url)

                embed.set_footer(text=f'Today at {datetime.utcnow().strftime("%H:%M")}')

                if message_id in self.skull_messages:
                    sent_message = self.skull_messages[message_id]
                    await sent_message.edit(
                        content=f"**#{reaction_total}** {emoji}", embed=embed
                    )
                else:
                    sent_message = await channel.send(
                        content=f"**#{reaction_total}** {emoji}", embed=embed
                    )
                    self.skull_messages[message_id] = sent_message

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot:
            return

        guild_id = reaction.message.guild.id
        settings = await self.client.pool.fetchrow(
            "SELECT emoji, channel_id, reaction_count FROM skullboard WHERE guild_id = $1",
            guild_id,
        )

        emoji = settings["emoji"] if settings else "💀"
        channel_id = settings["channel_id"] if settings else None
        reaction_count = settings["reaction_count"] if settings else 1

        if str(reaction.emoji) == emoji:
            message_id = reaction.message.id
            user_id = user.id

            if message_id in self.user_reactions:
                if user_id in self.user_reactions[message_id]:
                    self.user_reactions[message_id].remove(user_id)

                    reaction_total = len(self.user_reactions[message_id])

                    if message_id in self.skull_messages:
                        sent_message = self.skull_messages[message_id]
                        await sent_message.edit(
                            content=f"**#{reaction_total}** {emoji}"
                        )


async def setup(client):
    await client.add_cog(Skullboard(client))
