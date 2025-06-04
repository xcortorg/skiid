from __future__ import annotations

import random
from contextlib import suppress
from typing import Optional

import config
from discord import ButtonStyle, Embed, HTTPException, Member, Message, User
from discord.emoji import Emoji
from discord.interactions import Interaction
from discord.partial_emoji import PartialEmoji
from discord.ui import Button as OriginalButton
from discord.ui import View as OriginalView
from tools.client.context import Context


class View(OriginalView):
    ctx: Context
    opponent: Member
    message: Message

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def edit_message(self, *args: str, mention: bool = True) -> Message:
        # Provide a default implementation or ensure subclasses implement this
        if not hasattr(self, "message"):
            raise NotImplementedError(
                "Subclasses must implement this method or set 'self.message'"
            )
        # Example implementation
        embed = Embed(description="\n> ".join(args))
        return await self.message.edit(content=None, embed=embed, view=self)

    async def callback(self, interaction: Interaction, button: Button):
        raise NotImplementedError

    async def disable_buttons(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore

    async def on_timeout(self) -> None:
        await self.disable_buttons()
        with suppress(HTTPException):
            await self.message.delete()  # Delete the message instead of editing it

        self.stop()


class Button(OriginalButton):
    view: View
    custom_id: str

    def __init__(
        self,
        *,
        style: ButtonStyle = ButtonStyle.gray,
        label: str | None = None,
        disabled: bool = False,
        custom_id: str | None = None,
        url: str | None = None,
        emoji: str | Emoji | PartialEmoji | None = None,
        row: int | None = None,
    ):
        super().__init__(
            style=style,
            label=label,
            disabled=disabled,
            custom_id=custom_id,
            url=url,
            emoji=emoji,
            row=row,
        )

    async def callback(self, interaction: Interaction):
        await self.view.callback(interaction, self)


class TicTacToe(View):
    turn: Member

    def __init__(self, ctx: Context, opponent: Member):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.opponent = opponent
        self.turn = ctx.author
        for i in range(9):
            self.add_item(
                Button(
                    label="\u200b",
                    row=i // 3,
                    custom_id=f"board:{i}",
                )
            )

    async def edit_message(self, *args: str, mention: bool = True) -> Message:
        embed = Embed(
            description="\n> ".join(
                [f"**{self.ctx.author}** vs **{self.opponent}**", *args]
            )
        )
        return await self.message.edit(
            content=self.turn.mention if mention else None, embed=embed, view=self
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.turn:
            embed = Embed(description=f"It's {self.turn.mention}'s turn!")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        return interaction.user == self.turn

    async def callback(self, interaction: Interaction, button: Button):
        if not interaction.message:
            return

        await interaction.response.defer()
        button.label = "X" if self.turn == self.ctx.author else "O"
        button.style = (
            ButtonStyle.green if self.turn == self.ctx.author else ButtonStyle.red
        )
        button.disabled = True

        winner = await self.check_board()
        if winner:
            await self.disable_buttons()
            await self.edit_message(
                (
                    "Nobody won, it's a **tie**!"
                    if isinstance(winner, str)
                    else f"{winner.mention} won!"
                ),
                mention=False,
            )
            return self.stop()

        self.turn = self.opponent if self.turn == self.ctx.author else self.ctx.author
        await self.edit_message(
            f"`{'❌' if self.turn == self.ctx.author else '⭕'}` It's {self.turn.mention}'s turn"
        )

    async def check_board(self) -> Optional[Member | str]:
        board = [button.label for button in self.children]  # type: ignore
        winning_combinations = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            [0, 3, 6],
            [1, 4, 7],
            [2, 5, 8],
            [0, 4, 8],
            [2, 4, 6],
        ]

        return next(
            (
                self.ctx.author if board[combo[0]] == "X" else self.opponent
                for combo in winning_combinations
                if board[combo[0]] == board[combo[1]] == board[combo[2]] != "\u200b"
            ),
            "tie" if "\u200b" not in board else None,
        )

    async def start(self) -> Message:
        embed = Embed(
            description="\n> ".join(
                [
                    f"**{self.ctx.author}** vs **{self.opponent}**",
                    f"`{'❌' if self.turn == self.ctx.author else '⭕'}` It's {self.turn.mention}'s turn",
                ]
            ),
        )
        self.message = await self.ctx.send(
            content=self.turn.mention,
            embed=embed,
            view=self,
        )
        return self.message


class RPS(View):
    chosen: dict[Member | User, str]
    choices: dict[str, str] = {
        "rock": "🗿",
        "paper": "📰",
        "scissors": "✂️",
    }
    outcomes = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

    def __init__(self, ctx: Context):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.chosen = {}
        for custom_id, emoji in self.choices.items():
            self.add_item(
                Button(
                    emoji=emoji,
                    custom_id=custom_id,
                )
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.warn(f"This is {self.ctx.author.mention}'s interaction")
            return False
        return True

    async def callback(self, interaction: Interaction, button: Button):
        if not interaction.message:
            return

        await interaction.response.defer()
        bot_choice = random.choice(list(self.choices.keys()))
        player_choice = button.custom_id

        result, color = (
            ("You win!", config.Color.approve)
            if bot_choice == self.outcomes[player_choice]
            else (
                ("We're square!", config.Color.warn)
                if player_choice == bot_choice
                else ("You lose!", config.Color.deny)
            )
        )

        result_emoji = (
            self.choices[player_choice]
            if player_choice == bot_choice or bot_choice == self.outcomes[player_choice]
            else self.choices[bot_choice]
        )

        embed = Embed(
            description=f"You chose `{player_choice}`, and I chose `{bot_choice}`. {result} {result_emoji}",
            color=color,
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.message.edit(embed=embed, view=None)
        return self.stop()

    async def start(self) -> Message:
        embed = Embed(description="Choose your move!")
        self.message = await self.ctx.reply(
            embed=embed,
            view=self,
        )
        return self.message
