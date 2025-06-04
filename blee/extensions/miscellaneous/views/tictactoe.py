import contextlib
from typing import Optional

import discord
from discord.ext import commands
from discord.ui import Button, View  # type: ignore


class TicTacToeButton(Button):
    def __init__(
        self, label: str, style: discord.ButtonStyle, row: int, custom_id: str
    ):
        super().__init__(label=label, style=style, row=row, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        await self.view.callback(interaction, self)


class TicTacToe(View):
    def __init__(self, ctx: commands.Context, member: discord.Member):
        super().__init__(timeout=30.0)  # Changed to 30 seconds
        self.ctx = ctx
        self.bot = ctx.bot
        self.message = None
        self.member = member
        self.turn = ctx.author
        self.winner = None

        # Create a 3x3 grid of empty buttons
        for i in range(9):
            self.add_item(
                TicTacToeButton(
                    label="⠀",  # Using a different empty character
                    style=discord.ButtonStyle.secondary,  # Changed to secondary style
                    row=i // 3,
                    custom_id=f"board:{i}",
                )
            )

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.turn.id:
            return True
        await interaction.warn(
            f"it is not your **turn** yet - waiting on {self.turn.mention}"
        )
        return False

    async def on_timeout(self):
        with contextlib.suppress(discord.HTTPException):
            await self.message.delete()
        self.stop()

    async def on_error(
        self, error: Exception, item: Button, interaction: discord.Interaction
    ):
        await self.ctx.warn(f"An error occurred while processing your action: {item}")
        self.stop()

    async def callback(self, interaction: discord.Interaction, button: TicTacToeButton):
        await interaction.response.defer()

        button.label = "X" if self.turn == self.ctx.author else "O"
        button.disabled = True
        button.style = (
            discord.ButtonStyle.danger
            if self.turn == self.ctx.author
            else discord.ButtonStyle.success
        )

        if winner := await self.check_win(interaction):
            await interaction.message.edit(
                content=f"**{self.ctx.author.name}** vs **{self.member.name}**\n\n{winner}",
                view=self,
            )
            self.stop()
            return

        self.turn = self.member if self.turn == self.ctx.author else self.ctx.author
        turn_symbol = "❌" if self.turn == self.ctx.author else "⭕"
        await interaction.message.edit(
            content=f"**{self.ctx.author.name}** vs **{self.member.name}**\n\n{turn_symbol} {self.turn.mention}, your turn.",
            view=self,
        )

    async def check_win(self, interaction: discord.Interaction):
        board = [button.label for button in self.children]
        if board[0] == board[1] == board[2] != "⠀":
            self.winner = self.ctx.author if board[0] == "X" else self.member
        elif board[3] == board[4] == board[5] != "⠀":
            self.winner = self.ctx.author if board[3] == "X" else self.member
        elif board[6] == board[7] == board[8] != "⠀":
            self.winner = self.ctx.author if board[6] == "X" else self.member
        elif board[0] == board[3] == board[6] != "⠀":
            self.winner = self.ctx.author if board[0] == "X" else self.member
        elif board[1] == board[4] == board[7] != "⠀":
            self.winner = self.ctx.author if board[1] == "X" else self.member
        elif board[2] == board[5] == board[8] != "⠀":
            self.winner = self.ctx.author if board[2] == "X" else self.member
        elif board[0] == board[4] == board[8] != "⠀":
            self.winner = self.ctx.author if board[0] == "X" else self.member
        elif board[2] == board[4] == board[6] != "⠀":
            self.winner = self.ctx.author if board[2] == "X" else self.member
        elif "⠀" not in board:
            self.winner = "tie"

        if self.winner:
            for child in self.children:
                child.disabled = True

            if self.winner != "tie":
                # Record win for winner
                await self.bot.db.execute(
                    """
                    INSERT INTO tictactoe_stats (user_id, wins, losses, games_played)
                    VALUES ($1, 1, 0, 1)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET wins = tictactoe_stats.wins + 1,
                        games_played = tictactoe_stats.games_played + 1
                """,
                    self.winner.id,
                )

                # Record loss for loser
                loser = self.ctx.author if self.winner == self.member else self.member
                await self.bot.db.execute(
                    """
                    INSERT INTO tictactoe_stats (user_id, wins, losses, games_played)
                    VALUES ($1, 0, 1, 1)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET losses = tictactoe_stats.losses + 1,
                        games_played = tictactoe_stats.games_played + 1
                """,
                    loser.id,
                )
            else:
                # Record tie for both players
                for player in (self.ctx.author, self.member):
                    await self.bot.db.execute(
                        """
                        INSERT INTO tictactoe_stats (user_id, wins, losses, games_played)
                        VALUES ($1, 0, 0, 1)
                        ON CONFLICT (user_id) DO UPDATE 
                        SET games_played = tictactoe_stats.games_played + 1
                    """,
                        player.id,
                    )

            return (
                f"🏅 {self.winner.mention} won!"
                if self.winner != "tie"
                else "It's a **tie**!"
            )
        return False

    async def start(self):
        """Start the TicTacToe game"""
        self.message = await self.ctx.send(
            f"**{self.ctx.author.name}** vs **{self.member.name}**\n\n:alarm_clock: You have **30 seconds** to start!\n❌ {self.turn.mention}, make your first move.",
            view=self,
        )


class LeaderboardView(discord.ui.View):
    def __init__(self, ctx: commands.Context, pages: list[discord.Embed]):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.pages = pages
        self.current_page = 0

    @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.pages[self.current_page])

    @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.pages[self.current_page])

    @discord.ui.button(label="⇅", style=discord.ButtonStyle.gray)
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(embed=self.pages[self.current_page])

    @discord.ui.button(label="✕", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.warn("This menu is not for you!")
            return False
        return True


class TicTacToeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tictactoe", aliases=["ttt"])
    async def tictactoe(self, ctx: commands.Context, member: discord.Member):
        """Play Tic-Tac-Toe with another member"""
        if member.bot:
            return await ctx.warn("You cannot play against bots!")
        if member == ctx.author:
            return await ctx.warn("You cannot play against yourself!")

        view = TicTacToe(ctx, member)
        await view.start()

    @commands.command(name="tictactoe_leaderboard", aliases=["ttlb", "tttop"])
    async def tictactoe_leaderboard(self, ctx: commands.Context):
        """Display the TicTacToe leaderboard"""

        # Fetch all players
        records = await self.bot.db.fetch(
            """
            SELECT 
                user_id,
                wins,
                games_played
            FROM tictactoe_stats 
            ORDER BY wins DESC
        """
        )

        if not records:
            return await ctx.warn("No TicTacToe games have been played yet!")

        # Create pages
        pages = []
        entries_per_page = 10

        for i in range(0, len(records), entries_per_page):
            page_records = records[i : i + entries_per_page]

            embed = discord.Embed(
                title="Most Tic-Tac-Toe wins", color=discord.Color.blurple()
            )

            description = []
            for idx, record in enumerate(page_records, 1 + i):
                user = self.bot.get_user(record["user_id"])
                username = user.name if user else f"Unknown user#{record['user_id']}"

                description.append(f"`{idx}` {username} - {record['wins']:,} wins")

            embed.description = "\n".join(description)
            embed.set_footer(
                text=f"Page {i//entries_per_page + 1}/{-(-len(records)//entries_per_page)} ({len(records)} entries)"
            )

            pages.append(embed)

        view = LeaderboardView(ctx, pages)
        await ctx.send(embed=pages[0], view=view)


async def setup(bot):
    await bot.add_cog(TicTacToeCog(bot))
