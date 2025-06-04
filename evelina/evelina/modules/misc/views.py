import re
import io
import json
import discord
import aiohttp
import datetime

from io import BytesIO
from typing import Union

from discord import Interaction, Embed, ButtonStyle, Button, Member, TextStyle, PartialEmoji, Sticker, HTTPException, File, Emoji, utils, Message
from discord.ui import View, button, Modal, TextInput
from discord.ext.commands import Context
from discord.errors import Forbidden, NotFound

from modules.styles import emojis, colors

class confessModal(Modal, title="confess here"):
    name = TextInput(label="confession", placeholder="the confession is anonymous", style=TextStyle.long, required=True)

    async def on_submit(self, interaction: Interaction) -> None:
        check = await interaction.client.db.fetchrow("SELECT * FROM confess WHERE guild_id = $1", interaction.guild.id)
        if check:
            if re.search(r"[(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)", self.name.value):
                return await interaction.warn("You cannot use links in a confession", ephemeral=True)
            channel = interaction.guild.get_channel(check["channel_id"])
            if not channel:
                return await interaction.warn("Confession channel is **invalid**", ephemeral=True)
            count = check["confession"] + 1
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Sent your confession in {channel.mention}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            e = Embed(color=colors.NEUTRAL, description=f"{self.name.value}", title=f"Anonymous Confession (#{count})", timestamp=datetime.datetime.now())
            await channel.send(embed=e)
            await interaction.client.db.execute("UPDATE confess SET confession = $1 WHERE guild_id = $2", count, interaction.guild.id)
            await interaction.client.db.execute("INSERT INTO confess_members VALUES ($1,$2,$3)", interaction.guild.id, interaction.user.id, count)
    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't send your confession - {error}")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

class BoosterMod(View):
    def __init__(self, ctx: Context, member: Member, reason: str):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.member = member
        self.reason = reason
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            return False
        if not self.ctx.guild.get_member(self.member.id):
            await interaction.warn("Member not found", ephemeral=True)
            return False
        return True
    @button(label="Approve", style=ButtonStyle.green)
    async def yes_button(self, interaction: Interaction, button: Button):
        if self.ctx.command.name == "ban":
            await self.member.ban(reason=self.reason)
            await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} **{interaction.user.mention}**: Banned {self.member.mention} - {self.reason}"), view=None)
            current_timestamp = utils.utcnow().timestamp()
            await interaction.client.db.execute("INSERT INTO history (id, guild_id, user_id, moderator_id, server_id, punishment, duration, reason, time) VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM history), (SELECT COALESCE(MAX(guild_id), 0) + 1 FROM history WHERE server_id = $1), $2, $3, $4, $5, $6, $7, $8)", interaction.guild.id, self.member.id, interaction.user.id, interaction.guild.id, "Ban [Booster]", 'None', self.reason, current_timestamp)
        else:
            await self.member.kick(reason=self.reason)
            await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE}  **{interaction.user.mention}**: Kicked {self.member.mention} - {self.reason}"), view=None)
            current_timestamp = utils.utcnow().timestamp()
            await interaction.client.db.execute("INSERT INTO history (id, guild_id, user_id, moderator_id, server_id, punishment, duration, reason, time) VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM history), (SELECT COALESCE(MAX(guild_id), 0) + 1 FROM history WHERE server_id = $1), $2, $3, $4, $5, $6, $7, $8)", interaction.guild.id, self.member.id, interaction.user.id, interaction.guild.id, "Kick [Booster]", 'None', self.reason, current_timestamp)
    @button(label="Decline", style=ButtonStyle.red)
    async def no_button(self, interaction: Interaction, button: Button):
        if self.ctx.author.id != interaction.user.id:
            await interaction.warn("You are not the **author** of this embed", ephemeral=True)
        await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Booster ban/kick got canceled"), view=None)

class MarryView(View):
    def __init__(self, ctx: Context, member: Member):
        super().__init__()
        self.ctx = ctx
        self.member = member
        self.status = False
        self.wedding = "💒"
        self.marry_color = 0xFF819F
        self.message = None
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user == self.ctx.author:
            await interaction.warn("You can't interact with your own marriage", ephemeral=True)
            return False
        elif interaction.user != self.member:
            await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            return False
        return True
    @button(label="Approve", style=ButtonStyle.success)
    async def yes(self, interaction: Interaction, button: Button):
        author_row = await interaction.client.db.fetchrow("SELECT * FROM marry WHERE $1 IN (author, soulmate)", self.ctx.author.id)
        if author_row:
            await interaction.warn(f"{self.ctx.author.mention} **already** accepted a marriage", ephemeral=True)
            return
        user_row = await interaction.client.db.fetchrow("SELECT * FROM marry WHERE $1 IN (author, soulmate)", interaction.user.id)
        if user_row:
            await interaction.warn("You **already** accepted a marriage", ephemeral=True)
            return
        await interaction.client.db.execute("INSERT INTO marry VALUES ($1,$2,$3)", self.ctx.author.id, self.member.id, datetime.datetime.now().timestamp())
        await interaction.response.edit_message(content=None, embed=Embed(color=self.marry_color, description=f"{self.wedding} {self.ctx.author.mention}: Successfully married with {self.member.mention}"), view=None)
        self.status = True
    @button(label="Decline", style=ButtonStyle.danger)
    async def no(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(content=None, embed=Embed(color=self.marry_color, description=f"{self.wedding} {self.ctx.author.mention}: I'm sorry, but {self.member.mention} is probably not the right person for you"), view=None)
        self.status = True
    async def on_timeout(self):
        if not self.status:
            if self.message:
                await self.message.edit(content=None, embed=Embed(color=self.marry_color, description=f"{self.wedding} {self.ctx.author.mention}: {self.member.mention} didn't reply in time :("), view=None)

class ShareRoleView(View):
    def __init__(self, ctx: Context, user: Member):
        super().__init__()
        self.ctx = ctx
        self.user = user
        self.status = False
        self.message = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user == self.ctx.author:
            await interaction.warn("You can't interact with your own request", ephemeral=True)
            return False
        elif interaction.user != self.user:
            await interaction.warn("You are not the **recipient** of this request", ephemeral=True)
            return False
        return True

    @button(label="Approve", style=ButtonStyle.success)
    async def approve(self, interaction: Interaction, button: Button):
        data = await self.ctx.bot.db.fetchrow(
            "SELECT role_id, shared_users FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            self.ctx.guild.id, self.ctx.author.id
        )
        if not data:
            return await interaction.warn("No shared booster role found", ephemeral=True)
        role_data = data['role_id']
        shared_users = json.loads(data['shared_users']) if isinstance(data['shared_users'], str) else data['shared_users']
        if interaction.user.id in shared_users:
            return await interaction.warn(f"You are already sharing the booster role with {interaction.user.mention}", ephemeral=True)
        shared_users.append(interaction.user.id)
        await self.ctx.bot.db.execute(
            "UPDATE booster_roles SET shared_users = $1 WHERE guild_id = $2 AND user_id = $3",
            json.dumps(shared_users), self.ctx.guild.id, self.ctx.author.id
        )
        booster_role = self.ctx.guild.get_role(role_data)
        try:
            await interaction.user.add_roles(booster_role)
        except Forbidden:
            return await interaction.warn("I don't have permission to give the booster role to this user", ephemeral=True)
        except NotFound:
            return await interaction.warn("I couldn't find the booster role", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {self.ctx.author.mention} and {interaction.user.mention} are now sharing the booster role!"), view=None)
        self.status = True

    @button(label="Decline", style=ButtonStyle.danger)
    async def decline(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(content=None, embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {self.ctx.author.mention} and {interaction.user.mention} will **not** share the booster role."), view=None)
        self.status = True

    async def on_timeout(self):
        if not self.status:
            if self.message:
                await self.message.edit(content=None, embed=Embed(color=colors.ERROR, description=f"{self.ctx.author.mention}: {self.user.mention} didn't respond in time :("), view=None)

class DownloadAsset(View):
    def __init__(self: "DownloadAsset", ctx: Context, asset: Union[PartialEmoji, Emoji, Sticker]): super().__init__(); self.ctx, self.asset, self.pressed = ctx, asset, False
    async def interaction_check(self, interaction: Interaction) -> bool: return await interaction.warn("You are not the **author** of this embed", ephemeral=True) if interaction.user.id != self.ctx.author.id else await interaction.warn("You don't have permissions to add emojis/stickers in this server", ephemeral=True) if not interaction.user.guild_permissions.manage_expressions else await interaction.warn("The bot doesn't have permissions to add emojis/stickers in this server", ephemeral=True) if not interaction.user.guild.me.guild_permissions.manage_expressions else True
    @button(label="Download", style=ButtonStyle.gray)
    async def download_asset(self: "DownloadAsset", interaction: Interaction, button: Button):
        self.pressed = True
        embed = None
        e = None
        sticker = None
        file = None
        if isinstance(self.asset, (PartialEmoji, Emoji)):
            try:
                e = await interaction.guild.create_custom_emoji(name=self.asset.name, image=await self.asset.read(), reason=f"Emoji added by {interaction.user}")
                embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Added {e} as [**{e.name}**]({e.url})")
            except HTTPException:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Unable to add emoji")
            finally:
                await interaction.response.edit_message(embed=embed, view=None, attachments=[])
        else:
            try:
                file = File(BytesIO(await self.asset.read()))
                sticker = await interaction.guild.create_sticker(name=self.asset.name, description=self.asset.name, emoji="💀", file=file, reason=f"Sticker created by {interaction.user}")
                embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Added sticker as [**{sticker.name}**]({sticker.url})")
            except HTTPException:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Unable to add sticker")
            finally:
                await interaction.response.edit_message(embed=embed, view=None, attachments=[])

class ConfirmView(View):
    def __init__(self, author_id: int, yes_func, no_func):
        self.author_id = author_id
        self.yes_func = yes_func
        self.no_func = no_func
        super().__init__()

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            return False
        return True
    
    @button(label="Approve", style=ButtonStyle.green)
    async def yes_button(self, interaction: Interaction, button: Button):
        await self.yes_func(interaction)

    @button(label="Decline", style=ButtonStyle.red)
    async def no_button(self, interaction: Interaction, button: Button):
        await self.no_func(interaction)

class InputModal(Modal):
    def __init__(self, title: str, fields: list[tuple[str, str]], callback_func):
        super().__init__(title=title)
        self.callback_func = callback_func
        self.inputs = []

        for label, placeholder in fields:
            input_field = TextInput(label=label, placeholder=placeholder, style=TextStyle.paragraph, required=True)
            self.inputs.append(input_field)
            self.add_item(input_field)

    async def on_submit(self, interaction: Interaction):
        values = [field.value for field in self.inputs]
        await self.callback_func(interaction, values)

class ModalButtonView(View):
    def __init__(self, author_id: int, button_label: str, modal_title: str, fields: list[tuple[str, str]], callback_func):
        super().__init__()
        self.author_id = author_id
        self.button_label = button_label
        self.modal_title = modal_title
        self.fields = fields
        self.callback_func = callback_func
        self.open_modal_button.label = self.button_label

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            await interaction.warn("You are not the **author** of this message", ephemeral=True)
            return False
        return True

    @button(label="...", style=ButtonStyle.blurple)
    async def open_modal_button(self, interaction: Interaction, button: Button):
        modal = InputModal(self.modal_title, self.fields, self.callback_func)
        await interaction.response.send_modal(modal)

class TargetConfirmView(View):
    def __init__(self, author_id: int, user_id: int, yes_func, no_func):
        self.author_id = author_id
        self.user_id = user_id
        self.yes_func = yes_func
        self.no_func = no_func
        super().__init__()

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.user_id and interaction.user.id != self.author_id:
            await interaction.warn(f"Only <@{self.user_id}> or <@{self.author_id}> can use these buttons", ephemeral=True)
            return False
        return True

    @button(label="Approve", style=ButtonStyle.green)
    async def yes_button(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.warn(f"Only <@{self.user_id}> can approve", ephemeral=True)
            return
        await self.yes_func(interaction)

    @button(label="Decline", style=ButtonStyle.red)
    async def no_button(self, interaction: Interaction, button: Button):
        await self.no_func(interaction)

class ChooseView(View):
    def __init__(self, author_id: int, button_func, select_func):
        self.author_id = author_id
        self.button_func = button_func
        self.select_func = select_func
        super().__init__()

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            return False
        return True

    @button(label="Button", style=ButtonStyle.green)
    async def button_button(self, interaction: Interaction, button: Button):
        await self.button_func(interaction)

    @button(label="Select", style=ButtonStyle.red)
    async def select_button(self, interaction: Interaction, button: Button):
        await self.select_func(interaction)

class GunsInfoView(discord.ui.View):
    def __init__(self, bot, data):
        super().__init__(timeout=None)
        self.data = data
        self.bot = bot
               
    @discord.ui.button(label="Customize", style=discord.ButtonStyle.secondary)
    async def customize(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await self.bot.get_context(interaction.message)
        description = self.data["config"].get("description", emojis.DENY)
        profile_opacity = self.data["config"].get("opacity", emojis.DENY)
        profile_blur = self.data["config"].get("blur", emojis.DENY)
        background_effects = self.data["config"].get("background_effects", emojis.DENY)
        if background_effects == "night":
            background_effects = "Night Time"
        elif background_effects == "blured":
            background_effects = "Blured Background"
        elif background_effects == "tv":
            background_effects = "Old TV"
        elif background_effects == "none":
            background_effects = emojis.DENY
        username_effects = self.data["config"].get("username_effects", emojis.DENY)
        if username_effects == "none":
            username_effects = emojis.DENY
        swap_colors = self.data["config"].get("swap_colors", emojis.DENY)
        if swap_colors == True:
            swap_colors = emojis.APPROVE
        elif swap_colors == False:
            swap_colors = emojis.DENY
        social_glow = self.data["config"].get("social_glow", emojis.DENY)
        if social_glow == True:
            social_glow = emojis.APPROVE
        elif social_glow == False:
            social_glow = emojis.DENY
        username_glow = self.data["config"].get("username_glow", emojis.DENY)
        if username_glow == True:
            username_glow = emojis.APPROVE
        elif username_glow == False:
            username_glow = emojis.DENY
        badge_glow = self.data["config"].get("badge_glow", emojis.DENY)
        if badge_glow == True:
            badge_glow = emojis.APPROVE
        elif badge_glow == False:
            badge_glow = emojis.DENY

        color = self.data["config"].get("color", emojis.DENY)
        text_color = self.data["config"].get("text_color", emojis.DENY)
        bg_color = self.data["config"].get("bg_color", emojis.DENY)
        icon_color = self.data["config"].get("icon_color", emojis.DENY)
        profile_gradient = self.data["config"].get("profile_gradient", emojis.DENY)
        if profile_gradient == True:
            profile_gradient = emojis.APPROVE
        elif profile_gradient == False:
            profile_gradient = emojis.DENY
        gradient_1 = self.data["config"].get("gradient_1", emojis.DENY)
        gradient_2 = self.data["config"].get("gradient_2", emojis.DENY)

        monochrome = self.data["config"].get("monochrome", emojis.DENY)
        if monochrome == True:
            monochrome = emojis.APPROVE
        elif monochrome == False:
            monochrome = emojis.DENY
        animated_title = self.data["config"].get("animated_title", emojis.DENY)
        if animated_title == True:
            animated_title = emojis.APPROVE
        elif animated_title == False:
            animated_title = emojis.DENY
        volume_control = self.data["config"].get("volume_control", emojis.DENY)
        if volume_control == True:
            volume_control = emojis.APPROVE
        elif volume_control == False:
            volume_control = emojis.DENY
        use_discord_avatar = self.data["config"].get("use_discord_avatar", emojis.DENY)
        if use_discord_avatar == True:
            use_discord_avatar = emojis.APPROVE
        elif use_discord_avatar == False:
            use_discord_avatar = emojis.DENY
        
        embed_general = discord.Embed(title="Customize Profile", color=colors.NEUTRAL)
        embed_general.description = "> [General Customization](https://guns.lol/customize)"
        embed_general.add_field(name="Description", value=description, inline=True)
        embed_general.add_field(name="Profile Opacity", value=f"{profile_opacity}%", inline=True)
        embed_general.add_field(name="Profile Blur", value=f"{profile_blur}%", inline=True)
        embed_general.add_field(name="Background Effects", value=str(background_effects).capitalize(), inline=True)
        embed_general.add_field(name="Username Effects", value=str(username_effects).capitalize(), inline=True)
        embed_general.add_field(name="Swap Colors", value=swap_colors, inline=True)
        embed_general.add_field(name="Social Glow", value=social_glow, inline=True)
        embed_general.add_field(name="Username Glow", value=username_glow, inline=True)
        embed_general.add_field(name="Badge Glow", value=badge_glow, inline=True)
        embed_general.set_footer(text="Page 1/3 (3 entries)")
        embed_color = discord.Embed(title="Customize Profile", color=colors.NEUTRAL)
        embed_color.description = "> [Color Customization](https://guns.lol/customize)"
        embed_color.add_field(name="Color", value=color, inline=True)
        embed_color.add_field(name="Text Color", value=text_color, inline=True)
        embed_color.add_field(name="Background Color", value=bg_color, inline=True)
        embed_color.add_field(name="Icon Color", value=icon_color, inline=True)
        embed_color.add_field(name="\u200b", value="\u200b", inline=True)
        embed_color.add_field(name="\u200b", value="\u200b", inline=True)
        embed_color.add_field(name="Profile Gradient", value=profile_gradient, inline=True)
        embed_color.add_field(name="Gradient 1", value=gradient_1, inline=True)
        embed_color.add_field(name="Gradient 2", value=gradient_2, inline=True)
        embed_color.set_footer(text="Page 2/3 (3 entries)")
        embed_other = discord.Embed(title="Customize Profile", color=colors.NEUTRAL)
        embed_other.description = "> [Other Customization](https://guns.lol/customize)"
        embed_other.add_field(name="Monochrome", value=monochrome, inline=True)
        embed_other.add_field(name="Animated Title", value=animated_title, inline=True)
        embed_other.add_field(name="Volume Control", value=volume_control, inline=True)
        embed_other.add_field(name="Use Discord Avatar", value=use_discord_avatar, inline=True)
        embed_other.set_footer(text="Page 3/3 (3 entry)")
        await ctx.paginator(embeds=[embed_general, embed_color, embed_other], author_only=False, interaction=interaction, ephemeral=True)

    @discord.ui.button(label="Premium", style=discord.ButtonStyle.secondary)
    async def premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await self.bot.get_context(interaction.message)
        is_premium = self.data.get("premium", False)
        if is_premium == False:
            return await interaction.response.send_message(embed=discord.Embed(description=f"{emojis.WARNING} {interaction.user.mention}: User has no premium, so you can't view his settings", color=colors.WARNING), ephemeral=True)
        layout = self.data['config']['premium'].get("layout", emojis.DENY)
        animation = self.data['config']['premium'].get("animation", emojis.DENY)

        cursor_effects = self.data['config']['premium'].get("cursor_effects", emojis.DENY)
        if cursor_effects == "none":
            cursor_effects = emojis.DENY
        effects_color = self.data['config']['premium'].get("effects_color", emojis.DENY)
        font = self.data['config']['premium'].get("font", emojis.DENY)
        page_enter_text = self.data['config']['premium'].get("page_enter_text", emojis.DENY)

        typewriter_enabled = self.data['config']['premium'].get("typewriter_enabled", emojis.DENY)
        if typewriter_enabled == True:
            typewriter_enabled = emojis.APPROVE
        elif typewriter_enabled == False:
            typewriter_enabled = emojis.DENY
        typewriter_texts = self.data['config']['premium'].get("typewriter", [])
        if not typewriter_texts:
            typewriter_texts = [emojis.DENY]
        typewriter_display = "\n".join(typewriter_texts)
        hide_views = self.data['config']['premium'].get("hide_views", emojis.DENY)
        if hide_views == True:
            hide_views = emojis.APPROVE
        elif hide_views == False:
            hide_views = emojis.DENY
        parallax_animation = self.data['config']['premium'].get("parallax_animation", emojis.DENY)
        if parallax_animation == True:
            parallax_animation = emojis.APPROVE
        elif parallax_animation == False:
            parallax_animation = emojis.DENY

        embed_profile = discord.Embed(title="Premium Settings", color=colors.NEUTRAL)
        embed_profile.description = "> [Profile Customization](https://guns.lol/premium)"
        embed_profile.add_field(name="Layout", value=str(layout).capitalize(), inline=True)
        embed_profile.add_field(name="Animation", value=str(animation).capitalize(), inline=True)
        embed_profile.set_footer(text="Page 1/4 (4 entries)")
        embed_special = discord.Embed(title="Premium Settings", color=colors.NEUTRAL)
        embed_special.description = "> [Special Customization](https://guns.lol/premium)"
        embed_special.add_field(name="Cursor Effects", value=str(cursor_effects).capitalize(), inline=True)
        embed_special.add_field(name="Cursor Effects Color", value=effects_color, inline=True)
        embed_special.add_field(name="Text Font", value=str(font).capitalize(), inline=True)
        embed_special.add_field(name="Page Enter Text", value=page_enter_text, inline=True)
        embed_special.set_footer(text="Page 2/4 (4 entries)")
        embed_settings = discord.Embed(title="Premium Settings", color=colors.NEUTRAL)
        embed_settings.description = "> [Settings Customization](https://guns.lol/premium)"
        embed_settings.add_field(name="Typewriter Enabled", value=typewriter_enabled, inline=True)
        embed_settings.add_field(name="Parallax Animation", value=parallax_animation, inline=True)
        embed_settings.add_field(name="Hide Views", value=hide_views, inline=True)
        embed_settings.add_field(name="Typewriter Texts", value=typewriter_display, inline=False)
        embed_settings.set_footer(text="Page 3/4 (4 entries)")
        if layout == "default":
            border_enabled = self.data['config']['premium'].get("border_enabled", emojis.DENY)
            if border_enabled == True:
                border_enabled = emojis.APPROVE
            elif border_enabled == False:
                border_enabled = emojis.DENY
            banner = self.data['config']['premium'].get("banner", emojis.DENY)
            if banner:
                banner = f"[Click here]({banner})"
            else:
                banner = emojis.DENY
            border_color = self.data['config']['premium'].get("border_color", emojis.DENY)
            border_width = self.data['config']['premium'].get("border_width", emojis.DENY)
            border_radius = self.data['config']['premium'].get("border_radius", emojis.DENY)
            
            embed_layout = discord.Embed(title="Premium Settings", color=colors.NEUTRAL)
            embed_layout.description = "> [Layout Settings](https://guns.lol/premium/layout)"
            embed_layout.add_field(name="Border Enabled", value=border_enabled, inline=True)
            embed_layout.add_field(name="Banner", value=banner, inline=True)
            embed_layout.add_field(name="\u200b", value="\u200b", inline=True)
            embed_layout.add_field(name="Border Color", value=border_color, inline=True)
            embed_layout.add_field(name="Border Width", value=f"{border_width}px", inline=True)
            embed_layout.add_field(name="Border Radius", value=f"{border_radius}px", inline=True)
            embed_layout.set_footer(text="Page 4/4 (4 entries)")
        if layout == "modern":
            border_enabled = self.data['config']['premium'].get("border_enabled", emojis.DENY)
            if border_enabled == True:
                border_enabled = emojis.APPROVE
            elif border_enabled == False:
                border_enabled = emojis.DENY
            second_tab = self.data.get("second_tab", {})
            discord_link = second_tab.get("discord", None)
            spotify_link = second_tab.get("spotify", None)
            hide_join_date = self.data['config']['premium'].get("hide_join_date", emojis.DENY)
            if hide_join_date == True:
                hide_join_date = emojis.APPROVE
            elif hide_join_date == False:
                hide_join_date = emojis.DENY
            border_color = self.data['config']['premium'].get("border_color", emojis.DENY)
            border_width = self.data['config']['premium'].get("border_width", emojis.DENY)
            border_radius = self.data['config']['premium'].get("border_radius", emojis.DENY)

            embed_layout = discord.Embed(title="Premium Settings", color=colors.NEUTRAL)
            embed_layout.description = "> [Layout Settings](https://guns.lol/premium/layout)"
            embed_layout.add_field(name="Border Enabled", value=border_enabled, inline=True)
            if discord_link:
                embed_layout.add_field(name="Discord", value=discord_link, inline=True)
            if spotify_link:
                embed_layout.add_field(name="Spotify", value=spotify_link, inline=True)
            embed_layout.add_field(name="Hide Join Date", value=hide_join_date, inline=True)
            embed_layout.add_field(name="\u200b", value="\u200b", inline=True)
            embed_layout.add_field(name="Border Color", value=border_color, inline=True)
            embed_layout.add_field(name="Border Width", value=f"{border_width}px", inline=True)
            embed_layout.add_field(name="Border Radius", value=f"{border_radius}px", inline=True)
            embed_layout.set_footer(text="Page 4/4 (4 entries)")
        if layout == "simplistic":
            show_url = self.data['config']['premium'].get("show_url", emojis.DENY)
            if show_url == True:
                show_url = emojis.APPROVE
            elif show_url == False:
                show_url = emojis.DENY
            button_shadow = self.data['config']['premium'].get("button_shadow", emojis.DENY)
            if button_shadow == True:
                button_shadow = emojis.APPROVE
            elif button_shadow == False:
                button_shadow = emojis.DENY
            button_border_radius = self.data['config']['premium'].get("button_border_radius", emojis.DENY)
            buttons = self.data['config']['premium'].get("buttons", [])

            embed_layout = discord.Embed(title="Premium Settings", color=colors.NEUTRAL)
            embed_layout.description = "> [Layout Settings](https://guns.lol/premium/layout)"
            embed_layout.add_field(name="Show URL", value=show_url, inline=True)
            embed_layout.add_field(name="Button Shadow", value=button_shadow, inline=True)
            embed_layout.add_field(name="Button Border Radius", value=f"{button_border_radius}px", inline=True)
            if buttons:
                button_links = ", ".join([f"[{button['button_title']}]({button['button_url']})" for button in buttons])
                embed_layout.add_field(name="Buttons", value=button_links, inline=False)
            embed_layout.set_footer(text="Page 4/4 (4 entries)")
        await ctx.paginator(embeds=[embed_profile, embed_special, embed_settings, embed_layout], author_only=False, interaction=interaction, ephemeral=True)

    @discord.ui.button(label="Links", style=discord.ButtonStyle.secondary)
    async def links(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await self.bot.get_context(interaction.message)
        socials = self.data["config"].get("socials", [])
        if not socials:
            return await interaction.response.send_message(embed=discord.Embed(description=f"{emojis.WARNING} {interaction.user.mention}: No socials linked to this guns.lol account", color=colors.WARNING), ephemeral=True)
        embeds = []
        for i in range(0, len(socials), 9):
            embed = discord.Embed(title="Social Links", color=colors.NEUTRAL)
            for social in socials[i:i+9]:
                social_name = "Custom URL" if social["social"] == "custom_url" else str(social["social"]).capitalize()
                social_value = f'{social["value"]} [`Icon`]({social["icon"]})' if social["social"] == "custom_url" else social["value"]
                embed.add_field(name=social_name, value=social_value, inline=True)
                embed.set_footer(text=f"Page: {i//9 + 1}/{len(socials)//9 + 1} ({len(socials)} entries)")
            embeds.append(embed)
        if len(embeds) == 1:
            await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        else:
            await ctx.paginator(embeds, author_only=False, interaction=interaction, ephemeral=True)

    @discord.ui.button(label="Audios", style=discord.ButtonStyle.secondary)
    async def audios(self, interaction: discord.Interaction, button: discord.ui.Button):
        audio_url = self.data["config"].get("audio", [])
        if not audio_url:
            return await interaction.response.send_message(embed=discord.Embed(description=f"{emojis.WARNING} {interaction.user.mention}: No audio files found for this account", color=colors.WARNING), ephemeral=True)
        await interaction.response.defer()
        files = []
        async with aiohttp.ClientSession() as session:
            if isinstance(audio_url, str):
                url = audio_url
                title = "Unknown Title"
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            audio_data = await resp.read()
                            discord_file = discord.File(fp=io.BytesIO(audio_data), filename=f"{title}.mp3")
                            files.append(discord_file)
                except aiohttp.ClientError as e:
                    return await interaction.followup.send(embed=discord.Embed(description=f"{emojis.WARNING} {interaction.user.mention}: Error downloading **{title}** from\n> {url}", color=colors.WARNING), ephemeral=True)
            elif isinstance(audio_url, list):
                selected_audios = [audio for audio in audio_url]
                for audio in selected_audios:
                    url = audio.get("url")
                    title = audio.get("title", "Unknown Title")
                    try:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                audio_data = await resp.read()
                                discord_file = discord.File(fp=io.BytesIO(audio_data), filename=f"{title}.mp3")
                                files.append(discord_file)
                    except aiohttp.ClientError as e:
                        pass
            else:
                pass
        if files:
            await interaction.followup.send(files=files, ephemeral=True)

    @discord.ui.button(label="Badges", style=discord.ButtonStyle.secondary)
    async def badges(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        monochrome_badges = self.data.get('config', {}).get('premium', {}).get("monochrome_badges", emojis.DENY)
        if monochrome_badges is True:
            monochrome_badges = emojis.APPROVE
        elif monochrome_badges is False:
            monochrome_badges = emojis.DENY
        color = self.data.get("config", {}).get("badge_color", emojis.DENY)
        custom_badges = self.data.get('config', {}).get('custom_badges', [])
        badges_text = "No custom badges available"
        if isinstance(custom_badges, list) and custom_badges:
            formatted_badges = []
            for badge in custom_badges:
                if isinstance(badge, list) and len(badge) == 2:
                    name, icon_url = badge
                    formatted_badges.append(f"[{name}]({icon_url})")
                elif isinstance(badge, dict) and 'name' in badge and 'icon' in badge:
                    name = badge['name']
                    icon_url = badge['icon']
                    formatted_badges.append(f"[{name}]({icon_url})")
            if formatted_badges:
                badges_text = ", ".join(formatted_badges)
        embed = discord.Embed(title="Badges", color=colors.NEUTRAL)
        embed.add_field(name="Monochrome Badges", value=monochrome_badges, inline=True)
        embed.add_field(name="Badge Color", value=color, inline=True)
        embed.add_field(name="Custom Badges", value=badges_text, inline=False)
        return await interaction.followup.send(embed=embed, ephemeral=True)
    
class ServerView(View):
    def __init__(self, guild_name: str):
        super().__init__()
        self.guild_name = guild_name
        self.children[0].label = f"Sent from server: {self.guild_name}"

    @button(label="Sent from server:", style=ButtonStyle.gray, disabled=True)
    async def server_button(self, interaction, button):
        await interaction.response.send_message(f"Button pressed in server: {self.guild_name}")