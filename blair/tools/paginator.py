from __future__ import annotations

import uuid

import discord
from discord.ext import commands
from tools.config import color, emoji


class Simple(discord.ui.View):
    def __init__(
        self,
        *,
        timeout: int = None,
        PreviousButton: discord.ui.Button = discord.ui.Button(
            emoji="<:left:1294716353952874547>", style=discord.ButtonStyle.primary
        ),
        NextButton: discord.ui.Button = discord.ui.Button(
            emoji="<:right:1294716290199720037>", style=discord.ButtonStyle.primary
        ),
        ExitButton: discord.ui.Button = discord.ui.Button(
            emoji="<:exit:1294716331538645044>", style=discord.ButtonStyle.grey
        ),
        PaginateButton: discord.ui.Button = discord.ui.Button(
            emoji="<:paginate:1294716310701215784>", style=discord.ButtonStyle.grey
        ),
        InitialPage: int = 0,
        AllowExtInput: bool = False,
        ephemeral: bool = False,
    ) -> None:
        super().__init__(timeout=timeout)

        self.PreviousButton = PreviousButton
        self.NextButton = NextButton
        self.ExitButton = ExitButton
        self.PaginateButton = PaginateButton
        self.InitialPage = InitialPage
        self.AllowExtInput = AllowExtInput
        self.ephemeral = ephemeral

        self.pages = None
        self.ctx = None
        self.message = None
        self.current_page = None
        self.total_page_count = None
        self.paginator_id = str(uuid.uuid4())

        self.PreviousButton.custom_id = f"previous:{self.paginator_id}"
        self.NextButton.custom_id = f"next:{self.paginator_id}"
        self.ExitButton.custom_id = f"exit:{self.paginator_id}"
        self.PaginateButton.custom_id = f"paginate:{self.paginator_id}"

        self.PreviousButton.callback = self.previous_button_callback
        self.NextButton.callback = self.next_button_callback
        self.ExitButton.callback = self.exit_button_callback
        self.PaginateButton.callback = self.paginate_button_callback

        self.add_item(self.PreviousButton)
        self.add_item(self.NextButton)
        self.add_item(self.ExitButton)
        self.add_item(self.PaginateButton)

    async def start(
        self, ctx: discord.Interaction | commands.Context, pages: list[discord.Embed]
    ):
        if isinstance(ctx, discord.Interaction):
            ctx = await commands.Context.from_interaction(ctx)

        self.pages = pages
        self.total_page_count = len(pages)
        self.ctx = ctx
        self.current_page = self.InitialPage

        self.message = await ctx.send(
            embed=self.pages[self.InitialPage], view=self, ephemeral=self.ephemeral
        )

    async def previous(self):
        if self.current_page == 0:
            self.current_page = self.total_page_count - 1
        else:
            self.current_page -= 1
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def next(self):
        if self.current_page == self.total_page_count - 1:
            self.current_page = 0
        else:
            self.current_page += 1
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def exit(self):
        await self.message.delete()

    async def paginate_to_page(self, page_number: int):
        if 0 <= page_number < self.total_page_count:
            self.current_page = page_number
            await self.message.edit(embed=self.pages[self.current_page], view=self)
        else:
            await self.ctx.send(f"{emoji.deny} Invalid page number", ephemeral=True)

    async def previous_button_callback(self, interaction: discord.Interaction):
        if not self.is_valid_interaction(interaction, "previous"):
            return
        await self.previous()
        await interaction.response.defer()

    async def next_button_callback(self, interaction: discord.Interaction):
        if not self.is_valid_interaction(interaction, "next"):
            return
        await self.next()
        await interaction.response.defer()

    async def exit_button_callback(self, interaction: discord.Interaction):
        if not self.is_valid_interaction(interaction, "exit"):
            return
        await self.exit()
        await interaction.response.defer()

    async def paginate_button_callback(self, interaction: discord.Interaction):
        if not await self.is_valid_interaction(interaction, "paginate"):
            return

        options = [
            discord.SelectOption(label=f"Page {i + 1}", value=str(i))
            for i in range(self.total_page_count)
        ]
        select = discord.ui.Select(
            placeholder="Select a page",
            options=options,
            custom_id=f"select:{self.paginator_id}",
        )

        async def select_callback(interaction: discord.Interaction):
            page_number = int(select.values[0])
            await self.paginate_to_page(page_number)

            select.disabled = True
            await interaction.message.edit(view=self)
            await interaction.response.defer()

        select.callback = select_callback

        view = discord.ui.View()
        view.add_item(select)
        user_pfp = (
            interaction.user.avatar.url
            if interaction.user.avatar
            else interaction.user.default_avatar.url
        )
        embed = discord.Embed(
            description="> **Choose** a page for you to go on", color=color.default
        )
        embed.set_author(name=f"{interaction.user.name} | paginate", icon_url=user_pfp)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def is_valid_interaction(
        self, interaction: discord.Interaction, button_id: str
    ):
        if interaction.data["custom_id"] != f"{button_id}:{self.paginator_id}":
            return False

        if interaction.user != self.ctx.author and not self.AllowExtInput:
            embed = discord.Embed(
                description=f"{emoji.deny} {interaction.user.mention}: You **cannot** interact with this",
                color=color.deny,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

        return True
