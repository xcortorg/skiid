import discord, os
from var.config import CONFIG
from discord.ext import menus
from tuuid import tuuid
from ..util import image as GetImage


class StickerStealView(discord.ui.View, menus.MenuPages):
    def __init__(self, bot, source, sticker_steal):
        super().__init__(timeout=60)
        self._source = source
        self.value = 0
        self.sticker_steal = sticker_steal
        self.bot = bot
        self.current_page = 0
        self.ctx = None
        self.message = None

    async def start(self, ctx, *, channel=None, wait=False):
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def on_timeout(self):
        await self.message.edit(
            view=None,
            embed=discord.Embed(
                description=f"{CONFIG['emojis']['fail']} {self.ctx.author.mention}: **cancelled** sticker steal",
                color=0xD6BCD0,
            ),
        )
        if self.ctx.guild.id in self.sticker_steal:
            self.sticker_steal.pop(self.ctx.guild.id)
        return

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if "view" not in value:
            value.update({"view": self})
        return value

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                ephemeral=True,
                embed=discord.Embed(
                    description=f"{CONFIG['emojis']['warning']} <@!{interaction.user.id}>: **You aren't the author of this embed**",
                    color=0xD6BCD0,
                ),
            )
        else:
            await interaction.response.defer()
            return interaction.user == self.ctx.author

    @discord.ui.button(
        emoji=CONFIG["emojis"]["paginator"]["previous"], style=discord.ButtonStyle.grey
    )
    async def before_page(self, button, interaction):
        if self.current_page == 0:
            await self.show_page(self._source.get_max_pages() - 1)
        else:
            await self.show_checked_page(self.current_page - 1)
        # await interaction.response.defer()

    @discord.ui.button(
        emoji=CONFIG["emojis"]["paginator"]["next"], style=discord.ButtonStyle.grey
    )
    async def next_page(self, button, interaction):
        if self.current_page == self._source.get_max_pages() - 1:
            await self.show_page(0)
        else:
            await self.show_checked_page(self.current_page + 1)

    @discord.ui.button(
        emoji=CONFIG["emojis"]["success"], style=discord.ButtonStyle.grey
    )
    async def confirm(self, button, interaction):
        e = self.sticker_steal[self.ctx.guild.id][self.current_page]
        name = e.get("name", str(tuuid()))[:12]
        e_id = e.get("id")
        url = e.get("url")
        if len(self.ctx.guild.stickers) == self.ctx.guild.sticker_limit:
            return await self.message.edit(
                view=None,
                embed=discord.Embed(
                    color=0xD6BCD0,
                    description=f"{CONFIG['emojis']['warning']} {self.ctx.author.mention}: guild **sticker** limit reached",
                ),
            )
        f = await GetImage.download(url)
        emote = await self.ctx.guild.create_sticker(
            name=name,
            file=discord.File(f),
            description="Sticker",
            emoji="🥛",
            reason=f"Sticker Stolen By {str(self.ctx.author)}",
        )
        os.remove(f)
        await self.message.edit(
            view=None,
            embed=discord.Embed(
                description=f"{CONFIG['emojis']['success']} {self.ctx.author.mention}: **successfully** added {emote.name}",
                color=0xD6BCD0,
            ).set_image(url=url),
        )
        self.sticker_steal.pop(self.ctx.guild.id)
        return

    @discord.ui.button(emoji=CONFIG["emojis"]["fail"], style=discord.ButtonStyle.grey)
    async def deny(self, button, interaction):
        self.sticker_steal.pop(self.ctx.guild.id)
        await self.message.edit(
            view=None,
            embed=discord.Embed(
                description=f"{CONFIG['emojis']['fail']} {self.ctx.author.mention}: **cancelled** sticker steal",
                color=0xD6BCD0,
            ),
        )
