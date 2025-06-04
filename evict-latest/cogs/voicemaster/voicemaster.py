from typing import List, Tuple

import discord
from discord import Embed, HTTPException, RateLimited, VoiceState, TextStyle, Interaction
from discord.ext.commands import (
    BucketType,
    CommandError,
    cooldown,
    group,
    has_permissions,
)
from discord.utils import format_dt
from discord.ui import Modal, TextInput, View, Button

import config
from config import EMOJIS
from tools.converters import Bitrate, Member, Region, Role
from tools.converters.ratelimit import ratelimiter
from core.client.context import Context
from tools.utilities.managers.cog import Cog
from main import Evict
import json
from tools.conversion.embed import EmbedScript 

from .interface import Interface

class VoiceMaster(Cog):
    """Cog for VoiceMaster commands."""

    def __init__(self, bot: Evict):
        self.bot: Evict = bot
        self.description = "Allow server members to make automated voice channels."
        self.bot.add_view(Interface(bot))

    async def cog_load(self):
        schedule_deletion: List[Tuple[int]] = []

        for row in await self.bot.db.fetch(
            """
            SELECT channel_id FROM voicemaster.channels
            """
        ):
            channel_id: int = row.get("channel_id")
            if channel := self.bot.get_channel(channel_id):
                if not channel.members:
                    try:
                        await channel.delete(
                            reason="VoiceMaster: Flush empty voice channels"
                        )
                    except HTTPException:
                        pass

                    schedule_deletion.append((channel_id,))

            else:
                schedule_deletion.append((channel_id,))

        if schedule_deletion:
            await self.bot.db.executemany(
                """
                DELETE FROM voicemaster.channels
                WHERE channel_id = $1
                """,
                schedule_deletion,
            )

    @Cog.listener("on_voice_state_update")
    async def create_channel(
        self, member: discord.Member, before: VoiceState, after: VoiceState
    ):
        if not after.channel:
            return

        if before and before.channel == after.channel:
            return

        if not (
            configuration := await self.bot.db.fetchrow(
                """
                SELECT * FROM voicemaster.configuration
                WHERE guild_id = $1
                """,
                member.guild.id,
            )
        ):
            return

        if configuration.get("channel_id") != after.channel.id:
            return

        if _ := ratelimiter(
            "voicemaster:create",
            key=member,
            rate=1,
            per=10,
        ):
            try:
                await member.move_to(None)
            except HTTPException:
                pass

            return

        channel = await member.guild.create_voice_channel(
            name=f"{member.display_name}'s channel",
            category=(
                member.guild.get_channel(configuration.get("category_id"))
                or after.channel.category
            ),
            bitrate=(
                (
                    bitrate := configuration.get(
                        "bitrate", int(member.guild.bitrate_limit)
                    )
                )
                and (
                    bitrate
                    if bitrate <= int(member.guild.bitrate_limit)
                    else int(member.guild.bitrate_limit)
                )
            ),
            rtc_region=configuration.get("region"),
            reason=f"VoiceMaster: Created a voice channel for {member}",
        )

        try:
            await member.move_to(
                channel,
                reason="VoiceMaster: Created their own voice channel",
            )
        except HTTPException:
            await channel.delete(reason="VoiceMaster: Failed to move member")
            return

        await channel.set_permissions(
            member,
            read_messages=True,
            connect=True,
            reason=f"VoiceMaster: {member} created a new voice channel",
        )

        await self.bot.db.execute(
            """
            INSERT INTO voicemaster.channels (
                guild_id,
                channel_id,
                owner_id
            ) VALUES ($1, $2, $3)
            """,
            member.guild.id,
            channel.id,
            member.id,
        )

        if (
            role := member.guild.get_role(configuration.get("role_id"))
        ) and role not in member.roles:
            try:
                await member.add_roles(
                    role,
                    reason="VoiceMaster: Gave the owner the default role",
                )
            except Exception:
                pass

    @Cog.listener("on_voice_state_update")
    async def remove_channel(
        self, member: discord.Member, before: VoiceState, after: VoiceState
    ):
        if not before.channel:
            return

        if after and before.channel == after.channel:
            return

        if (
            (
                role_id := await self.bot.db.fetchval(
                    """
                SELECT role_id FROM voicemaster.configuration
                WHERE guild_id = $1
                """,
                    member.guild.id,
                )
            )
            and role_id in (role.id for role in member.roles)
        ):
            try:
                await member.remove_roles(
                    member.guild.get_role(role_id),
                    reason="VoiceMaster: Removed the default role",
                )
            except Exception:
                pass

        if list(filter(lambda m: not m.bot, before.channel.members)):
            return

        if not (
            _ := await self.bot.db.fetchval(
                """
                DELETE FROM voicemaster.channels
                WHERE channel_id = $1
                RETURNING owner_id
                """,
                before.channel.id,
            )
        ):
            return

        try:
            await before.channel.delete()
        except HTTPException:
            pass

    async def cog_check(self, ctx: Context) -> bool:
        if ctx.command.qualified_name in (
            "voicemaster",
            "voicemaster setup",
            "voicemaster reset",
            "voicemaster category",
            "voicemaster defaultrole",
            "voicemaster defaultregion",
            "voicemaster defaultbitrate",
            "voicemaster emoji",
            "voicemaster emoji set",
            "voicemaster emoji remove", 
            "voicemaster emoji reset",
            "voicemaster emoji list",
            "voicemaster layout",
            "voicemaster embed",
            "voicemaster embed set",
            "voicemaster embed delete",
            "voicemaster embed view",
            "voicemaster embed variables"
        ):
            return True

        if not ctx.author.voice:
            raise CommandError("You're not connected to a **voice channel**")

        if not (
            owner_id := await ctx.bot.db.fetchval(
                """
            SELECT owner_id FROM voicemaster.channels
            WHERE channel_id = $1
            """,
                ctx.author.voice.channel.id,
            )
        ):
            raise CommandError("You're not in a **VoiceMaster** channel!")

        if ctx.command.qualified_name == "voicemaster claim":
            if ctx.author.id == owner_id:
                raise CommandError(
                    "You already have **ownership** of this voice channel!"
                )

            if owner_id in (member.id for member in ctx.author.voice.channel.members):
                raise CommandError(
                    "You can't claim this **voice channel**, the owner is still active here."
                )

            return True

        if ctx.author.id != owner_id:
            raise CommandError("You don't own a **voice channel**!")

        return True

    @group(
        name="voicemaster",
        usage="(subcommand) <args>",
        example="setup",
        aliases=[
            "voice",
            "vm",
            "vc",
        ],
        invoke_without_command=True,
    )
    async def voicemaster(self, ctx: Context):
        """Make temporary voice channels in your server!"""
        return await ctx.send_help(ctx.command)

    @voicemaster.group(
        name="embed",
        invoke_without_command=True
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_embed(self, ctx: Context):
        """Manage the VoiceMaster interface embed"""
        await ctx.send_help(ctx.command)

    @voicemaster_embed.command(name="set")
    @has_permissions(manage_guild=True)
    async def voicemaster_embed_set(self, ctx: Context, *, embed_code: EmbedScript):
        """Set a custom embed for the VoiceMaster interface"""
        try:
            try:
                await embed_code.compile()
                if embed_code.objects.get('embeds'):
                    test_embed = embed_code.objects['embeds'][0]
                    await ctx.send(embed=test_embed, delete_after=1)
                else:
                    raise ValueError("No embed found in script")
            except Exception as e:
                return await ctx.warn(f"Invalid embed code: {e}")

            config = await self.bot.db.fetchrow(
                """
                SELECT * FROM voicemaster.configuration 
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )
            
            if config:
                await self.bot.db.execute(
                    """
                    UPDATE voicemaster.configuration 
                    SET interface_embed = $2
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id,
                    str(embed_code)
                )
            else:
                await self.bot.db.execute(
                    """
                    INSERT INTO voicemaster.configuration (
                        guild_id,
                        interface_embed
                    ) VALUES ($1, $2)
                    """,
                    ctx.guild.id,
                    str(embed_code)
                )
            
            await ctx.approve("Successfully updated the interface embed! Use `voicemaster setup` to apply changes.")
            
        except Exception as e:
            await ctx.warn(f"Failed to update embed: {e}")

    @voicemaster_embed.command(name="delete", aliases=["remove", "reset"])
    @has_permissions(manage_guild=True)
    async def voicemaster_embed_delete(self, ctx: Context):
        """Reset the interface embed to default"""
        await self.bot.db.execute(
            """
            UPDATE voicemaster.configuration 
            SET interface_embed = NULL
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        await ctx.approve("Reset interface embed to default! Use `voicemaster setup` to apply changes.")

    @voicemaster_embed.command(name="view", aliases=["show"])
    @has_permissions(manage_guild=True)
    async def voicemaster_embed_view(self, ctx: Context):
        """View the current interface embed code"""
        if embed_code := await self.bot.db.fetchval(
            """
            SELECT interface_embed FROM voicemaster.configuration 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        ):
            await ctx.send(f"```{embed_code}```")
        else:
            await ctx.warn("No custom embed configured")

    @voicemaster_embed.command(name="variables", aliases=["vars"])
    @has_permissions(manage_guild=True)
    async def voicemaster_embed_variables(self, ctx: Context):
        """View available variables for the interface embed"""
        await ctx.send(
            "Available variables for the interface embed:\n"
            "- `{lock}` - Lock emoji\n"
            "- `{unlock}` - Unlock emoji\n"
            "- `{ghost}` - Ghost emoji\n"
            "- `{reveal}` - Reveal emoji\n"
            "- `{claim}` - Claim emoji\n"
            "- `{disconnect}` - Disconnect emoji\n"
            "- `{activity}` - Activity emoji\n"
            "- `{information}` - Information emoji\n"
            "- `{increase}` - Increase emoji\n"
            "- `{decrease}` - Decrease emoji"
        )

    @voicemaster.command(name="setup")
    @has_permissions(manage_guild=True)
    async def voicemaster_setup(self, ctx: Context):
        """Begin VoiceMaster server configuration setup"""
        try:
            db_config = await self.bot.db.fetchrow(
                """
                SELECT * FROM voicemaster.configuration
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

            if db_config and any([db_config['category_id'], db_config['channel_id'], db_config['interface_id']]):
                return await ctx.warn(
                    "Server is already configured for **VoiceMaster**, run `voicemaster reset` to reset the **VoiceMaster** server configuration"
                )

            category = await ctx.guild.create_category(
                "Voice Channels", reason=f"{ctx.author} setup VoiceMaster"
            )
            
            interface = Interface(self.bot)
            await interface.create_channel(category, ctx.author)
            
            layout = db_config.get('interface_layout', 'default') if db_config else 'default'
            
            if layout == 'default':
                await interface.setup_buttons(ctx.guild.id)
            
            await interface.set_permissions(ctx.guild.default_role, ctx.author)
            
            channel = await category.create_voice_channel(
                "Join to Create", reason=f"{ctx.author} setup VoiceMaster"
            )

            try:
                existing_emojis = json.loads(db_config['interface_emojis']) if db_config and db_config['interface_emojis'] else {}
            except (TypeError, KeyError):
                existing_emojis = {}

            interface_emojis = {
                'LOCK': existing_emojis.get('LOCK', EMOJIS.INTERFACE.LOCK),
                'UNLOCK': existing_emojis.get('UNLOCK', EMOJIS.INTERFACE.UNLOCK),
                'GHOST': existing_emojis.get('GHOST', EMOJIS.INTERFACE.GHOST),
                'REVEAL': existing_emojis.get('REVEAL', EMOJIS.INTERFACE.REVEAL),
                'CLAIM': existing_emojis.get('CLAIM', EMOJIS.INTERFACE.CLAIM),
                'DISCONNECT': existing_emojis.get('DISCONNECT', EMOJIS.INTERFACE.DISCONNECT),
                'ACTIVITY': existing_emojis.get('ACTIVITY', EMOJIS.INTERFACE.ACTIVITY),
                'INFORMATION': existing_emojis.get('INFORMATION', EMOJIS.INTERFACE.INFORMATION),
                'INCREASE': existing_emojis.get('INCREASE', EMOJIS.INTERFACE.INCREASE),
                'DECREASE': existing_emojis.get('DECREASE', EMOJIS.INTERFACE.DECREASE),
            }

            if layout == 'default':
                if db_config and db_config.get('interface_embed'):
                    try:
                        embed_code = db_config['interface_embed']
                        script = EmbedScript(embed_code)
                        result = await script.compile()
                        if script.objects.get('embeds'):
                            embed = script.objects['embeds'][0]
                        else:
                            embed = Embed(
                                title="VoiceMaster Interface",
                                description="Click the buttons below to control your voice channel",
                            )
                            embed.set_author(
                                name=ctx.guild.name,
                                icon_url=ctx.guild.icon,
                            )
                            embed.set_thumbnail(url=self.bot.user.display_avatar)
                            field_value = self._create_button_field(interface_emojis)
                            embed.add_field(
                                name="**Button Usage**",
                                value=field_value
                            )
                    except Exception as e:
                        embed = self._create_default_embed(ctx.guild, interface_emojis)
                else:
                    embed = self._create_default_embed(ctx.guild, interface_emojis)
            else:
                if db_config and db_config.get('interface_embed'):
                    try:
                        embed_code = db_config['interface_embed']
                        script = EmbedScript(embed_code)
                        result = await script.compile()
                        if script.objects.get('embeds'):
                            embed = script.objects['embeds'][0]
                        else:
                            embed = Embed(
                                title="Voicemaster Control Menu",
                                description="control your voice channel using the dropdown below",
                                color=0x2B2D31
                            )
                            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
                            embed.set_thumbnail(url=self.bot.user.display_avatar)
                    except Exception as e:
                        embed = Embed(
                            title="Voicemaster Control Menu",
                            description="control your voice channel using the dropdown below",
                            color=0x2B2D31
                        )
                        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
                        embed.set_thumbnail(url=self.bot.user.display_avatar)
                else:
                    embed = Embed(
                        title="Voicemaster Control Menu",
                        description="control your voice channel using the dropdown below",
                        color=0x2B2D31
                    )
                    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
                    embed.set_thumbnail(url=self.bot.user.display_avatar)

            await interface.send(embed=embed)

            if db_config:
                await self.bot.db.execute(
                    """
                    UPDATE voicemaster.configuration 
                    SET category_id = $2, 
                        interface_id = $3, 
                        channel_id = $4,
                        interface_layout = $5
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id,
                    category.id,
                    interface.channel.id,
                    channel.id,
                    layout
                )
            else:
                await self.bot.db.execute(
                    """
                    INSERT INTO voicemaster.configuration (
                        guild_id,
                        category_id,
                        interface_id,
                        channel_id,
                        interface_emojis,
                        interface_layout,
                        interface_embed
                    ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                    """,
                    ctx.guild.id,
                    category.id,
                    interface.channel.id,
                    channel.id,
                    json.dumps(existing_emojis),
                    layout,
                    None
                )

            await ctx.approve(
                "Finished setting up the **VoiceMaster** channels. A category and two channels have been created, you can move the channels or rename them if you want."
            )
            return

        except Exception as e:
            raise

    @voicemaster.command(
        name="reset",
        aliases=["clear"]
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_reset(self, ctx: Context):
        """Reset VoiceMaster configuration"""
        try:
            await self.bot.db.execute(
                """
                DELETE FROM voicemaster.configuration 
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )

            await self.bot.db.execute(
                """
                DELETE FROM voicemaster.channels 
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )
        except Exception as e:
            return await ctx.warn(f"Failed to reset VoiceMaster: {str(e)}")

        return await ctx.approve("Successfully reset VoiceMaster configuration")

    @voicemaster.command(
        name="category",
        example="Voice Channels",
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_category(
        self, ctx: Context, *, channel: discord.CategoryChannel
    ):
        """Redirect voice channels to custom category"""
        try:
            await self.bot.db.execute(
                """
                UPDATE voicemaster.configuration
                SET category_id = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                channel.id,
            )
        except Exception:
            return await ctx.warn(
                "Server is not configured in the **database**, you need to run `voicemaster setup` to be able to run this command"
            )

        return await ctx.approve(
            f"Set **{channel}** as the default voice channel category"
        )

    @voicemaster.command(
        name="defaultrole",
        example="@vc",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def voicemaster_defaultrole(self, ctx: Context, *, role: Role):
        """Set a role that members get for being in a VM channel"""
        try:
            await self.bot.db.execute(
                """
                UPDATE voicemaster.configuration
                SET role_id = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                role.id,
            )
        except Exception:
            return await ctx.warn(
                "Server is not configured in the **database**, you need to run `voicemaster setup` to be able to run this command"
            )

        return await ctx.approve(
            f"Set {role.mention} as the default role for members in voice channels"
        )

    @voicemaster.command(
        name="defaultregion",
        example="russia",
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_defaultregion(self, ctx: Context, *, region: Region):
        """Edit default region for new Voice Channels"""
        try:
            await self.bot.db.execute(
                """
                UPDATE voicemaster.configuration
                SET region = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                region,
            )
        except Exception:
            return await ctx.warn(
                "Server is not configured in the **database**, you need to run `voicemaster setup` to be able to run this command"
            )

        return await ctx.approve(
            f"Set **{region}** as the default voice channel region"
        )

    @voicemaster.command(
        name="defaultbitrate",
        example="80kbps",
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_defaultbitrate(self, ctx: Context, *, bitrate: Bitrate):
        """Edit default bitrate for new Voice Channels"""
        try:
            await self.bot.db.execute(
                """
                UPDATE voicemaster.configuration
                SET bitrate = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                bitrate * 1000,
            )
        except Exception:
            return await ctx.warn(
                "Server is not configured in the **database**, you need to run `voicemaster setup` to be able to run this command"
            )

        return await ctx.approve(
            f"Set `{bitrate} kbps` as the default voice channel bitrate"
        )

    @voicemaster.command(
        name="configuration",
        aliases=[
            "config",
            "show",
            "view",
            "info",
        ],
    )
    async def voicemaster_configuration(self, ctx: Context):
        """See current configuration for current voice channel"""
        channel = ctx.author.voice.channel

        embed = Embed(
            title=channel.name,
            description=(
                f"**Owner:** {ctx.author} (`{ctx.author.id}`)"
                + "\n**Locked:** "
                + (
                    config.Emoji.approve
                    if channel.permissions_for(ctx.guild.default_role).connect is False
                    else config.Emoji.deny
                )
                + "\n**Created:** "
                + format_dt(
                    channel.created_at,
                    style="R",
                )
                + f"\n**Bitrate:** {int(channel.bitrate / 1000)}kbps"
                + f"\n**Connected:** `{len(channel.members)}`"
                + (f"/`{channel.user_limit}`" if channel.user_limit else "")
            ),
        )

        if roles_permitted := [
            target
            for target, overwrite in channel.overwrites.items()
            if overwrite.connect is True and isinstance(target, discord.Role)
        ]:
            embed.add_field(
                name="Role Permitted",
                value=", ".join(role.mention for role in roles_permitted),
                inline=False,
            )

        if members_permitted := [
            target
            for target, overwrite in channel.overwrites.items()
            if overwrite.connect is True
            and isinstance(target, discord.Member)
            and target != ctx.author
        ]:
            embed.add_field(
                name="Member Permitted",
                value=", ".join(member.mention for member in members_permitted),
                inline=False,
            )

        return await ctx.send(embed=embed)

    @voicemaster.command(name="claim")
    async def voicemaster_claim(self, ctx: Context):
        """Claim an inactive voice channel"""
        await self.bot.db.execute(
            """
            UPDATE voicemaster.channels
            SET owner_id = $2
            WHERE channel_id = $1
            """,
            ctx.author.voice.channel.id,
            ctx.author.id,
        )

        if ctx.author.voice.channel.name.endswith("channel"):
            try:
                await ctx.author.voice.channel.edit(
                    name=f"{ctx.author.display_name}'s channel"
                )
            except Exception:
                pass

        return await ctx.approve("You are now the owner of this **channel**!")

    @voicemaster.command(
        name="transfer",
        example="@x",
    )
    async def voicemaster_transfer(self, ctx: Context, *, member: Member):
        """Transfer ownership of your channel to another member"""
        if member == ctx.author or member.bot:
            return await ctx.send_help()

        if not member.voice or member.voice.channel != ctx.author.voice.channel:
            return await ctx.warn(f"**{member}** is not in your channel!")

        await self.bot.db.execute(
            """
            UPDATE voicemaster.channels
            SET owner_id = $2
            WHERE channel_id = $1
            """,
            ctx.author.voice.channel.id,
            member.id,
        )

        if ctx.author.voice.channel.name.endswith("channel"):
            try:
                await ctx.author.voice.channel.edit(
                    name=f"{member.display_name}'s channel"
                )
            except Exception:
                pass

        return await ctx.approve(f"**{member}** now has ownership of this channel")

    @voicemaster.command(
        name="name",
        example="priv channel",
        aliases=["rename"],
    )
    async def voicemaster_name(self, ctx: Context, *, name: str):
        """Rename your voice channel"""
        if len(name) > 100:
            return await ctx.warn(
                "Your channel's name cannot be longer than **100 characters**"
            )

        try:
            await ctx.author.voice.channel.edit(
                name=name,
                reason=f"VoiceMaster: {ctx.author} renamed voice channel",
            )
        except HTTPException:
            return await ctx.warn("Voice channel name cannot contain **vulgar words**")
        except RateLimited:
            return await ctx.warn(
                "Voice channel is being **rate limited**, try again later"
            )
        else:
            return await ctx.approve(
                f"Your **voice channel** has been renamed to `{name}`"
            )

    @voicemaster.command(
        name="bitrate",
        example="80kbps",
        aliases=["quality"],
    )
    async def voicemaster_bitrate(self, ctx: Context, bitrate: Bitrate):
        """Edit bitrate of your voice channel"""
        await ctx.author.voice.channel.edit(
            bitrate=bitrate * 1000,
            reason=f"VoiceMaster: {ctx.author} edited voice channel bitrate",
        )

        return await ctx.approve(
            f"Your **voice channel**'s bitrate has been updated to `{bitrate} kbps`"
        )

    @voicemaster.command(
        name="limit",
        example="3",
        aliases=["userlimit"],
    )
    async def voicemaster_limit(self, ctx: Context, limit: int):
        """Edit user limit of your voice channel"""
        if limit < 0:
            return await ctx.warn(
                "Channel member limit must be greater than **0 members**"
            )

        if limit > 99:
            return await ctx.warn(
                "Channel member limit cannot be more than **99 members**"
            )

        await ctx.author.voice.channel.edit(
            user_limit=limit,
            reason=f"VoiceMaster: {ctx.author} edited voice channel user limit",
        )

        return await ctx.approve(
            f"Your **voice channel**'s limit has been updated to `{limit}`"
        )

    @voicemaster.command(name="lock")
    async def voicemaster_lock(self, ctx: Context):
        """Lock your voice channel"""
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            connect=False,
            reason=f"VoiceMaster: {ctx.author} locked voice channel",
        )

        await ctx.message.add_reaction(config.EMOJIS.INTERFACE.LOCK)
        return await ctx.approve(f"Your **voice channel** has been locked")

    @voicemaster.command(name="unlock")
    async def voicemaster_unlock(self, ctx: Context):
        """Unlock your voice channel"""
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            connect=None,
            reason=f"VoiceMaster: {ctx.author} unlocked voice channel",
        )

        await ctx.message.add_reaction(config.EMOJIS.INTERFACE.UNLOCK)
        return await ctx.approve("Your **voice channel** has been unlocked")

    @voicemaster.command(name="ghost", aliases=["hide"])
    async def voicemaster_ghost(self, ctx: Context):
        """Hide your voice channel"""
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            view_channel=False,
            reason=f"VoiceMaster: {ctx.author} made voice channel hidden",
        )

        await ctx.message.add_reaction(config.EMOJIS.INTERFACE.GHOST)
        return await ctx.approve("Your **voice channel** has been hidden")

    @voicemaster.command(name="unghost", aliases=["reveal", "unhide"])
    async def voicemaster_unghost(self, ctx: Context):
        """Reveal your voice channel"""
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            view_channel=None,
            reason=f"VoiceMaster: {ctx.author} revealed voice channel",
        )

        await ctx.message.add_reaction(config.EMOJIS.INTERFACE.REVEAL)
        return await ctx.approve("Your **voice channel** has been revealed")

    @voicemaster.command(
        name="permit",
        example="@x",
        aliases=["allow"],
    )
    async def voicemaster_permit(self, ctx: Context, *, target: Member | Role):
        """Permit a member or role to join your VC"""
        await ctx.author.voice.channel.set_permissions(
            target,
            connect=True,
            view_channel=True,
            reason=f"VoiceMaster: {ctx.author} permitted {target} to join voice channel",
        )

        return await ctx.approve(
            f"Granted **connect permission** to {target.mention} to join"
        )

    @voicemaster.command(
        name="reject",
        example="@x",
        aliases=[
            "remove",
            "deny",
            "kick",
        ],
    )
    async def voicemaster_reject(self, ctx: Context, *, target: Member | Role):
        """Reject a member or role from joining your VC"""
        await ctx.author.voice.channel.set_permissions(
            target,
            connect=False,
            view_channel=None,
            reason=f"VoiceMaster: {ctx.author} rejected {target} from joining voice channel",
        )

        if isinstance(target, discord.Member):
            if (voice := target.voice) and voice.channel == ctx.author.voice.channel:
                await target.move_to(None)

        return await ctx.approve(
            f"Removed **connect permission** from {target.mention} to join"
        )

    @voicemaster.group(
        name="emoji",
        usage="(subcommand) <args>",
        example="set lock <:lock:1234567890>",
        aliases=["emojis"],
        invoke_without_command=True
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_emoji(self, ctx: Context):
        """Manage custom emojis for VoiceMaster buttons"""
        return await ctx.send_help(ctx.command)

    @voicemaster_emoji.command(
        name="set",
        example="lock 🔒"
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_emoji_set(self, ctx: Context, button: str, emoji: str):
        """Set a custom emoji for a VoiceMaster button"""
        valid_buttons = {
            "LOCK", "UNLOCK", "GHOST", "REVEAL", "CLAIM",
            "DISCONNECT", "ACTIVITY", "INFORMATION",
            "INCREASE", "DECREASE"
        }
        
        button = button.upper()
        if button not in valid_buttons:
            return await ctx.warn(
                f"Invalid button type. Valid options: {', '.join(valid_buttons)}"
            )

        if emoji.startswith("<") and emoji.endswith(">"):
            try:
                emoji_id = int(emoji.split(":")[-1][:-1])
                if not discord.utils.get(ctx.guild.emojis, id=emoji_id):
                    return await ctx.warn("That emoji is not from this server")
            except (ValueError, IndexError):
                return await ctx.warn("Invalid custom emoji format")
        else:
            if len(emoji) != 1 and not (emoji.startswith(":") and emoji.endswith(":")):
                return await ctx.warn("Please provide a valid emoji (custom or unicode)")

        try:
            exists = await self.bot.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM voicemaster.configuration 
                    WHERE guild_id = $1
                )
                """,
                ctx.guild.id
            )

            if not exists:
                await self.bot.db.execute(
                    """
                    INSERT INTO voicemaster.configuration (guild_id, interface_emojis)
                    VALUES ($1, $2::jsonb)
                    """,
                    ctx.guild.id,
                    json.dumps({button: emoji})
                )
            else:
                current_emojis = json.loads(await self.bot.db.fetchval(
                    """
                    SELECT interface_emojis 
                    FROM voicemaster.configuration 
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id
                ) or '{}')

                if not isinstance(current_emojis, dict):
                    current_emojis = {}

                current_emojis[button] = emoji

                await self.bot.db.execute(
                    """
                    UPDATE voicemaster.configuration 
                    SET interface_emojis = $2::jsonb
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id,
                    json.dumps(current_emojis)
                )

        except Exception as e:
            return await ctx.warn(f"Failed to set emoji: {str(e)}")

        return await ctx.approve(f"Updated the {button} button emoji to {emoji}")

    @voicemaster_emoji.command(
        name="remove",
        example="lock",
        aliases=["delete"]
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_emoji_remove(self, ctx: Context, button: str):
        """Remove a custom emoji for a VoiceMaster button"""
        valid_buttons = {
            "LOCK", "UNLOCK", "GHOST", "REVEAL", "CLAIM",
            "DISCONNECT", "ACTIVITY", "INFORMATION",
            "INCREASE", "DECREASE"
        }
        
        button = button.upper()
        if button not in valid_buttons:
            return await ctx.warn(
                f"Invalid button type. Valid options: {', '.join(valid_buttons)}"
            )

        await self.bot.db.execute(
            """
            UPDATE voicemaster.configuration 
            SET interface_emojis = interface_emojis - $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            button
        )

        return await ctx.approve(
            f"Reset {button} button to default emoji {getattr(config.EMOJIS.INTERFACE, button)}"
        )

    @voicemaster_emoji.command(name="reset")
    @has_permissions(manage_guild=True)
    async def voicemaster_emoji_reset(self, ctx: Context):
        """Reset all custom emojis to defaults"""
        await self.bot.db.execute(
            """
            UPDATE voicemaster.configuration 
            SET interface_emojis = '{}'::jsonb
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        return await ctx.approve("Reset all button emojis to defaults")

    @voicemaster_emoji.command(
        name="list",
        aliases=["show", "view"]
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_emoji_list(self, ctx: Context):
        """List all custom emojis for VoiceMaster buttons"""
        custom_emojis = await self.bot.db.fetchval(
            """
            SELECT interface_emojis
            FROM voicemaster.configuration
            WHERE guild_id = $1
            """,
            ctx.guild.id
        ) or {}

        embed = Embed(title="VoiceMaster Button Emojis")
        
        for button in ["LOCK", "UNLOCK", "GHOST", "REVEAL", "CLAIM",
                      "DISCONNECT", "ACTIVITY", "INFORMATION", 
                      "INCREASE", "DECREASE"]:
            embed.add_field(
                name=button,
                value=custom_emojis.get(button, getattr(config.EMOJIS.INTERFACE, button)),
                inline=True
            )

        return await ctx.send(embed=embed)

    @voicemaster.command(
        name="layout",
        example="dropdown",
        aliases=["style"]
    )
    @has_permissions(manage_guild=True)
    async def voicemaster_layout(self, ctx: Context, layout: str = None):
        """Change the interface layout style (default/dropdown)"""
        valid_layouts = ["default", "dropdown"]
        
        if not layout:
            current_layout = await self.bot.db.fetchval(
                """
                SELECT interface_layout 
                FROM voicemaster.configuration 
                WHERE guild_id = $1
                """,
                ctx.guild.id
            ) or "default"
            
            return await ctx.neutral(f"Current interface layout is set to: **{current_layout}**")

        layout = layout.lower()
        if layout not in valid_layouts:
            return await ctx.warn(
                f"Invalid layout type. Valid options: {', '.join(valid_layouts)}"
            )

        try:
            exists = await self.bot.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM voicemaster.configuration 
                    WHERE guild_id = $1
                )
                """,
                ctx.guild.id
            )

            if not exists:
                await self.bot.db.execute(
                    """
                    INSERT INTO voicemaster.configuration (guild_id, interface_layout)
                    VALUES ($1, $2)
                    """,
                    ctx.guild.id,
                    layout
                )
            else:
                await self.bot.db.execute(
                    """
                    UPDATE voicemaster.configuration 
                    SET interface_layout = $2
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id,
                    layout
                )

        except Exception as e:
            return await ctx.warn(f"Failed to set layout: {str(e)}")

        return await ctx.approve(f"Updated interface layout to **{layout}**")

    def _create_button_field(self, interface_emojis):
        field_value = ""
        for action, emoji in interface_emojis.items():
            emoji_display = emoji if emoji.startswith('<') and emoji.endswith('>') else emoji
            field_value += f"{emoji_display} — [`{action.title()}`](https://discord.gg/evict) "
            field_value += "the voice channel\n" if action not in ['DISCONNECT', 'ACTIVITY', 'INFORMATION', 'INCREASE', 'DECREASE'] else {
                'DISCONNECT': "a member\n",
                'ACTIVITY': "a new voice channel activity\n",
                'INFORMATION': "channel information\n",
                'INCREASE': "the user limit\n",
                'DECREASE': "the user limit\n"
            }[action]
        return field_value

    def _create_default_embed(self, guild, interface_emojis):
        embed = Embed(
            title="VoiceMaster Interface",
            description="Click the buttons below to control your voice channel",
        )
        embed.set_author(
            name=guild.name,
            icon_url=guild.icon,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        field_value = self._create_button_field(interface_emojis)
        embed.add_field(
            name="**Button Usage**",
            value=field_value
        )
        return embed
