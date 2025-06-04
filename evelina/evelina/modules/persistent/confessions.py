import re

from discord import Embed, TextStyle, ButtonStyle, Thread
from discord import Interaction
from discord.ui import Modal, TextInput, Button, button, View

from modules.styles import emojis, colors

class confessModal(Modal, title="Submit a Confession"):
    content = TextInput(label="Confession Content", style=TextStyle.long, required=True)
    attachment = TextInput(label="Attachment (Optional)", style=TextStyle.short, required=False)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        check = await interaction.client.db.fetchrow("SELECT * FROM confess WHERE guild_id = $1", interaction.guild.id)
        if check:
            if re.search(r"[(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)", self.content.value):
                return await interaction.warn("You cannot use links in a confession", ephemeral=True)
            if self.attachment.value and not self.attachment.value.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                return await interaction.warn("Your attachment is not valid. The file must end in `.png`, `.jpg`, `.jpeg`, or `.gif`.", ephemeral=True)
            channel = interaction.guild.get_channel(check["channel_id"])
            if not channel:
                return await interaction.warn("Confession channel is **invalid**", ephemeral=True)
            count = check["confession"] + 1
            e = Embed(color=colors.NEUTRAL, description=f"```{self.content.value}```", title=f"Anonymous Confession (#{count})")
            if self.attachment.value:
                e.set_image(url=self.attachment.value)
            msg = await channel.send(embed=e, view=confessView(interaction.client))
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Sent your reply in {msg.jump_url}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            await interaction.client.db.execute("UPDATE confess SET confession = $1 WHERE guild_id = $2", count, interaction.guild.id)
            await interaction.client.db.execute("INSERT INTO confess_members VALUES ($1,$2,$3)", interaction.guild.id, interaction.user.id, count)
    
class confessReplyModal(Modal, title="Submit a Reply"):
    content = TextInput(label="Reply Content", style=TextStyle.long, required=True)
    attachment = TextInput(label="Attachment (Optional)", style=TextStyle.short, required=False)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        check = await interaction.client.db.fetchrow("SELECT * FROM confess WHERE guild_id = $1", interaction.guild.id)
        if check:
            if re.search(r"[(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)", self.content.value):
                return await interaction.warn("You cannot use links in a confession", ephemeral=True)
            if self.attachment.value and not self.attachment.value.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                return await interaction.warn("Your attachment is not valid. The file must end in `.png`, `.jpg`, `.jpeg`, or `.gif`.", ephemeral=True)
            channel = interaction.guild.get_channel(check["channel_id"])
            if not channel:
                return await interaction.warn("Confession channel is **invalid**", ephemeral=True)
            count = check["confession"] + 1
            e = Embed(color=colors.NEUTRAL, description=f"```{self.content.value}```", title=f"Anonymous Reply (#{count})")
            if self.attachment.value:
                e.set_image(url=self.attachment.value)
            if isinstance(interaction.message.channel, Thread):
                msg = await interaction.followup.send(embed=e, view=confessReplyView(interaction.client))
                await interaction.client.db.execute("UPDATE confess SET confession = $1 WHERE guild_id = $2", count, interaction.guild.id)
                return await interaction.client.db.execute("INSERT INTO confess_members VALUES ($1,$2,$3)", interaction.guild.id, interaction.user.id, count)
            if interaction.message.thread:
                thread = interaction.message.thread
            else:
                thread = await interaction.message.create_thread(name=f"Confession Replies")
                await thread.edit(auto_archive_duration=10080)
            msg = await thread.send(embed=e, view=confessReplyView(interaction.client))
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Sent your reply in {msg.jump_url}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            owner_id = await interaction.client.db.fetchval("SELECT user_id FROM confess_members WHERE confession = $1 AND guild_id = $2", check["confession"], interaction.guild.id)
            owner = interaction.guild.get_member(owner_id)
            if owner:
                embed = Embed(color=colors.NEUTRAL, description=f"Someone replied to your confession in {msg.jump_url}")
                await owner.send(embed=embed)
            await interaction.client.db.execute("UPDATE confess SET confession = $1 WHERE guild_id = $2", count, interaction.guild.id)
            await interaction.client.db.execute("INSERT INTO confess_members VALUES ($1,$2,$3)", interaction.guild.id, interaction.user.id, count)
    
class confessView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Submit a confession!", style=ButtonStyle.blurple, custom_id="persistent:submit_confession")
    async def submit_confession(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(confessModal())

    @button(label="Reply", style=ButtonStyle.secondary, custom_id="persistent:reply_confession")
    async def reply_confession(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(confessReplyModal())

class confessReplyView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Reply", style=ButtonStyle.secondary, custom_id="persistent:submit_reply")
    async def submit_reply(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(confessReplyModal())