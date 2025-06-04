from discord.ui import View, Select
from discord import SelectOption, Interaction, Embed
from var.config import CONFIG
from ..models.user import SpotifyUser
from lib.patch.context import Context
from typing import Optional


class DeviceSelect(Select):
    def __init__(
        self,
        ctx: Context,
        options: list,
        placeholder: Optional[str] = "Select a device...",
    ):
        self.ctx = ctx
        self._options = options
        options = [
            SelectOption(
                label=_.name,
                description=str(_.type),
                value=_,
            )
            for _ in self._options.items
        ]
        super().__init__(
            custom_id="DeviceSelect",
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction):
        value = self.values[0]
        self.values.clear()
        await interaction.response.defer()
        self.view.children[0].placeholder = value
        await self.view.user.set_device(value)
        return await interaction.message.edit(
            embed=Embed(
                description=f"{CONFIG['emojis']['success']} {interaction.user.mention}: set your device to **{value.name}**",
                color=CONFIG["colors"]["success"],
            ),
            view=None,
        )


class DeviceView(View):
    def __init__(self, ctx: Context, user: SpotifyUser):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.user = user

    @classmethod
    async def initialize(cls, ctx: Context, user: SpotifyUser):
        self = cls(ctx=ctx, user=user)
        self.add_item(DeviceSelect(self.ctx, await self.user.devices()))
        return self
