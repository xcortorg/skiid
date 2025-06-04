import asyncio
import datetime
import io
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

import aiohttp
import asyncpg
import discord
from config import color, emoji
from discord.ext import commands
from discord.utils import format_dt, utcnow
from system.base.context import Context


class Moderation(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.session = aiohttp.ClientSession()

    # OTHERS

    async def send_dm(self, ctx, member, action, reason=None):
        embed = discord.Embed(color=color.default)
        embed.set_author(
            name=f"You have been {'Kicked' if action == 'kick' else 'Banned'} by: {ctx.author.name}",
            icon_url=ctx.author.avatar.url,
        )
        embed.add_field(name="Reason", value=f"> {reason if reason else 'None'}")
        embed.add_field(
            name="Time",
            value=f"> {discord.utils.format_dt(datetime.datetime.now(), style='F')}",
        )
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Sent from: {ctx.guild.name}")

        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    def time(self, time_value: int, unit: str) -> int:
        if unit == "m":
            return time_value * 60
        elif unit == "h":
            return time_value * 3600
        else:
            return time_value * 86400

    async def fetch_image(self, ctx, url):
        if url is None and len(ctx.message.attachments) > 0:
            url = ctx.message.attachments[0].url

        if url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return io.BytesIO(await response.read())
                    else:
                        await ctx.deny(
                            "**Could not** download the image, make sure the link is valid"
                        )
                        return None
        else:
            await ctx.warn("**Provide** a valid link or image")
            return None

    def serverinfo(self, guild):
        boosts = guild.premium_subscription_count
        user_count_with_bots = sum(not user.bot for user in guild.members)
        return boosts, user_count_with_bots

    def variables(self, message, user, guild):
        if not message:
            return "contact support: discord.gg/strict"

        placeholders = {
            "{user.mention}": user.mention,
            "{user.name}": user.name,
            "{user.id}": str(user.id),
            "{guild.name}": guild.name,
            "{guild.id}": str(guild.id),
            "{boosts}": str(guild.premium_subscription_count),
            "{user.count}": str(guild.member_count),
        }

        for key, value in placeholders.items():
            message = message.replace(key, value)

        return message

    # COMMANDS

    @commands.command(description="Ban a user")
    @commands.has_permissions(ban_members=True)
    async def ban(
        self, ctx: commands.Context, member: discord.Member = None, *, reason=None
    ):
        if member is None:
            await ctx.warn("**Mention** a user")
            return
        if member.top_role >= ctx.author.top_role:
            await ctx.deny("You **cannot** ban someone with an equal or higher role")
            return

        result = await self.client.pool.fetchrow(
            "SELECT message FROM invoke WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            "ban",
        )
        custom_message = result["message"] if result else None

        await member.ban(reason=reason)

        if custom_message:
            await ctx.send(self.variables(custom_message, member, ctx.guild))
        else:
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Softban a user")
    @commands.has_permissions(ban_members=True)
    async def softban(
        self, ctx: commands.Context, member: discord.Member = None, *, reason=None
    ):
        if member is None:
            await ctx.warn("**Mention** a user")
            return
        if member.top_role >= ctx.author.top_role:
            await ctx.deny(
                "You **cannot** softban someone with an equal or higher role"
            )
            return

        result = await self.client.pool.fetchrow(
            "SELECT message FROM invoke WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            "softban",
        )
        custom_message = result["message"] if result else None

        await member.ban(reason=reason)
        await ctx.guild.unban(member)

        if custom_message:
            await ctx.send(self.variables(custom_message, member, ctx.guild))
        else:
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Unban a user")
    @commands.has_permissions(ban_members=True)
    async def unban(
        self, ctx: commands.Context, member: discord.User = None, *, reason=None
    ):
        if member is None:
            await ctx.warn("**Mention** a user")
            return

        result = await self.client.pool.fetchrow(
            "SELECT message FROM invoke WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            "unban",
        )
        custom_message = result["message"] if result else None

        await ctx.guild.unban(member)

        if custom_message:
            await ctx.send(self.variables(custom_message, member, ctx.guild))
        else:
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Kick a user")
    @commands.has_permissions(kick_members=True)
    async def kick(
        self, ctx: commands.Context, member: discord.Member = None, *, reason=None
    ):
        if member is None:
            await ctx.warn("**Mention** a user")
            return
        if member.top_role >= ctx.author.top_role:
            await ctx.deny("You **cannot** kick someone with an equal or higher role")
            return

        result = await self.client.pool.fetchrow(
            "SELECT message FROM invoke WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            "kick",
        )
        custom_message = result["message"] if result else None

        await member.kick(reason=reason)

        if custom_message:
            await ctx.send(self.variables(custom_message, member, ctx.guild))
        else:
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Recreate a channel")
    @commands.has_permissions(administrator=True)
    async def nuke(self, ctx):
        position = ctx.channel.position
        new = await ctx.channel.clone(reason="Nuked")
        await ctx.channel.delete(reason="Nuked")
        await new.edit(position=position)
        await new.send("first")

    @commands.command(description="Mute a user", aliases=["shush", "timeout", "to"])
    @commands.has_permissions(ban_members=True)
    async def mute(
        self,
        ctx: Context,
        member: Optional[discord.Member] = None,
        duration: str = "5m",
    ):
        if member is None:
            await ctx.warn("**Mention** a user")
            return
        if member.top_role >= ctx.author.top_role:
            await ctx.deny("You **cannot** mute someone with an equal or higher role")
            return

        time_units = {"m": "minutes", "h": "hours", "d": "days"}
        unit = duration[-1]
        if unit not in time_units:
            await ctx.deny(
                f"**Invalid unit,** use m(minutes), s(seconds), h(hours) and so on"
            )
            return

        try:
            time_value = int(duration[:-1])
        except ValueError:
            await ctx.warn("You're **missing** time")
            return

        seconds = self.time(time_value, unit)
        mute_until = discord.utils.utcnow() + timedelta(seconds=seconds)
        await member.timeout(mute_until)
        formatted_duration = f"{time_value} {time_units[unit]}"
        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Unmute a user", aliases=["untimeout", "unto"])
    @commands.has_permissions(ban_members=True)
    async def unmute(
        self, ctx: commands.Context, member: Optional[discord.Member] = None
    ):
        if member is None:
            await ctx.warn("**Mention** a user")
            return
        await member.edit(timed_out_until=None)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.group(description="Manage threads")
    @commands.has_permissions(manage_threads=True)
    async def thread(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @thread.command(name="lock", description="Lock a thread")
    @commands.has_permissions(manage_threads=True)
    async def thread_lock(self, ctx: Context, thread: discord.Thread = None):
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.warn("**Execute** this in a thread")
                return
        await thread.edit(locked=True)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @thread.command(name="unlock", description="Unlock a thread")
    @commands.has_permissions(manage_threads=True)
    async def thread_unlock(self, ctx: Context, thread: discord.Thread = None):
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.warn("**Execute** this in a thread")
                return
        await thread.edit(locked=False)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @thread.command(name="delete", description="Delete a thread")
    @commands.has_permissions(manage_threads=True)
    async def thread_delete(self, ctx, thread: discord.Thread = None):
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.warn("**Execute** this in a thread")
                return
        await thread.delete()
        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Lock a channel")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: Context, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Unlock a channel")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: Context, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Clear messages", aliases=["purge"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = None):
        if amount is None:
            await ctx.warn("You're **missing a number**")
        else:
            deleted_messages = await ctx.channel.purge(limit=amount + 1)
            embed = discord.Embed(
                description=f"> {emoji.agree} {ctx.author.mention}: **Deleted** {len(deleted_messages) - 1} messages",
                color=color.agree,
            )
            await ctx.send(embed=embed, delete_after=2)

    @commands.group(
        description="Manage roles", invoke_without_command=True, aliases=["r"]
    )
    @commands.has_permissions(manage_roles=True)
    async def role(
        self, ctx, member: discord.Member = None, *, role: discord.Role = None
    ):
        if not member or not role:
            await ctx.send_help(ctx.command.qualified_name)
            return

        if ctx.author.top_role.position <= role.position:
            await ctx.deny(
                f"You **cannot** interact with this role since it's higher than yours"
            )
            return

        if role in member.roles:
            await member.remove_roles(role)
            embed = discord.Embed(
                description=f"> <:remove:1302374923544690769> {ctx.author.mention}: **Removed** {role.mention} from {member.mention}",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
        else:
            await member.add_roles(role)
            embed = discord.Embed(
                description=f"> <:add:1302374903672078447> {ctx.author.mention}: **Added** {role.mention} to {member.mention}",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)

    @role.command(name="create", description="Create a role")
    @commands.has_permissions(manage_roles=True)
    async def role_create(self, ctx, *, name):
        new_role = await ctx.guild.create_role(name=name)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @role.command(name="delete", description="Delete a role")
    @commands.has_permissions(manage_roles=True)
    async def role_delete(self, ctx, *, role: discord.Role = None):
        if role is None:
            ctx.warn("**Mention** a role")
        await role.delete()
        await ctx.message.add_reaction(f"{emoji.agree}")

    @role.command(name="rename", description="Rename a role")
    @commands.has_permissions(manage_roles=True)
    async def role_rename(self, ctx, role: discord.Role = None, *, name):
        if role is None:
            ctx.warn("**Mention** a role")
        await role.edit(name=name)
        await ctx.message.add_reaction(f"{emoji.agree}")

    async def find_role(ctx, role_name):
        role = discord.utils.find(
            lambda r: r.name.lower() == role_name.lower(), ctx.guild.roles
        )
        if not role:
            role = discord.utils.find(
                lambda r: role_name.lower() in r.name.lower(), ctx.guild.roles
            )
        return role

    @role.command(name="all", description="Give a role to everyone")
    @commands.has_permissions(manage_roles=True)
    async def role_all(self, ctx, role: discord.Role = None):
        if role is None:
            await ctx.warn(f"**Mention** a role")
            return
        elif ctx.author.top_role.position <= role.position:
            await ctx.deny(
                f"You **cannot** interact with this role since it's higher than yours"
            )
            return

        index = 0
        embed = discord.Embed(
            description=f"> <:cooldown:1302376391274139750> {ctx.author.mention}: **Adding** {role.mention} to everyone",
            color=color.agree,
        )
        message = await ctx.send(embed=embed)

        for member in ctx.guild.members:
            if role not in member.roles:
                await member.add_roles(
                    role, reason=f"Mass role all from: {ctx.author.name}"
                )
                index += 1
                embed.description = f"> <:cooldown:1302376391274139750> {ctx.author.mention}: **Added** {role.mention} to {index} people"
                await message.edit(embed=embed)
                await asyncio.sleep(0.3)

        embed.description = f"> {emoji.agree} {ctx.author.mention}: **Added** {role.mention} to everyone!"
        await message.edit(embed=embed)

    @role.command(name="bots", description="Give a role to bots")
    @commands.has_permissions(manage_roles=True)
    async def role_bots(self, ctx, role: discord.Role = None):
        if role is None:
            await ctx.warn(f"**Mention** a role")
            return
        elif ctx.author.top_role.position <= role.position:
            await ctx.deny(
                f"You **cannot** interact with this role since it's higher than yours"
            )
            return

        index = 0
        embed = discord.Embed(
            description=f"> <:cooldown:1302376391274139750> {ctx.author.mention}: **Adding** {role.mention} to bots",
            color=color.agree,
        )
        message = await ctx.send(embed=embed)

        for member in ctx.guild.members:
            if member.bot and role not in member.roles:
                await member.add_roles(
                    role, reason=f"Mass bot role from: {ctx.author.name}"
                )
                index += 1
                embed.description = f"> <:cooldown:1302376391274139750> {ctx.author.mention}: **Added** {role.mention} to {index} bots"
                await message.edit(embed=embed)
                await asyncio.sleep(0.3)

        embed.description = f"> {emoji.agree} {ctx.author.mention}: **Added** {role.mention} to all the bots!"
        await message.edit(embed=embed)

    @role.command(name="humans", description="Give a role to humans (non-bots)")
    @commands.has_permissions(manage_roles=True)
    async def role_humans(self, ctx, role: discord.Role = None):
        if role is None:
            await ctx.warn(f"**Mention** a role")
            return
        elif ctx.author.top_role.position <= role.position:
            await ctx.deny(
                f"You **cannot** interact with this role since it's higher than yours"
            )
            return

        index = 0
        embed = discord.Embed(
            description=f"> <:cooldown:1302376391274139750> {ctx.author.mention}: **Adding** {role.mention} to humans",
            color=color.agree,
        )
        message = await ctx.send(embed=embed)

        for member in ctx.guild.members:
            if not member.bot and role not in member.roles:
                await member.add_roles(
                    role, reason=f"Mass human role from: {ctx.author.name}"
                )
                index += 1
                embed.description = f"> <:cooldown:1302376391274139750> {ctx.author.mention}: **Added** {role.mention} to {index} humans"
                await message.edit(embed=embed)
                await asyncio.sleep(0.3)

        embed.description = f"> {emoji.agree} {ctx.author.mention}: **Added** {role.mention} to all humans!"
        await message.edit(embed=embed)

    @commands.command(description="Set a slowmode for a channel")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, duration: str = "5m"):
        time_units = {"m": "minutes", "h": "hours", "d": "days"}
        unit = duration[-1]

        if unit not in time_units:
            await ctx.deny(
                f"**Invalid unit,** use m(minutes), s(seconds), h(hours) and so on"
            )
            return

        try:
            time_value = int(duration[:-1])
        except ValueError:
            await ctx.warn("You're **missing** time")
            return

        seconds = self.time(time_value, unit)
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.group(description="Manage your guild", aliases=["guild"])
    @commands.has_permissions(manage_guild=True)
    async def set(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @set.command(description="Change the avatar of your guild", aliases=["avatar"])
    @commands.has_permissions(manage_guild=True)
    async def pfp(self, ctx, url: str = None):
        if url is None and not ctx.message.attachments:
            await ctx.warn("**Provide** a valid link or image")
            return

        image_data = await self.fetch_image(ctx, url)
        if image_data:
            try:
                await ctx.guild.edit(icon=image_data.read())
                await ctx.message.add_reaction(f"{emoji.agree}")
            except discord.HTTPException:
                await ctx.deny("**Could not** change the avatar of the guild")

    @set.command(description="Change the banner of your guild", aliases=["bnner"])
    @commands.has_permissions(manage_guild=True)
    async def banner(self, ctx, url: str = None):
        if url is None and not ctx.message.attachments:
            await ctx.warn("**Provide** a valid link or image")
            return

        image_data = await self.fetch_image(ctx, url)
        if image_data:
            try:
                await ctx.guild.edit(banner=image_data.read())
                await ctx.message.add_reaction(f"{emoji.agree}")
            except discord.HTTPException:
                await ctx.deny(
                    "**Could not** change the banner of the guild, make sure your server is boosted to level 2"
                )

    @set.command(description="Change the splash of your guild", aliases=["splsh"])
    @commands.has_permissions(manage_guild=True)
    async def splash(self, ctx, url: str = None):
        if url is None and not ctx.message.attachments:
            await ctx.warn("**Provide** a valid link or image")
            return

        image_data = await self.fetch_image(ctx, url)
        if image_data:
            try:
                await ctx.guild.edit(splash=image_data.read())
                await ctx.message.add_reaction(f"{emoji.agree}")
            except discord.HTTPException:
                await ctx.send(
                    "**Could not** change the splash of the guild, make sure your server is boosted to level 1"
                )

    @set.command(description="Change the name of your guild")
    @commands.has_permissions(manage_guild=True)
    async def name(self, ctx, *, name: str):
        await ctx.guild.edit(name=name)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(
        description="Remove peoples ability to send attachments", aliases=["imute"]
    )
    @commands.has_permissions(manage_channels=True)
    async def imagemute(
        self, ctx, user: discord.Member, channel: discord.TextChannel = None
    ):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(user)

        overwrite.attach_files = False
        overwrite.embed_links = False
        await channel.set_permissions(user, overwrite=overwrite)
        await ctx.agree(
            f"**Muted** {user.mention}'s ability to send images in {channel.mention}"
        )

    @commands.command(description="Remove peoples ability to react", aliases=["rmute"])
    @commands.has_permissions(manage_channels=True)
    async def reactionmute(
        self, ctx, user: discord.Member, channel: discord.TextChannel = None
    ):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(user)

        overwrite.add_reactions = False
        await channel.set_permissions(user, overwrite=overwrite)
        await ctx.agree(
            f"**Muted** {user.mention}'s ability to react in {channel.mention}"
        )

    @commands.command(description="Pin a message")
    @commands.has_permissions(manage_messages=True)
    async def pin(self, ctx):
        if ctx.message.reference is None:
            await ctx.warn("**You** need to reply to a message")
            return

        pinned = await ctx.channel.fetch_message(ctx.message.reference.message_id)

        if pinned.pinned:
            await pinned.unpin()
            await ctx.message.add_reaction(f"{emoji.agree}")
        else:
            await pinned.pin()
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.group(description="Manage emojis")
    @commands.has_permissions(manage_emojis=True)
    async def emoji(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @emoji.command(name="steal", description="Steal emojis", aliases=["add"])
    @commands.has_permissions(manage_emojis=True)
    async def emoji_steal(self, ctx, emoji: discord.PartialEmoji, *, name: str = None):
        name = name or emoji.name
        async with self.client.session.get(str(emoji.url)) as response:
            if response.status != 200:
                await ctx.deny(f"**Could** not download the emoji")
                return

            emoji_data = BytesIO(await response.read())

        ext = "gif" if emoji.animated else "png"
        new_emoji = await ctx.guild.create_custom_emoji(
            name=name, image=emoji_data.getvalue()
        )

        await ctx.agree(f"**Added** {new_emoji} as `{name}`")

    @emoji.command(
        name="stealmore",
        description="Steal multiple emojis at once",
        aliases=["stealmultiple"],
    )
    @commands.has_permissions(manage_emojis=True)
    async def emoji_stealmore(self, ctx, *, emojis: str):
        added_emojis = []

        emoji_pattern = re.compile(
            r"<a?:\w+:\d+>|[\U00010000-\U0010ffff]", flags=re.UNICODE
        )

        emoji_matches = emoji_pattern.findall(emojis)

        if not emoji_matches:
            await ctx.deny("**Could not** find any valid emojis.")
            return

        for emoji_str in emoji_matches:
            try:
                emoji = await commands.PartialEmojiConverter().convert(ctx, emoji_str)
            except commands.BadArgument:
                await ctx.deny(f"**Could** not process emoji: {emoji_str}")
                continue

            async with self.client.session.get(str(emoji.url)) as response:
                if response.status != 200:
                    await ctx.deny(f"**Could** not download emoji: {emoji_str}")
                    continue

                emoji_data = BytesIO(await response.read())

            if emoji.animated and len(emoji_data.getvalue()) > 256 * 1024:
                continue

            new_emoji = await ctx.guild.create_custom_emoji(
                name=emoji.name, image=emoji_data.getvalue()
            )
            added_emojis.append(str(new_emoji))

        if added_emojis:
            await ctx.agree(f"**Added** {', '.join(added_emojis)}")

    @emoji.command(
        name="delete",
        description="Delete emojis",
    )
    @commands.has_permissions(manage_emojis=True)
    async def emoji_delete(self, ctx, *emojis: discord.Emoji):
        for emoji in emojis:
            await emoji.delete()
            await ctx.agree(f"**Deleted** {emoji}")

    @commands.group(description="Manage sticker")
    @commands.has_permissions(manage_emojis_and_stickers=True)
    async def sticker(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @sticker.command(name="steal", description="Steal stickers")
    @commands.has_permissions(manage_emojis_and_stickers=True)
    async def sticker_steal(self, ctx, name: str):
        if not ctx.message.reference:
            await ctx.warn("**Reply** to a message")
            return

        message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if not message.stickers:
            await ctx.deny("That message **doesn't** have a sticker")
            return

        sticker = message.stickers[0]

        async with self.client.session.get(str(sticker.url)) as response:
            if response.status != 200:
                await ctx.deny(f"**Could** not download the sticker")
                return
            sticker_data = BytesIO(await response.read())

        url = f"https://discord.com/api/v10/guilds/{ctx.guild.id}/stickers"
        headers = {"Authorization": f"Bot {self.client.http.token}"}

        form_data = aiohttp.FormData()
        form_data.add_field("name", name)
        form_data.add_field("description", "added by myth")
        form_data.add_field("tags", name)
        form_data.add_field(
            "file",
            sticker_data.getvalue(),
            filename="sticker.png",
            content_type="image/png",
        )

        async with self.client.session.post(
            url, headers=headers, data=form_data
        ) as response:
            if response.status != 201:
                await ctx.deny(f"**Failed** to create sticker: {response.status}")
                return
            new_sticker = await response.json()

        await ctx.agree(f"**Added** `{new_sticker['name']}`")

    @sticker.command(name="delete", description="Delete stickers")
    @commands.has_permissions(manage_emojis_and_stickers=True)
    async def sticker_delete(self, ctx):
        if not ctx.message.reference:
            await ctx.warn("**Reply** to a message")
            return

        message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if not message.stickers:
            await ctx.deny("That message **doesn't** have a sticker")
            return

        sticker = message.stickers[0]
        await sticker.delete()
        await ctx.agree(f"**Deleted** `{sticker.name}`")

    @commands.command(description="Hide a channel")
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Unhide a channel")
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.message.add_reaction(f"{emoji.agree}")


async def setup(client):
    await client.add_cog(Moderation(client))
