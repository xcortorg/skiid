import re
import json
import datetime

from modules.styles import emojis, colors
from modules.exceptions import RenameRateLimit

from discord import Embed, Interaction, TextStyle, ButtonStyle, Guild, utils, VoiceChannel
from discord.ui import Modal, Button, View, TextInput, UserSelect
from discord.interactions import Interaction
from discord.ext.commands import AutoShardedBot, CommandError, BadArgument
from discord.errors import HTTPException

async def rename_vc_bucket(bot: AutoShardedBot, channel: VoiceChannel):
    bucket = await bot.cache.get(f"vc-bucket-{channel.id}")
    if not bucket:
        bucket = []
    bucket.append(datetime.datetime.now())
    to_remove = [d for d in bucket if (datetime.datetime.now() - d).total_seconds() > 600]
    for l in to_remove:
        bucket.remove(l)
    await bot.cache.set(f"vc-bucket-{channel.id}", bucket)
    if len(bucket) >= 3:
        raise RenameRateLimit()
    return True

def validator(text: str, max_len: int, error: str):
    if len(text) >= max_len:
        raise BadArgument(error)

def is_url(text: str):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s!()\[\]{};:'\".,<>?«»“”‘’]))"
    return bool(re.search(regex, text))

class ButtonScript:
    def script(params: str):
        x = {}
        fields = []
        content = None
        list = []
        params = params.replace("{embed}", "")
        parts = [p[1:][:-1] for p in params.split("$v")]
        for part in parts:
            if part.startswith("content:"):
                content = part[len("content:"):]
                validator(content, 2000, "Message content too long")
            if part.startswith("title:"):
                x["title"] = part[len("title:"):]
                validator(part[len("title:"):], 256, "Embed title too long")
            if part.startswith("url:"):
                url = part[len("url:"):].strip()
                if is_url(url):
                    x["url"] = url
            if part.startswith("description:"):
                x["description"] = part[len("description:"):]
                validator(part[len("description:"):], 2048, "Embed description too long")
            if part.startswith("color:"):
                try:
                    x["color"] = int(part[len("color:"):].replace("#", ""), 16)
                except:
                    x["color"] = int("808080", 16)
            if part.startswith("thumbnail:"):
                thumbnail_url = part[len("thumbnail:"):].strip()
                if is_url(thumbnail_url):
                    x["thumbnail"] = {"url": thumbnail_url}
            if part.startswith("image:"):
                image_url = part[len("image:"):].strip()
                if is_url(image_url):
                    x["image"] = {"url": image_url}
            if part == "timestamp":
                x["timestamp"] = datetime.datetime.now().isoformat()
            if part.startswith("author:"):
                author_parts = part[len("author: "):].split(" && ")
                name = None
                url = None
                icon_url = None
                for z in author_parts:
                    if z.startswith("name:"):
                        name = z[len("name:"):]
                        validator(name, 256, "author name too long")
                    if z.startswith("icon:"):
                        icon_url = z[len("icon:"):]
                        icon_url = icon_url if is_url(icon_url) else None
                    if z.startswith("url:"):
                        url = z[len("url:"):]
                        url = url if is_url(url) else None
                x["author"] = {"name": name}
                if icon_url:
                    x["author"]["icon_url"] = icon_url
                if url:
                    x["author"]["url"] = url
            if part.startswith("field:"):
                name = None
                value = None
                inline = False
                field_parts = part[len("field: "):].split(" && ")
                for z in field_parts:
                    if z.startswith("name:"):
                        name = z[len("name:"):]
                        validator(name, 256, "field name too long")
                    if z.startswith("value:"):
                        value = z[len("value:"):]
                        validator(value, 1024, "field value too long")
                    if z.strip() == "inline":
                        inline = True
                fields.append({"name": name, "value": value, "inline": inline})
            if part.startswith("footer:"):
                text = None
                icon_url = None
                footer_parts = part[len("footer: "):].split(" && ")
                for z in footer_parts:
                    if z.startswith("text:"):
                        text = z[len("text:"):]
                        validator(text, 2048, "footer text too long")
                    if z.startswith("icon:"):
                        icon_url = z[len("icon:"):]
                        if not is_url(icon_url):
                            icon_url = None
                if text:
                    x["footer"] = {"text": text}
                    if icon_url:
                        x["footer"]["icon_url"] = icon_url
            if part.startswith("button:"):
                choices = part[len("button: ") :].split(" && ")
                button_action = choices[0]
                label = ""
                emoji = None
                style = "gray"
                for choice in choices:
                    if choice.startswith("label:"):
                        label = choice[len("label: ") :]
                    if choice.startswith("emoji:"):
                        emoji = choice[len("emoji: ") :]
                    if choice.startswith("style:"):
                        style = choice[len("style: ") :]
                list.append((button_action, label, emoji, style))
        if not x:
            embed = None
        else:
            x["fields"] = fields
            embed = Embed.from_dict(x)
        return content, embed, list

class InteractionMes:
    @staticmethod
    async def vc_task(interaction: Interaction) -> tuple[bool, str | None]:
        if not interaction.user.voice:
            return False, "You are **not** in a voice channel"
        if not interaction.user.voice.channel:
            return False, "You are **not** in a valid voice channel"
        check = await interaction.client.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", interaction.guild.id)
        if not check:
            return False, "VoiceMaster is **not** configured"
        check_vc = await interaction.client.db.fetchrow("SELECT user_id FROM voicemaster_channels WHERE voice = $1", interaction.user.voice.channel.id)
        if not check_vc:
            return False, "This voice channel is **not** managed by the system"
        if check_vc[0] != interaction.user.id:
            return False, "You are **not** the **owner** of this voice channel"
        return True, None

class RenameModal(Modal, title="rename your voice channel"):
    name = TextInput(label="voice channel name", placeholder="the new voice channel name...", style=TextStyle.short)

    async def get_banned_words(self, interaction, guild_id):
        banned_words_json = await interaction.client.db.fetchval("SELECT banned_words FROM voicemaster WHERE guild_id = $1", guild_id)
        if banned_words_json:
            return json.loads(banned_words_json)
        return []

    async def save_banned_words(self, interaction, guild_id, banned_words):
        banned_words_json = json.dumps(banned_words)
        await interaction.client.db.execute("UPDATE voicemaster SET banned_words = $1 WHERE guild_id = $2", banned_words_json, guild_id)

    def contains_banned_words(self, banned_words, text):
        text_lower = text.lower()
        return any(banned_word in text_lower for banned_word in banned_words)

    async def on_submit(self, interaction: Interaction) -> None:
        banned_words = await self.get_banned_words(interaction, interaction.guild.id)
        if self.contains_banned_words(banned_words, self.name.value):
            return await interaction.warn("This voice channel name contains a prohibited word. Please choose a different name.", ephemeral=True)
        await rename_vc_bucket(interaction.client, interaction.user.voice.channel)
        try:
            await interaction.user.voice.channel.edit(name=self.name.value, reason=f"Voice channel name changed by {interaction.user}")
        except HTTPException:
            return await interaction.warn("Name contains words not allowed for servers in Server Discover", ephemeral=True)
        savesettings = await interaction.client.db.fetchval("SELECT savesettings FROM voicemaster WHERE guild_id = $1", interaction.guild.id)
        if savesettings:
            await interaction.client.db.execute("INSERT INTO voicemaster_names (guild_id, user_id, name) VALUES ($1, $2, $3) ON CONFLICT (guild_id, user_id) DO UPDATE SET name = $3", interaction.guild.id, interaction.user.id, self.name.value)
        await interaction.approve(f"Voice channel name changed to **{self.name.value}**", ephemeral=True)

    async def on_error(self, interaction: Interaction, error: CommandError):
        if isinstance(error, RenameRateLimit):
            return await interaction.warn(error.message, ephemeral=True)
        return await interaction.warn(error.args[0], ephemeral=True)

class rename(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, style=style, emoji=emoji, custom_id="persistent_view:rename")

    async def callback(self, interaction: Interaction) -> None:
        if await InteractionMes.vc_task(interaction):
            await interaction.response.send_modal(RenameModal())

class lock(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, style=style, emoji=emoji, custom_id="persistent_view:lock")

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        overwrite = interaction.user.voice.channel.overwrites_for(interaction.guild.default_role)
        overwrite.connect = False
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Channel locked by {interaction.user}")
        return await interaction.embed(f"{emojis.LOCK} {interaction.user.mention}: Locked {interaction.user.voice.channel.mention}", ephemeral=True)

class unlock(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, style=style, emoji=emoji, custom_id="persistent_view:unlock")

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        overwrite = interaction.user.voice.channel.overwrites_for(interaction.guild.default_role)
        overwrite.connect = True
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Channel unlocked by {interaction.user}")
        return await interaction.embed(f"{emojis.UNLOCK} {interaction.user.mention}: Unlocked {interaction.user.voice.channel.mention}", ephemeral=True)

class hide(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style, custom_id="persistent_view:hide")

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        overwrite = interaction.user.voice.channel.overwrites_for(interaction.guild.default_role)
        overwrite.view_channel = False
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Channel hidden by {interaction.user}")
        return await interaction.embed(f"{emojis.HIDE} {interaction.user.mention}: Hidden {interaction.user.voice.channel.mention}", ephemeral=True)

class reveal(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style, custom_id="persistent_view:reveal")

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        overwrite = interaction.user.voice.channel.overwrites_for(interaction.guild.default_role)
        overwrite.view_channel = True
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Channel revealed by {interaction.user}")
        return await interaction.embed(f"{emojis.REVEAL} {interaction.user.mention}: Revealed {interaction.user.voice.channel.mention}", ephemeral=True)

class decrease(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style, custom_id="persistent_view:decrease")

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        if interaction.user.voice.channel.user_limit == 0:
            return await interaction.warn("Limit can't be lower than 0", ephemeral=True)
        await interaction.user.voice.channel.edit(user_limit=interaction.user.voice.channel.user_limit - 1, reason=f"Channel user limit decreased by {interaction.user}")
        return await interaction.embed(f"{emojis.DECREASE} {interaction.user.mention}: Decreased {interaction.user.voice.channel.mention}'s member limit", ephemeral=True)

class increase(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style, custom_id="persistent_view:increase")

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        if interaction.user.voice.channel.user_limit == 99:
            return await interaction.warn("Limit can't be higher than 99", ephemeral=True)
        await interaction.user.voice.channel.edit(user_limit=interaction.user.voice.channel.user_limit + 1, reason=f"Channel user limit increased by {interaction.user}")
        return await interaction.embed(f"{emojis.INCREASE} {interaction.user.mention}: Increased {interaction.user.voice.channel.mention}'s member limit", ephemeral=True)

class info(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style, custom_id="persistent_view:info")

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        check = await interaction.client.db.fetchrow("SELECT user_id FROM voicemaster_channels WHERE voice = $1", interaction.user.voice.channel.id)
        member = interaction.guild.get_member(check[0])
        permitted_members = [voice_member.mention for voice_member in interaction.guild.members if interaction.user.voice.channel.permissions_for(voice_member).connect]
        description = f"**Owner:** {member.mention} (`{member.id}`)\n**Created:** {utils.format_dt(interaction.user.voice.channel.created_at, style='R')}\n**Bitrate:** {interaction.user.voice.channel.bitrate/1000}kbps\n**Permitted:** {', '.join(permitted_members)}"
        if len(description) > 4096:
            description = description[:4093] + "..."
        embed = Embed(color=colors.NEUTRAL, title=interaction.user.voice.channel.name, description=description)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        return await interaction.followup.send(embed=embed, ephemeral=True)

class claim(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style, custom_id="persistent_view:claim")

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        if not interaction.user.voice:
            return await interaction.warn("You are **not** in a voice channel", ephemeral=True)
        check = await interaction.client.db.fetchrow("SELECT user_id FROM voicemaster_channels WHERE voice = $1", interaction.user.voice.channel.id)
        if check is None:
            return await interaction.warn("This voice channel is not managed by the system", ephemeral=True)
        owner = interaction.guild.get_member(check[0])
        if owner in interaction.user.voice.channel.members:
            return await interaction.warn("The owner is still in the voice channel", ephemeral=True)
        await interaction.client.db.execute("UPDATE voicemaster_channels SET user_id = $1 WHERE voice = $2", interaction.user.id, interaction.user.voice.channel.id)
        if owner:
            await interaction.user.voice.channel.set_permissions(owner, view_channel=None, connect=None)
        await interaction.user.voice.channel.set_permissions(interaction.user, view_channel=True, connect=True)
        return await interaction.embed(f"{emojis.CLAIM} {interaction.user.mention}: You are the new owner of the voice channel", ephemeral=True)

class kick(Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style, custom_id="persistent_view:manage_access")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        view = View()
        view.add_item(PermitButton(label="Permit", style=ButtonStyle.green))
        view.add_item(UnPermitButton(label="Unpermit", style=ButtonStyle.red))
        view.add_item(KickButton(label="Kick", style=ButtonStyle.grey))
        embed = Embed(color=colors.NEUTRAL, description=f"{interaction.user.mention}: Choose an action to perform on a member in the voice channel")
        return await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class PermitButton(Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style, custom_id="persistent_view:permit")

    async def callback(self, interaction: Interaction):
        await send_user_selection(interaction, "permit")

class UnPermitButton(Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style, custom_id="persistent_view:unpermit")

    async def callback(self, interaction: Interaction):
        await send_user_selection(interaction, "unpermit")

class KickButton(Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style, custom_id="persistent_view:kick")

    async def callback(self, interaction: Interaction):
        await send_user_selection(interaction, "kick")

async def send_user_selection(interaction: Interaction, action: str):
    await interaction.response.defer(ephemeral=True)
    ok, reason = await InteractionMes.vc_task(interaction)
    if not ok:
        return await interaction.warn(reason, ephemeral=True)
    if action == "kick" and len(interaction.user.voice.channel.members) == 1:
        return await interaction.warn("You are the only member in the voice channel", ephemeral=True)
    select = UserSelection(action)
    view = View()
    view.add_item(select)
    embed = Embed(color=colors.NEUTRAL, description=f"{interaction.user.mention}: Use the dropdown menu to select the members")
    await interaction.edit_original_response(embed=embed, view=view)

class UserSelection(UserSelect):
    def __init__(self, action: str):
        self.action = action
        super().__init__(placeholder=f"Who do you want to {action}?", min_values=1, max_values=5)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        ok, reason = await InteractionMes.vc_task(interaction)
        if not ok:
            return await interaction.warn(reason, ephemeral=True)
        members = [interaction.guild.get_member(user.id) for user in self.values]
        if self.action == "permit":
            for member in members:
                await interaction.user.voice.channel.set_permissions(member, connect=True, view_channel=True)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: {', '.join(member.mention for member in members)} have been permitted")
        elif self.action == "unpermit":
            for member in members:
                await interaction.user.voice.channel.set_permissions(member, connect=False)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: {', '.join(member.mention for member in members)} have been unpermitted")
        elif self.action == "kick":
            for member in members:
                await interaction.user.voice.channel.set_permissions(member, connect=False)
                try:
                    await member.move_to(channel=None, reason=f"Member kicked from voice channel by {interaction.user}")
                except:
                    pass
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: {', '.join(member.mention for member in members)} have been kicked")
        await interaction.edit_original_response(embed=embed, view=None)

class VoiceMasterView(View):
    def __init__(self, bot: AutoShardedBot, to_add: list = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.styles = {"red": ButtonStyle.danger, "green": ButtonStyle.green, "blue": ButtonStyle.blurple, "gray": ButtonStyle.gray}
        if to_add:
            for result in to_add:
                try:
                    self.readd_button(result["action"], label=result["label"], emoji=result["emoji"], style=result["style"])
                except:
                    continue

    def readd_button(self, action: str, /, *, label: str = "", emoji=None, style: str = "gray"):
        action = action.strip().lower()
        if action == "lock":
            self.add_item(lock(label, emoji, self.styles.get(style)))
        elif action == "unlock":
            self.add_item(unlock(label, emoji, self.styles.get(style)))
        elif action == "hide":
            self.add_item(hide(label, emoji, self.styles.get(style)))
        elif action == "reveal":
            self.add_item(reveal(label, emoji, self.styles.get(style)))
        elif action == "decrease":
            self.add_item(decrease(label, emoji, self.styles.get(style)))
        elif action == "increase":
            self.add_item(increase(label, emoji, self.styles.get(style)))
        elif action == "info":
            self.add_item(info(label, emoji, self.styles.get(style)))
        elif action == "kick":
            self.add_item(kick(label, emoji, self.styles.get(style)))
        elif action == "claim":
            self.add_item(claim(label, emoji, self.styles.get(style)))
        elif action == "rename":
            self.add_item(rename(label, emoji, self.styles.get(style)))

    async def add_button(self, guild: Guild, action: str, /, *, label: str = "", emoji=None, style: str = "gray"):
        self.readd_button(action, label=label, emoji=emoji, style=style)
        await self.bot.db.execute("INSERT INTO voicemaster_buttons VALUES ($1,$2,$3,$4,$5)", guild.id, action, label, emoji, style)

    async def add_default_buttons(self, guild: Guild):
        for action in [
            (f"{emojis.LOCK}", "lock"),
            (f"{emojis.UNLOCK}", "unlock"),
            (f"{emojis.HIDE}", "hide"),
            (f"{emojis.REVEAL}", "reveal"),
            (f"{emojis.CLAIM}", "claim"),
            (f"{emojis.KICK}", "kick"),
            (f"{emojis.INFO}", "info"),
            (f"{emojis.RENAME}", "rename"),
            (f"{emojis.INCREASE}", "increase"),
            (f"{emojis.DECREASE}", "decrease"),
        ]:
            await self.add_button(guild, action[1], emoji=action[0])