import discord
from loguru import logger
from var.config import CONFIG

class UserInfo(discord.ui.View):
    def __init__(self, ctx, bot, pages):
        super().__init__(timeout = None)
        self.ctx = ctx
        self.bot = bot
        self.page = 1
        self.responded = False
        self.pages = pages

    async def edit_message(self, interaction: discord.Interaction, **kwargs):
        self.bot.inter = interaction
        try:
            try:
                return await interaction.message.edit_message(**kwargs)
            except Exception:
                try:
                    logger.info("2")
                    return await interaction.message.edit(**kwargs)
                except Exception:
                    try:
                        return await interaction.response.edit_message(**kwargs)
                    except Exception as e:
                        raise e
        except Exception as e:
            raise e

    @discord.ui.button(
        emoji=CONFIG["emojis"].get("information"),
        custom_id="info",
        style=discord.ButtonStyle.grey,
    )
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.inter = interaction
        if interaction.user.id != self.ctx.author.id:
            if self.responded:
                i = await interaction.original_response()
            else:
                i = interaction.message
            try:
                return await interaction.warn("you cannot **interact** with this",
                    ephemeral=True,
                )
            except Exception:
                return await interaction.response.defer()
        if self.page == 2:
            kwargs = {'embed': self.pages[0], 'view': self}
            try:
                p = await self.edit_message(interaction, **kwargs)
                self.page = 1
            except Exception as e:
                return await interaction.response.send_message("lol couldnt respond")
        else:
            self.page = 2
            kwargs = {'embed': self.pages[1], 'view': self}
            try:
                p = await self.edit_message(interaction, **kwargs)
                self.responded = True
            except Exception as e:
                return await interaction.response.send_message("lol couldnt respond")
        return await interaction.response.defer()
