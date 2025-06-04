from typing import Optional
import discord


class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int, label: str):
        self.x = x
        self.y = y
        super().__init__(label=label, row=self.x)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        self.disabled = True

        if self.view.turn == "X":
            self.style = discord.ButtonStyle.red
            self.label = self.view.turn
            self.view.turn = "O"
            self.view.player = self.view.player2
            self.view.board[self.x][self.y] = self.view.X
        else:
            self.style = discord.ButtonStyle.green
            self.label = self.view.turn
            self.view.turn = "X"
            self.view.player = self.view.player1
            self.view.board[self.x][self.y] = self.view.O

        winner = self.view.check_winner()
        if winner:
            self.view.stop()
            if winner == self.view.X:
                await interaction.client.db.execute(
                    """INSERT INTO tictactoe (user_id, wins) VALUES($1, $2) 
                    ON CONFLICT(user_id) DO UPDATE SET wins = tictactoe.wins + excluded.wins""",
                    self.view.player1.id,
                    1,
                )
                await interaction.client.db.execute(
                    """INSERT INTO tictactoe (user_id, losses) VALUES($1, $2) 
                    ON CONFLICT(user_id) DO UPDATE SET losses = tictactoe.losses + excluded.losses""",
                    self.view.player2.id,
                    1,
                )
                return await interaction.response.edit_message(
                    content=f"{self.view.player1.mention} Won the game!",
                    view=self.view,
                    allowed_mentions=discord.AllowedMentions.none(),
                )

            elif winner == self.view.O:
                await interaction.client.db.execute(
                    """INSERT INTO tictactoe (user_id, wins) VALUES($1, $2) 
                    ON CONFLICT(user_id) DO UPDATE SET wins = tictactoe.wins + excluded.wins""",
                    self.view.player2.id,
                    1,
                )
                await interaction.client.db.execute(
                    """INSERT INTO tictactoe (user_id, losses) VALUES($1, $2) 
                    ON CONFLICT(user_id) DO UPDATE SET losses = tictactoe.losses + excluded.losses""",
                    self.view.player1.id,
                    1,
                )
                return await interaction.response.edit_message(
                    content=f"{self.view.player2.mention} Won the game!",
                    view=self.view,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            else:
                await interaction.client.db.execute(
                    """INSERT INTO tictactoe (user_id, ties) VALUES($1, $2) 
                    ON CONFLICT(user_id) DO UPDATE SET ties = tictactoe.ties + excluded.ties""",
                    self.view.player1.id,
                    1,
                )
                await interaction.client.db.execute(
                    """INSERT INTO tictactoe (user_id, ties) VALUES($1, $2) 
                    ON CONFLICT(user_id) DO UPDATE SET ties = tictactoe.ties + excluded.ties""",
                    self.view.player2.id,
                    1,
                )
                return await interaction.response.edit_message(
                    content="It's a tie", view=self.view
                )

        content = (
            f"⭕ {self.view.player1.mention}, your turn"
            if self.view.turn == "X"
            else f"⭕ {self.view.player2.mention}, your turn"
        )
        return await interaction.response.edit_message(
            content=content,
            view=self.view,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class TicTacToe(discord.ui.View):
    def __init__(
        self,
        player1: discord.Member,
        player2: discord.Member,
    ):
        self.player1 = player1
        self.player2 = player2
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        self.turn = "X"
        self.player = player1
        self.X = 1
        self.O = -1
        self.tie = 2
        self.stopped = False
        super().__init__()

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y, label="ã…¤"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.player.id:
            await interaction.fail(
                f"It is not your **turn** yet - waiting on {self.player.mention} rn!"
            )

        return interaction.user.id == self.player.id

    def check_winner(self) -> Optional[int]:
        if any([sum(s) == 3 for s in self.board]):  # checking if X won on a line
            return self.X

        if any([sum(s) == -3 for s in self.board]):  # checking if O won on a line
            return self.O

        value = sum([self.board[i][i] for i in range(3)])  # checking diagonals
        if value == 3:
            return self.X
        elif value == -3:
            return self.O

        value = sum(
            [self.board[i][2 - i] for i in range(3)]
        )  # checking the secondary diagonal
        if value == 3:
            return self.X
        elif value == -3:
            return self.O

        for i in range(3):  # checking columns
            val = 0
            for j in range(3):
                val += self.board[j][i]

            if val == 3:
                return self.X
            elif val == -3:
                return self.O

        if all([i != 0 for s in self.board for i in s]):  # checking for a tie
            return self.tie

        return None  # the game didn't end

    def stop(self):
        for child in filter(lambda c: not c.disabled, self.children):
            child.disabled = True

        self.stopped = True
        return super().stop()

    async def on_timeout(self):
        if not self.stopped:
            self.stop()
            await self.message.delete()
