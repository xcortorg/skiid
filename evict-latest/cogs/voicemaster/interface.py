import config
import logging
import json

from contextlib import suppress
import discord

from discord import (
    Embed,
    Guild,
    Interaction,
    InteractionResponded,
    InviteTarget,
    Member,
    Role,
    SelectOption,
    VoiceChannel,
    WebhookMessage,
    TextInput,
    TextStyle,
)
from discord.ui import Button, Select, View, button
from discord.utils import format_dt

from tools.converters.basic import activity_types
from main import Evict
from tools.utilities.text import Plural
from tools.conversion.embed import EmbedScript


class DisconnectMembers(Select):
    def __init__(self, member: Member):
        self.member: Member = member
        self.guild: Guild = member.guild
        self.channel: VoiceChannel = member.voice.channel
        super().__init__(
            placeholder="Choose members...",
            min_values=1,
            max_values=len(self.channel.members),
            options=[
                SelectOption(
                    value=member.id,
                    label=f"{member} ({member.id})",
                    emoji="👤",
                )
                for member in self.channel.members
            ],
        )

    async def callback(
            self, 
            interaction: Interaction
            ) -> WebhookMessage:
        await interaction.response.defer()

        disconnected, failed = 0, 0

        for member_id in self.values:
            if member := self.guild.get_member(int(member_id)):
                if member == self.member:
                    failed += 1
                elif not member.voice or member.voice.channel != self.channel:
                    failed += 1
                else:
                    try:
                        await member.move_to(None)
                    except:  # noqa
                        failed += 1
                    else:
                        disconnected += 1

        return await interaction.approve(
            f"Successfully **disconnected** {Plural(disconnected, code=True):member} (`{failed}` failed)"
        )


class ActivitySelection(Select):
    def __init__(self, member: Member):
        self.member: Member = member
        self.guild: Guild = member.guild
        self.channel: VoiceChannel = member.voice.channel
        super().__init__(
            placeholder="Choose an activity...",
            min_values=1,
            max_values=1,
            options=[
                SelectOption(
                    value=activity["id"],
                    label=activity["name"],
                    emoji=activity["emoji"],
                )
                for activity in activity_types
            ],
        )

    async def callback(
            self, 
            interaction: Interaction
            ) -> WebhookMessage:
        await interaction.response.defer()

        try:
            invite = await self.channel.create_invite(
                max_age=0,
                target_type=InviteTarget.embedded_application,
                target_application_id=int(self.values[0]),
                reason=f"VoiceMaster: {self.member} started an activity",
            )
        except Exception:
            return await interaction.warn(
                "Failed to create an **invite** for the selected **activity**!"
            )

        return await interaction.followup.send(
            f"[Click here to join the activity!]({invite})",
            ephemeral=True,
        )


class VoicemasterDropdown(Select):
    def __init__(self, interface: 'Interface'):
        self.interface = interface
        super().__init__(
            placeholder="select task...",
            min_values=1,
            max_values=1,
            options=[]  
        )
        
    async def setup_options(self, guild_id: int):
        """Setup dropdown options with proper emojis"""
        custom_emojis = await self.interface.get_custom_emojis(guild_id)
        
        options = [
            ("LOCK", "Lock", "the voice channel"),
            ("UNLOCK", "Unlock", "the voice channel"),
            ("GHOST", "Hide", "the voice channel"),
            ("REVEAL", "Reveal", "the voice channel"),
            ("CLAIM", "Claim", "the voice channel"),
            ("DISCONNECT", "Disconnect", "a member"),
            ("ACTIVITY", "Start", "a new voice channel activity"),
            ("INFORMATION", "View", "channel information"),
            ("INCREASE", "Increase", "the user limit"),
            ("DECREASE", "Decrease", "the user limit")
        ]
        
        for button_type, label, description in options:
            emoji = custom_emojis.get(button_type, getattr(config.EMOJIS.INTERFACE, button_type))
            
            if isinstance(emoji, str) and emoji.startswith('<') and emoji.endswith('>'):
                try:
                    emoji_id = int(emoji.split(':')[-1][:-1])
                    emoji_name = emoji.split(':')[1]
                    emoji = discord.PartialEmoji(name=emoji_name, id=emoji_id, animated=False)
                except (ValueError, IndexError):
                    emoji = getattr(config.EMOJIS.INTERFACE, button_type)
            
            self.options.append(
                SelectOption(
                    label=f"{label} {description}",
                    value=button_type.lower(),
                    emoji=emoji
                )
            )

    async def callback(self, interaction: Interaction):
        
        if not await self.interface.interaction_check(interaction):
            return
            
        action = self.values[0].lower()  
        
        method = getattr(self.interface.__class__, action)
        await method(self.interface, interaction, None)
            
        new_dropdown = VoicemasterDropdown(self.interface)
        await new_dropdown.setup_options(interaction.guild_id)
        new_view = View(timeout=None)
        new_view.add_item(new_dropdown)
        
        await interaction.message.edit(view=new_view)


class Interface(View):
    def __init__(self, bot: Evict):
        self.bot: Evict = bot
        super().__init__(timeout=None)

    async def get_layout(self, guild_id: int) -> str:
        """
        Get interface layout preference.
        """
        try:
            layout = await self.bot.db.fetchval(
                """
                SELECT interface_layout 
                FROM voicemaster.configuration 
                WHERE guild_id = $1
                """,
                guild_id
            ) or 'default'
            return layout
        except Exception as e:
            return 'default'

    def create_dropdown_embed(self, guild):
        """Create the dropdown style interface embed"""
        embed = Embed(
            title="Voicemaster Control Menu",
            description="control your voice channe using the dropdown below",
            color=0x2B2D31 
        )
        embed.set_author(
            name=guild.name,
            icon_url=guild.icon
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        return embed

    async def send(self, **kwargs) -> discord.Message:
        """
        Send the interface and store the message.
        """
        if not hasattr(self, 'channel'):
            raise ValueError("Channel not created. Call create_channel() first")

        layout = await self.get_layout(self.channel.guild.id)
        custom_emojis = await self.get_custom_emojis(self.channel.guild.id)
        
        print(f"[Interface] Received embed: {kwargs.get('embed').to_dict() if 'embed' in kwargs else None}")
        print(f"[Interface] Custom emojis: {custom_emojis}")
        
        if 'embed' in kwargs and kwargs['embed'].description:
            emoji_map = {
                'lock': custom_emojis.get('LOCK', getattr(config.EMOJIS.INTERFACE, 'LOCK')),
                'unlock': custom_emojis.get('UNLOCK', getattr(config.EMOJIS.INTERFACE, 'UNLOCK')),
                'ghost': custom_emojis.get('GHOST', getattr(config.EMOJIS.INTERFACE, 'GHOST')),
                'reveal': custom_emojis.get('REVEAL', getattr(config.EMOJIS.INTERFACE, 'REVEAL')),
                'claim': custom_emojis.get('CLAIM', getattr(config.EMOJIS.INTERFACE, 'CLAIM')),
                'disconnect': custom_emojis.get('DISCONNECT', getattr(config.EMOJIS.INTERFACE, 'DISCONNECT')),
                'activity': custom_emojis.get('ACTIVITY', getattr(config.EMOJIS.INTERFACE, 'ACTIVITY')),
                'information': custom_emojis.get('INFORMATION', getattr(config.EMOJIS.INTERFACE, 'INFORMATION')),
                'increase': custom_emojis.get('INCREASE', getattr(config.EMOJIS.INTERFACE, 'INCREASE')),
                'decrease': custom_emojis.get('DECREASE', getattr(config.EMOJIS.INTERFACE, 'DECREASE'))
            }
            
            description = kwargs['embed'].description
            print(f"[Interface] Original description: {description}")
            
            import re
            for key, emoji in emoji_map.items():
                pattern = r'\{' + re.escape(key) + r'\}?'
                description = re.sub(pattern, str(emoji), description)
                print(f"[Interface] After replacing {key}: {description}")
                
            kwargs['embed'].description = description
            print(f"[Interface] Final description: {kwargs['embed'].description}")
        
        if layout == 'dropdown':
            if 'embed' not in kwargs:
                kwargs['embed'] = self.create_dropdown_embed(self.channel.guild)
            
            dropdown = VoicemasterDropdown(self)
            await dropdown.setup_options(self.channel.guild.id)
            
            view = View(timeout=None)
            view.add_item(dropdown)
            kwargs['view'] = view
        else:
            kwargs['view'] = self
        
        self.message = await self.channel.send(**kwargs)
        return self.message

    async def get_custom_emojis(self, guild_id: int) -> dict:
        """Get custom emojis from database"""
        try:
            custom_emojis = json.loads(await self.bot.db.fetchval(
                """
                SELECT interface_emojis 
                FROM voicemaster.configuration 
                WHERE guild_id = $1
                """,
                guild_id
            ) or '{}')
            return custom_emojis
        except Exception as e:
            return {}

    async def setup_buttons(self, guild_id: int):
        """Setup button emojis with custom ones where available"""
        custom_emojis = await self.get_custom_emojis(guild_id)
        
        for child in self.children:
            if isinstance(child, Button):
                button_type = child.custom_id.split(":")[1].upper()
                emoji = custom_emojis.get(button_type, getattr(config.EMOJIS.INTERFACE, button_type))
                
                if isinstance(emoji, str) and emoji.startswith('<') and emoji.endswith('>'):
                    try:
                        emoji_id = int(emoji.split(':')[-1][:-1])
                        emoji_name = emoji.split(':')[1]
                        child.emoji = discord.PartialEmoji(name=emoji_name, id=emoji_id, animated=False)
                    except (ValueError, IndexError):
                        child.emoji = getattr(config.EMOJIS.INTERFACE, button_type)
                else:
                    child.emoji = emoji

    async def create_channel(self, category, author):
        """Create the interface channel"""
        self.channel = await category.create_text_channel(
            "interface", 
            reason=f"{author} setup VoiceMaster"
        )
        return self.channel

    def create_embed(self, guild):
        """Create the interface embed"""
        embed = Embed(
            title="VoiceMaster Interface",
            description="Click the buttons below to control your voice channel",
        )
        embed.set_author(
            name=guild.name,
            icon_url=guild.icon,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.add_field(
            name="**Button Usage**",
            value=(
                f"{config.EMOJIS.INTERFACE.LOCK} — [`Lock`](https://discord.gg/evict) the voice channel\n"
                f"{config.EMOJIS.INTERFACE.UNLOCK} — [`Unlock`](https://discord.gg/evict) the voice channel\n"
                f"{config.EMOJIS.INTERFACE.GHOST} — [`Ghost`](https://discord.gg/evict) the voice channel\n"
                f"{config.EMOJIS.INTERFACE.REVEAL} — [`Reveal`](https://discord.gg/evict) the voice channel\n"
                f"{config.EMOJIS.INTERFACE.CLAIM} — [`Claim`](https://discord.gg/evict) the voice channel\n"
                f"{config.EMOJIS.INTERFACE.DISCONNECT} — [`Disconnect`](https://discord.gg/evict) a member\n"
                f"{config.EMOJIS.INTERFACE.ACTIVITY} — [`Start`](https://discord.gg/evict) a new voice channel activity\n"
                f"{config.EMOJIS.INTERFACE.INFORMATION} — [`View`](https://discord.gg/evict) channel information\n"
                f"{config.EMOJIS.INTERFACE.INCREASE} — [`Increase`](https://discord.gg/evict) the user limit\n"
                f"{config.EMOJIS.INTERFACE.DECREASE} — [`Decrease`](https://discord.gg/evict) the user limit\n"
            ),
        )
        return embed

    async def set_permissions(self, default_role: discord.Role, author: discord.Member):
        """Set default permissions for the interface channel"""
        if hasattr(self, 'channel'):
            await self.channel.set_permissions(
                default_role,
                send_messages=False,
                add_reactions=False,
                reason=f"{author} setup VoiceMaster"
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Check if the user can use the interface"""
        try:
            custom_emojis = await self.get_custom_emojis(interaction.guild_id)
            
            for child in self.children:
                if isinstance(child, Button):
                    button_type = child.custom_id.split(":")[1].upper()
                    emoji = custom_emojis.get(button_type, getattr(config.EMOJIS.INTERFACE, button_type))
                    
                    if isinstance(emoji, str) and emoji.startswith('<') and emoji.endswith('>'):
                        try:
                            emoji_id = int(emoji.split(':')[-1][:-1])
                            emoji_name = emoji.split(':')[1]
                            child.emoji = discord.PartialEmoji(name=emoji_name, id=emoji_id, animated=False)
                        except (ValueError, IndexError):
                            child.emoji = getattr(config.EMOJIS.INTERFACE, button_type)
                    else:
                        child.emoji = emoji
                    
        except Exception as e:
            return False

        if not interaction.user.voice:
            await interaction.warn("You're not connected to a **voice channel**")
            return False

        if not (
            owner_id := await self.bot.db.fetchval(
                """
            SELECT owner_id FROM voicemaster.channels
            WHERE channel_id = $1
            """,
                interaction.user.voice.channel.id,
            )
        ):
            await interaction.warn("You're not in a **VoiceMaster** channel!")
            return False

        if interaction.data["custom_id"] == "voicemaster:claim":
            if interaction.user.id == owner_id:
                await interaction.warn(
                    "You already have **ownership** of this voice channel!"
                )
                return False

            if owner_id in (
                member.id for member in interaction.user.voice.channel.members
            ):
                await interaction.warn(
                    "You can't claim this **voice channel**, the owner is still active here."
                )
                return False

            return True

        if interaction.user.id != owner_id:
            await interaction.warn("You don't own a **voice channel**!")
            return False

        return True

    @button(
        custom_id="voicemaster:lock",
    )
    async def lock(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """Lock your voice channel"""
        await interaction.user.voice.channel.set_permissions(
            interaction.guild.default_role,
            connect=False,
            reason=f"VoiceMaster: {interaction.user} locked voice channel",
        )
        return await interaction.warn("Your **voice channel** has been locked", emoji=":lock:")

    @button(
        custom_id="voicemaster:unlock",
    )
    async def unlock(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """Unlock your voice channel"""
        await interaction.user.voice.channel.set_permissions(
            interaction.guild.default_role,
            connect=None,
            reason=f"VoiceMaster: {interaction.user} unlocked voice channel",
        )
        return await interaction.warn("Your **voice channel** has been unlocked", emoji=":unlock:")

    @button(
        custom_id="voicemaster:ghost",

    )
    async def ghost(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """Hide your voice channel"""
        await interaction.user.voice.channel.set_permissions(
            interaction.guild.default_role,
            view_channel=False,
            reason=f"VoiceMaster: {interaction.user} made voice channel hidden",
        )
        return await interaction.approve("Your **voice channel** has been hidden")

    @button(
        custom_id="voicemaster:reveal",
    )
    async def reveal(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """Reveal your voice channel"""
        await interaction.user.voice.channel.set_permissions(
            interaction.guild.default_role,
            view_channel=None,
            reason=f"VoiceMaster: {interaction.user} revealed voice channel",
        )
        return await interaction.approve("Your **voice channel** has been revealed")

    @button(
        custom_id="voicemaster:claim",
    )
    async def claim(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """Claim an inactive voice channel"""
        await self.bot.db.execute(
            """
            UPDATE voicemaster.channels
            SET owner_id = $2
            WHERE channel_id = $1
            """,
            interaction.user.voice.channel.id,
            interaction.user.id,
        )
        if interaction.user.voice.channel.name.endswith("channel"):
            try:
                await interaction.user.voice.channel.edit(
                    name=f"{interaction.user.display_name}'s channel"
                )
            except Exception:
                pass
        return await interaction.approve("You are now the owner of this **channel**!")

    @button(
        custom_id="voicemaster:disconnect",
    )
    async def disconnect(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """Reject a member or role from joining your VC"""
        view = View(timeout=None)
        view.add_item(DisconnectMembers(interaction.user))
        return await interaction.neutral(
            "Select members from the **dropdown** to disconnect.",
            emoji="🔨",
            view=view,
        )

    @button(
        custom_id="voicemaster:activity",
    )
    async def activity(self, interaction: Interaction, button: Button):
        """Start an activity in your voice channel"""
        view = View(timeout=None)
        view.add_item(ActivitySelection(interaction.user))
        return await interaction.neutral(
            "Select an activity from the **dropdown** to start!",
            emoji=config.EMOJIS.INTERFACE.ACTIVITY,
            view=view,
        )

    @button(
        custom_id="voicemaster:information",
    )
    async def information(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """See current configuration for current voice channel"""
        with suppress(InteractionResponded):
            await interaction.response.defer(ephemeral=True)
        channel = interaction.user.voice.channel
        embed = Embed(
            title=channel.name,
            description=(
                f"**Owner:** {interaction.user} (`{interaction.user.id}`)"
                + "\n**Locked:** "
                + (
                    config.EMOJIS.CONTEXT.APPROVE
                    if channel.permissions_for(interaction.guild.default_role).connect is False
                    else config.EMOJIS.CONTEXT.DENY
                )
                + "\n**Created:** "
                + format_dt(channel.created_at, style="R")
                + f"\n**Bitrate:** {int(channel.bitrate / 1000)}kbps"
                + f"\n**Connected:** `{len(channel.members)}`"
                + (f"/`{channel.user_limit}`" if channel.user_limit else "")
            ),
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
        if roles_permitted := [
            target for target, overwrite in channel.overwrites.items()
            if overwrite.connect is True and isinstance(target, Role)
        ]:
            embed.add_field(
                name="**Role Permitted**",
                value=", ".join(role.mention for role in roles_permitted),
                inline=False,
            )
        if members_permitted := [
            target for target, overwrite in channel.overwrites.items()
            if overwrite.connect is True and isinstance(target, Member)
            and target != interaction.user
        ]:
            embed.add_field(
                name="**Member Permitted**",
                value=", ".join(member.mention for member in members_permitted),
                inline=False,
            )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    @button(
        custom_id="voicemaster:increase",
    )
    async def increase(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """Increase the user limit of your voice channel"""
        limit = interaction.user.voice.channel.user_limit or 0
        if limit == 99:
            return await interaction.warn("Channel member limit cannot be more than **99 members**!")
        await interaction.user.voice.channel.edit(
            user_limit=limit + 1,
            reason=f"VoiceMaster: {interaction.user} increased voice channel user limit",
        )
        return await interaction.approve(f"Your **voice channel**'s limit has been updated to `{limit + 1}`")

    @button(
        custom_id="voicemaster:decrease",
    )
    async def decrease(self, interaction: Interaction, button: Button) -> WebhookMessage:
        """Decrease the user limit of your voice channel"""
        limit = interaction.user.voice.channel.user_limit or 0
        if limit == 0:
            return await interaction.warn("Channel member limit must be greater than **0 members**")
        await interaction.user.voice.channel.edit(
            user_limit=limit - 1,
            reason=f"VoiceMaster: {interaction.user} decreased voice channel user limit",
        )
        return await interaction.approve(
            "Your **voice channel**'s limit has been **removed**"
            if (limit - 1) == 0
            else f"Your **voice channel**'s limit has been updated to `{limit - 1}`"
        )

    async def get_custom_embed(self, guild_id: int) -> str:
        """Get custom embed code from database"""
        try:
            embed_code = await self.bot.db.fetchval(
                """
                SELECT interface_embed 
                FROM voicemaster.configuration 
                WHERE guild_id = $1
                """,
                guild_id
            )
            return embed_code
        except Exception:
            return None

    def create_default_embed(self, guild):
        """Create the default interface embed"""
        embed = Embed(
            title="VoiceMaster Interface",
            description="Click the buttons below to control your voice channel",
        )
        embed.set_author(
            name=guild.name,
            icon_url=guild.icon,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        return embed
