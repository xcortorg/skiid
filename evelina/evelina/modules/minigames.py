import io
import random
import discord
import asyncio

from datetime import datetime, timedelta

from discord import Interaction, ButtonStyle, Embed, Member, File, Color
from discord.ui import Button, View, button
from discord.errors import NotFound

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.helpers import EvelinaContext

class GameStatsManager:
    def __init__(self, bot: Evelina):
        self.bot = bot

    async def update_gamestats(self, win_player, loose_player, result, game):
        if isinstance(win_player, int):
            win_player = self.bot.get_user(win_player)
        if isinstance(loose_player, int):
            loose_player = self.bot.get_user(loose_player)
        if result == "win":
            if win_player is not None:
                await self.bot.db.execute("INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, 1, 0, 0) ON CONFLICT (user_id, game) DO UPDATE SET wins = gamestats.wins + 1, loses = COALESCE(gamestats.loses, 0), ties = COALESCE(gamestats.ties, 0)", win_player.id, game)
                if loose_player is not None:
                    await self.bot.db.execute("INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, 0, 1, 0) ON CONFLICT (user_id, game) DO UPDATE SET wins = COALESCE(gamestats.wins, 0), loses = gamestats.loses + 1, ties = COALESCE(gamestats.ties, 0)", loose_player.id, game)
            elif loose_player is not None:
                await self.bot.db.execute("INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, 0, 1, 0) ON CONFLICT (user_id, game) DO UPDATE SET wins = COALESCE(gamestats.wins, 0), loses = gamestats.loses + 1, ties = COALESCE(gamestats.ties, 0)", loose_player.id, game)
        elif result == "tie":
            if win_player is not None:
                await self.bot.db.execute("INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, 0, 0, 1) ON CONFLICT (user_id, game) DO UPDATE SET wins = COALESCE(gamestats.wins, 0), loses = COALESCE(gamestats.loses, 0), ties = gamestats.ties + 1", win_player.id, game)
            if loose_player is not None:
                await self.bot.db.execute("INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, 0, 0, 1) ON CONFLICT (user_id, game) DO UPDATE SET wins = COALESCE(gamestats.wins, 0), loses = COALESCE(gamestats.loses, 0), ties = gamestats.ties + 1", loose_player.id, game)

class TicTacToeButton(Button["TicTacToe"]):
    def __init__(self, x: int, y: int, player1: Member, player2: Member, game_manager: GameStatsManager, **kwargs):
        self.x = x
        self.y = y
        self.player1 = player1
        self.player2 = player2
        self.game_manager = game_manager
        super().__init__(style=ButtonStyle.secondary, label="\u200b", row=y, **kwargs)

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        view: 'TicTacToe' = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return
        if view.current_player == view.X:
            if interaction.user != self.player1:
                return await interaction.response.send_message("You can't interact with this button", ephemeral=True)
            self.style = ButtonStyle.danger
            self.label = "X"
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            content = f"{self.player1} ⚔️ {self.player2}\nIt's **{self.player2.name}**'s turn"
            result = "continue"
        else:
            if interaction.user != self.player2:
                return await interaction.response.send_message("You can't interact with this button", ephemeral=True)
            self.style = ButtonStyle.success
            self.label = "O"
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            content = f"{self.player1} ⚔️ {self.player2}\nIt's **{self.player1.name}'s** turn"
            result = "continue"
        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = f"{self.player1} ⚔️ {self.player2}\n**{self.player1.name}** won!"
                result = "win"
            elif winner == view.O:
                content = f"{self.player1} ⚔️ {self.player2}\n**{self.player2.name}** won!"
                result = "win"
            else:
                content = f"{self.player1} ⚔️ {self.player2}\nIt's a tie!"
                result = "tie"
            await self.game_manager.update_gamestats(self.player1.id, self.player2.id, result, game="tictactoe")
            for child in view.children:
                child.disabled = True
            view.stop()
        try:
            await interaction.response.edit_message(content=content, view=view)
        except NotFound:
            pass
        except Exception:
            pass
        await asyncio.sleep(0.5)

class TicTacToe(View):
    children: list[TicTacToeButton]
    X = -1
    O = 1
    Tie = 2

    def __init__(self, player1: Member, player2: Member, bot: Evelina):
        super().__init__(timeout=60)
        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        self.bot = bot
        game_manager = GameStatsManager(self.bot)
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y, player1, player2, game_manager))

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X
        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X
        if all(i != 0 for row in self.board for i in row):
            return self.Tie
        return None

class RockPaperScissors(View):
    def __init__(self, ctx: EvelinaContext, game_manager: GameStatsManager, opponent: Member = None):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.game_manager = game_manager
        self.opponent = opponent
        self.get_emoji = {"rock": "🪨", "paper": "📰", "scissors": "✂️"}
        self.choices = {}
        self.players = [ctx.author.id]
        self.message = None
        if opponent:
            self.players.append(opponent.id)

    async def disable_buttons(self):
        if self.message:
            await self.message.edit(view=None)

    async def interaction_check(self, interaction: Interaction):
        if self.opponent:
            if interaction.user.id not in self.players:
                await interaction.response.send_message("This game is not for you", ephemeral=True)
                return False
        else:
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("This game is not for you", ephemeral=True)
                return False
        return True

    async def action(self, interaction: Interaction, selection: str):
        self.choices[interaction.user.id] = selection
        if self.opponent:
            if len(self.choices) < 2:
                await interaction.response.defer()
                return
            player1_choice = self.choices[self.players[0]]
            player2_choice = self.choices[self.players[1]]
            def get_winner(choice1, choice2):
                if choice1 == choice2:
                    return None
                if (choice1 == "rock" and choice2 == "scissors") or \
                   (choice1 == "paper" and choice2 == "rock") or \
                   (choice1 == "scissors" and choice2 == "paper"):
                    return self.players[0]
                else:
                    return self.players[1]
            winner_id = get_winner(player1_choice, player2_choice)
            if winner_id is None:
                result_message = f"It's a tie! Both players chose {self.get_emoji.get(player1_choice)}"
                await self.game_manager.update_gamestats(None, None, "tie", "rockpaperscissors")
            else:
                winner_user = next(user for user in self.players if user == winner_id)
                loser_user = next(user for user in self.players if user != winner_id)
                result_message = f"<@{self.players[0]}>: {self.get_emoji.get(player1_choice)} vs <@{self.players[1]}>: {self.get_emoji.get(player2_choice)}\n> <@{winner_user}> wins!"
                await self.game_manager.update_gamestats(winner_user, loser_user, "win", "rockpaperscissors")
        else:
            bot_selection = random.choice(["rock", "paper", "scissors"])
            def get_winner():
                if selection == bot_selection:
                    return None
                if (selection == "rock" and bot_selection == "scissors") or \
                   (selection == "paper" and bot_selection == "rock") or \
                   (selection == "scissors" and bot_selection == "paper"):
                    return interaction.user.id
                else:
                    return interaction.client.user.id
            winner_id = get_winner()
            if winner_id is None:
                result_message = f"It's a tie! Both players chose {self.get_emoji.get(selection)}"
                await self.game_manager.update_gamestats(interaction.user, None, "tie", "rockpaperscissors")
            elif winner_id == interaction.user.id:
                result_message = f"You win! You chose {self.get_emoji.get(selection)} and the bot chose {self.get_emoji.get(bot_selection)}."
                await self.game_manager.update_gamestats(interaction.user, None, "win", "rockpaperscissors")
            else:
                result_message = f"The bot wins! You chose {self.get_emoji.get(selection)}, the bot chose {self.get_emoji.get(bot_selection)}."
                await self.game_manager.update_gamestats(None, interaction.user, "win", "rockpaperscissors")
        await interaction.response.edit_message(embed=Embed(color=colors.NEUTRAL, title="Match result", description=result_message))
        await self.disable_buttons()

    @button(emoji="🪨")
    async def rock(self, interaction: Interaction, button: Button):
        return await self.action(interaction, "rock")

    @button(emoji="📰")
    async def paper(self, interaction: Interaction, button: Button):
        return await self.action(interaction, "paper")

    @button(emoji="✂️")
    async def scissors(self, interaction: Interaction, button: Button):
        return await self.action(interaction, "scissors")

    async def on_timeout(self):
        if self.message:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} <@{self.players[0]}>: The game has expired due to inactivity")
            await self.message.edit(embed=embed, view=None)

class BlackTea:
    def __init__(self, bot, game_manager: GameStatsManager):
        self.bot = bot
        self.game_manager = game_manager
        self.emoji = "🍵"
        self.lifes = {}
        self.players = {}
        self.lock = asyncio.Lock()
        self.game_active = False
        self.player_locks = {}

    def get_string(self):
        words = self.get_words()
        word = random.choice([l for l in words if len(l) > 3])
        return word[:3].lower()

    async def remove_stuff(self, guild_id: int):
        await self.bot.cache.delete(f"MatchStart_{guild_id}")
        async with self.lock:
            if guild_id in self.players:
                del self.players[guild_id]
            if guild_id in self.lifes:
                del self.lifes[guild_id]
            if guild_id in self.player_locks:
                del self.player_locks[guild_id]
            self.game_active = False

    async def lost_a_life(self, member: int, reason: str, ctx: EvelinaContext):
        async with self.lock:
            guild_id = ctx.guild.id
            if guild_id not in self.lifes:
                return
            if member not in self.lifes[guild_id]:
                return
            self.lifes[guild_id][member] += 1
            remaining_lifes = 3 - self.lifes[guild_id][member]
            if reason == "timeout":
                embed = self.create_embed(f"Time is up! You have **{remaining_lifes}** lifes left!", emoji="⏰", color=colors.ERROR)
                await ctx.send(embed=embed)
            elif reason == "wrong":
                embed = self.create_embed(f"Wrong answer! You have **{remaining_lifes}** lifes left!", emoji="💥", color=colors.ERROR)
                await ctx.send(embed=embed)
            if self.lifes[guild_id][member] == 3:
                await ctx.send(embed=Embed(color=colors.ERROR, description=f"☠️ <@{member}> You're eliminated!"))
                await self.add_loser(member)
                del self.lifes[guild_id][member]
                if member in self.players.get(guild_id, []):
                    self.players[guild_id].remove(member)
                if len(self.players.get(guild_id, [])) == 1:
                    winner = self.players[guild_id][0]
                    await self.add_winner(winner)
                    await ctx.send(
                        embed=Embed(color=colors.WARNING, description=f"🥇 <@{winner}> Won the game!"))
                    await self.remove_stuff(guild_id)
                    self.game_active = False
                    return

    def get_words(self):
        with open("./data/wordlist.txt", encoding="utf-8") as data:
            return data.read().splitlines()

    async def add_loser(self, player: int):
        await self.game_manager.update_gamestats(None, player, "win", "blacktea")

    async def add_winner(self, player: int):
        await self.game_manager.update_gamestats(player, None, "win", "blacktea")

    async def start_blacktea_game(self, ctx: EvelinaContext):
        async with self.lock:
            self.game_active = True
        embed = Embed(color=colors.BLACKTEA, title="BlackTea Matchmaking")
        embed.add_field(
            name="Guide",
            value=f"React with `{self.emoji}` to join the round."
            "\n> You have 20 seconds to join"
            "\n> The game starts only if there are at least 2 joined players"
            "\n> Everyone has 3 lifes"
            "\n> Think about a word that starts with the specific letters given",
        )
        mes = await ctx.send(embed=embed)
        await mes.add_reaction(self.emoji)
        await asyncio.sleep(20)
        try:
            newmes = await ctx.channel.fetch_message(mes.id)
        except Exception as e:
            await self.remove_stuff(ctx.guild.id)
            return await ctx.send_warning(f"The blacktea message was deleted or an error occurred: {str(e)}")
        if not newmes.reactions or newmes.reactions[0].count <= 1:
            await self.remove_stuff(ctx.guild.id)
            return await ctx.send_warning("Reactions got removed from the message, canceling the match.. 😓")
        users = [u.id async for u in newmes.reactions[0].users() if u.id != self.bot.user.id]
        if len(users) < 2:
            await self.remove_stuff(ctx.guild.id)
            return await ctx.send_warning("Not enough players to start the blacktea match... 😓")
        async with self.lock:
            self.players[ctx.guild.id] = users
            self.lifes[ctx.guild.id] = {user: 0 for user in users}
            self.player_locks[ctx.guild.id] = {user: asyncio.Lock() for user in users}
        while self.game_active:
            for i, user in enumerate(users):
                async with self.player_locks[ctx.guild.id].get(user, asyncio.Lock()):
                    rand = self.get_string()
                    timestamp = int((datetime.now() + timedelta(seconds=10)).timestamp())
                    embed = self.create_embed(f"Say a word containing **`{rand}`**\n> Time ends <t:{timestamp}:R>", emoji="🍵", user_mention=f"<@{user}>")
                    await ctx.send(content=f"<@{user}>", embed=embed)
                    try:
                        message = await self.bot.wait_for("message", check=lambda m: m.channel.id == ctx.channel.id and m.author.id == user, timeout=10)
                        user_input = message.content.lower()
                        if rand in user_input and user_input in self.get_words():
                            await message.add_reaction("✅")
                        else:
                            await self.lost_a_life(user, "wrong", ctx)
                    except asyncio.TimeoutError:
                        await self.lost_a_life(user, "timeout", ctx)
                    except Exception as e:
                        await ctx.send(f"An unexpected error occurred: {str(e)}")
                    if not self.game_active:
                        break
            if not self.game_active:
                break
        await self.remove_stuff(ctx.guild.id)

    def create_embed(self, description: str, emoji: str = "", user_mention: str = "", color: str = None,) -> Embed:
        embed_description = (f"{emoji} {user_mention}: {description}" if user_mention else f"{emoji} {description}")
        embed = Embed(color=color if color else colors.BLACKTEA, description=embed_description)
        return embed