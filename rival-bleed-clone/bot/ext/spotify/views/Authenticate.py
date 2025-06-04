from discord.ui import View, button, Modal, Button, TextInput
from discord import Interaction, ButtonStyle, Message
from ..models.user import SpotifyUser, Callback
from lib.patch.context import Context
from loguru import logger
from urllib.parse import parse_qs
from base64 import b64decode
import discord


class AuthenticationModel(Modal, title="Connect Your Spotify"):
    code = TextInput(label="Connect Your Spotify", placeholder="Code...")

    async def interaction_check(self, interaction: Interaction):
        if interaction.data["components"][0]["components"][0]["value"]:
            name = interaction.data["components"][0]["components"][0]["value"]
            await interaction.response.defer()
            return True
        else:
            await interaction.response.send_message(
                "Please enter your Spotify code.", ephemeral=True
            )
            return False


class AuthenticationView(View):
    def __init__(self, ctx: Context, user: SpotifyUser):
        self.ctx = ctx
        self.user = user
        self.message: Message = None
        super().__init__(timeout=None)

    @discord.ui.button(emoji="🔗", label="Submit Code", style=ButtonStyle.gray)
    async def submit_code(self, interaction: Interaction, button: Button):
        modal = AuthenticationModel()
        await interaction.response.send_modal(modal)
        await modal.wait()
        code = modal.code.value
        try:
            code = b64decode(code.encode("utf-8")).decode("utf-8")
        except Exception:
            code = code
        _params = parse_qs(code)
        values = list(_params.values())
        code = values[0][0]
        state = values[1][0]
        callback = Callback(code=code, state=state)
        d = await self.user.authorize(callback)
        logger.info(f"authorization returned {d}")
        user = await self.user.session.current_user()
        url = f"https://open.spotify.com/{user.uri.split('spotify:', 1)[1].replace(':', '/')}"
        embed = await self.ctx.success(
            f"Your **Discord Account** has been connected to [{user.display_name}]({url})",
            return_embed=True,
        )
        return await self.message.edit(embed=embed, view=None)
