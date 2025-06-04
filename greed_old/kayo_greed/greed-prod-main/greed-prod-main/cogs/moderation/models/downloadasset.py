from discord import ButtonStyle, Interaction, PartialEmoji, Emoji, Sticker, Embed, HTTPException, File
from discord.ui import Button, View, button
from io import BytesIO
from main import Context
from typing import Union
import config

class DownloadAsset(View):
    def __init__(
        self: "DownloadAsset", ctx: Context, asset: Union[PartialEmoji, Emoji, Sticker]
    ):
        super().__init__()
        self.ctx = ctx
        self.asset = asset
        self.pressed = False

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.warn(
                "You are **not** the author of this embed", ephemeral=True
            )
            return False

        if not interaction.user.guild_permissions.manage_expressions:
            await interaction.warn(
                "You do not have permissions to add emojis/stickers in this server",
                ephemeral=True,
            )
            return False

        if not interaction.user.guild.me.guild_permissions.manage_expressions:
            await interaction.warn(
                "The bot doesn't have permissions to add emojis/stickers in this server",
                ephemeral=True,
            )
            return False

        return True

    @button(label="Download", style=ButtonStyle.green)
    async def download_asset(
        self: "DownloadAsset", interaction: Interaction, button: Button
    ):
        self.pressed = True
        if isinstance(self.asset, (PartialEmoji, Emoji)):
            try:
                e = await interaction.guild.create_custom_emoji(
                    name=self.asset.name,
                    image=await self.asset.read(),
                    reason=f"Emoji added by {interaction.user}",
                )

                embed = Embed(
                    color=config.CLIENT.COLORS.APPROVE,
                    description=f"{interaction.client.yes} {interaction.user.mention}: Added {e} as [**{e.name}**]({e.url})",
                )

            except HTTPException:
                embed = Embed(
                    color=config.CLIENT.COLORS.WARN,
                    description=f"{interaction.client.warning} {interaction.user.mention}: Unable to add emoji",
                )
            finally:
                await interaction.response.edit_message(
                    embed=embed, view=None, attachments=[]
                )

        else:
            try:
                file = File(BytesIO(await self.asset.read()))
                sticker = await interaction.guild.create_sticker(
                    name=self.asset.name,
                    description=self.asset.name,
                    emoji="💀",
                    file=file,
                    reason=f"Sticker created by {interaction.user}",
                )

                embed = Embed(
                    color=config.CLIENT.COLORS.APPROVE,
                    description=f"{interaction.client.yes} {interaction.user.mention}: Added sticker as [**{sticker.name}**]({sticker.url})",
                )

            except HTTPException:
                embed = Embed(
                    color=config.CLIENT.COLORS.WARN,
                    description=f"{interaction.client.warning} {interaction.user.mention}: Unable to add sticker",
                )
            finally:
                await interaction.response.edit_message(
                    embed=embed, view=None, attachments=[]
                )

    async def on_timeout(self):
        if not self.pressed:
            await self.message.edit(view=None)