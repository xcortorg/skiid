import io
import os
import re
import string
import aiohttp
import requests
import random
import discord
import asyncio
import datetime

from discord import Embed, Member, User, Message, File, TextChannel
from discord.utils import get
from discord.ext.commands import Cog, BucketType, Author, command, group, cooldown, has_guild_permissions

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageSequence, UnidentifiedImageError
from typing import Optional, Union

from modules import config
from modules.styles import emojis, colors
from modules.helpers import EvelinaContext
from modules.evelinabot import Evelina
from modules.minigames import GameStatsManager, BlackTea, RockPaperScissors, TicTacToe

class Fun(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.active_games = {}

    def calculate_KD(self, wins: int, loses: int) -> float:
        if loses == 0:
            return wins
        kd_ratio = wins / loses
        kd_ratio = round(kd_ratio, 2)
        return kd_ratio

    async def stats_execute(self, ctx: EvelinaContext, user: User) -> Message:
        check = await self.bot.db.fetchrow("SELECT * FROM gamestats WHERE game = $1 AND user_id = $2", ctx.command.name, user.id)
        if not check:
            return await ctx.send_warning("There are no stats recorded for this member")
        kd_ratio = self.calculate_KD(check['wins'], check['loses'])
        kd_ratio = f"{kd_ratio:.2f} KD"
        embed = Embed(color=colors.NEUTRAL, title=f"Stats for {ctx.command.name}").set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.add_field(name="Wins", value=f"> {check['wins']}", inline=True)
        embed.add_field(name="Loses", value=f"> {check['loses']}", inline=True)
        embed.add_field(name="Ties", value=f"> {check['ties']}", inline=True)
        embed.add_field(name="Total", value=f"> {check['wins'] + check['loses'] + check['ties']}", inline=True)
        embed.add_field(name="K/D Ratio", value=f"> {kd_ratio}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        return await ctx.reply(embed=embed)

    async def stats_leaderboard_execute(self, ctx: EvelinaContext, game: str):
        alias_command_mapping = {alias: command.name for command in ctx.bot.commands for alias in command.aliases}
        game_name = game.lower()
        game_name = alias_command_mapping.get(game_name, game_name)
        check = await self.bot.db.fetch("SELECT * FROM gamestats WHERE game = $1 ORDER BY wins DESC", game_name)
        if not check:
            return await ctx.send_warning("There are no stats recorded for this game.\n> If you are using a custom alias, try the normal command.")
        total_entries = len(check)
        pages = (total_entries + 9) // 9
        embeds = []
        for page in range(pages):
            embed = Embed(color=colors.NEUTRAL, title=f"Leaderboard for {game_name}").set_author(name=ctx.me.name, icon_url=ctx.me.avatar.url)
            for index in range(page * 9, min((page + 1) * 9, total_entries)):
                row = check[index]
                user = self.bot.get_user(row["user_id"])
                kd_ratio = self.calculate_KD(row['wins'], row['loses'])
                kd_ratio = f"{kd_ratio:.2f} KD"
                embed.add_field(
                    name=f"`{index + 1}.` {user}",
                    value=f"**Wins:** {row['wins']}・**Loses:** {row['loses']}・{kd_ratio}",
                    inline=True,
                )
            embed.set_footer(text=f"Page {page + 1}/{pages}・({total_entries} entries)")
            embeds.append(embed)
        return await ctx.paginator(embeds)

    def shorten(self, value: str, length: int = 32):
        if len(value) > length:
            value = value[: length - 2] + ("..." if len(value) > length else "").strip()
        return value

    @group(name="blacktea", aliases=["bt"], invoke_without_command=True, case_insensitive=True)
    async def blacktea(self, ctx: EvelinaContext):
        """Play blacktea with the server members"""
        if await self.bot.cache.get(f"MatchStart_{ctx.guild.id}"):
            return await ctx.send_warning("There is **already** a blacktea game **in progress**")
        await self.bot.cache.set(f"MatchStart_{ctx.guild.id}", 'started', expiration=900)
        game_manager = GameStatsManager(self.bot)
        blacktea_instance = BlackTea(self.bot, game_manager)
        await self.bot.cache.set(f"blacktea_game_{ctx.guild.id}", blacktea_instance, 900)
        await blacktea_instance.start_blacktea_game(ctx)

    @blacktea.command(name="end", aliases=["stop"])
    async def blacktea_end(self, ctx: EvelinaContext):
        """End the blacktea game"""
        blacktea_instance = await self.bot.cache.get(f"blacktea_game_{ctx.guild.id}")
        match_start_key = await self.bot.cache.get(f"MatchStart_{ctx.guild.id}")
        if blacktea_instance:
            blacktea_instance.game_active = False
            await blacktea_instance.remove_stuff(ctx.guild.id)
            await self.bot.cache.delete(f"blacktea_game_{ctx.guild.id}")
            await ctx.send_success("The blacktea game has been **forcefully** ended.")
        elif match_start_key:
            await self.bot.cache.delete(f"MatchStart_{ctx.guild.id}")
            await ctx.send_success("The match cache has been cleared")
        else:
            await ctx.send_warning("No blacktea game is currently running.")

    @command(name="rockpaperscissors", aliases=["rps"], usage="rockpaperscissors comminate", description="Play rock-paper-scissors with a member or the bot")
    async def rockpaperscissors(self, ctx: EvelinaContext, opponent: discord.Member = None):
        if opponent is None:
            embed = Embed(color=colors.NEUTRAL, title="Rock Paper Scissors!", description="You challenged the bot to a game! Click a button to make your choice!")
        else:
            if opponent.bot:
                return await ctx.send_warning("You can't play against a bot")
            if opponent.id == ctx.author.id:
                return await ctx.send_warning("You can't play against yourself")
            embed = Embed(color=colors.NEUTRAL, title="Rock Paper Scissors!", description=f"{ctx.author.mention} has challenged {opponent.mention} to a game! Both players, click a button to make your choice!")
        game_manager = GameStatsManager(self.bot)
        view = RockPaperScissors(ctx, game_manager, opponent)
        game_message = await ctx.reply(embed=embed, view=view)
        view.message = game_message

    @command(name="tictactoe", aliases=["ttt"], usage="tictactoe comminate", description="Play tictactoe with a member")
    async def tictactoe(self, ctx: EvelinaContext, *, member: Member):
        if member.id == ctx.author.id:
            return await ctx.send_warning("You can't play against yourself")
        if member.bot:
            return await ctx.send_warning("You can't play against a bot")
        view = TicTacToe(ctx.author, member, self.bot)
        view.message = await ctx.send(content=f"{ctx.author} ⚔️ {member}\n\nIt's {ctx.author.name}'s turn", view=view)

    @command(name="flags", usage="flags easy solo", description="Rate your knowledge of flags")
    async def flags(self, ctx: EvelinaContext, difficulty: str = "easy", mode: str = "solo"):
        if ctx.author.id in self.active_games:
            await ctx.send_warning("You are already in a game!")
            return
        self.active_games[ctx.author.id] = True
        async with aiohttp.ClientSession() as session:
            async with session.get('https://cdn.evelina.bot/flags.json') as resp:
                if resp.status == 200:
                    data = await resp.json()
                else:
                    await ctx.send_warning("Couldn't fetch country data.")
                    self.active_games.pop(ctx.author.id, None)
                    return

            european_countries = [
                'al', 'ad', 'am', 'at', 'az', 'by', 'be', 'ba', 'bg', 'hr', 
                'cy', 'cz', 'dk', 'ee', 'fi', 'fr', 'ge', 'de', 'gr', 'hu', 
                'is', 'ie', 'it', 'kz', 'xk', 'lv', 'li', 'lt', 'lu', 'mt', 
                'md', 'mc', 'me', 'nl', 'mk', 'no', 'pl', 'pt', 'ro', 'ru', 
                'sm', 'rs', 'sk', 'si', 'es', 'se', 'ch', 'tr', 'ua', 'gb', 
                'va'
            ]
            un_countries = [
                'af', 'al', 'dz', 'ad', 'ao', 'ag', 'ar', 'am', 'au', 'at',
                'az', 'bs', 'bh', 'bd', 'bb', 'by', 'be', 'bz', 'bj', 'bt',
                'bo', 'ba', 'bw', 'br', 'bn', 'bg', 'bf', 'bi', 'cv', 'kh',
                'cm', 'ca', 'cf', 'td', 'cl', 'cn', 'co', 'km', 'cg', 'cd',
                'cr', 'ci', 'hr', 'cu', 'cy', 'cz', 'dk', 'dj', 'dm', 'do',
                'ec', 'eg', 'sv', 'gq', 'er', 'ee', 'sz', 'et', 'fj', 'fi',
                'fr', 'ga', 'gm', 'ge', 'de', 'gh', 'gr', 'gd', 'gt', 'gn',
                'gw', 'gy', 'ht', 'hn', 'hu', 'is', 'in', 'id', 'ir', 'iq',
                'ie', 'il', 'it', 'jm', 'jp', 'jo', 'kz', 'ke', 'ki', 'kp',
                'kr', 'kw', 'kg', 'la', 'lv', 'lb', 'ls', 'lr', 'ly', 'li',
                'lt', 'lu', 'mg', 'mw', 'my', 'mv', 'ml', 'mt', 'mh', 'mr',
                'mu', 'mx', 'fm', 'md', 'mc', 'mn', 'me', 'ma', 'mz', 'mm',
                'na', 'nr', 'np', 'nl', 'nz', 'ni', 'ne', 'ng', 'no', 'om',
                'pk', 'pw', 'pa', 'pg', 'py', 'pe', 'ph', 'pl', 'pt', 'qa',
                'ro', 'ru', 'rw', 'kn', 'lc', 'vc', 'ws', 'sm', 'st', 'sa',
                'sn', 'rs', 'sc', 'sl', 'sg', 'sk', 'si', 'sb', 'so', 'za',
                'ss', 'es', 'lk', 'sd', 'sr', 'se', 'ch', 'sy', 'tw', 'tj',
                'tz', 'th', 'tl', 'tg', 'to', 'tt', 'tn', 'tr', 'tm', 'tv',
                'ug', 'ua', 'ae', 'gb', 'us', 'uy', 'uz', 'vu', 've', 'vn',
                'ye', 'zm', 'zw'
            ]

            if difficulty == "easy":
                selected_countries = {k: v for k, v in data.items() if k in european_countries}
                points = 1
            elif difficulty == "hard":
                selected_countries = {k: v for k, v in data.items() if k in european_countries or k in un_countries}
                points = 2
            elif difficulty == "extreme":
                selected_countries = data
                points = 3
            else:
                await ctx.send_warning("Invalid difficulty level. Choose from `easy`, `hard`, `extreme`")
                self.active_games.pop(ctx.author.id, None)
                return
            
            country_code, country_name = random.choice(list(selected_countries.items()))
            flag_url = f"https://flagcdn.com/256x192/{country_code}.png"
            async with session.get(flag_url) as img_resp:
                if img_resp.status == 200:
                    image_data = await img_resp.read()
                    os.makedirs("data/images/tmp", exist_ok=True)
                    with open(f"data/images/tmp/{country_code}.png", "wb") as f:
                        f.write(image_data)
                else:
                    await ctx.send_warning("Couldn't download the flag image.")
                    self.active_games.pop(ctx.author.id, None)
                    return

        embed = Embed(color=colors.NEUTRAL, title=f"Guess the Flag ({str(difficulty).capitalize()})", description="What country does this flag belong to?\n> Type `cancel` to surrender")
        file = discord.File(f"data/images/tmp/{country_code}.png", filename="flag.png")
        embed.set_thumbnail(url="attachment://flag.png")
        embed.set_footer(icon_url="http://cdn.evelina.bot/flag.png", text=f'Time: 10 Seconds ・ Difficulties: "easy", "hard", "extreme"')
        await ctx.send(embed=embed, file=file)

        def check(m):
            if mode == "solo":
                return m.author == ctx.author and m.channel == ctx.channel
            else:
                return m.channel == ctx.channel

        attempts_per_user = {}
        max_attempts = 5

        try:
            while True:
                guess = await self.bot.wait_for('message', timeout=10.0, check=check)

                if guess.content.lower() == "cancel":
                    await ctx.send_warning(f'Game cancelled! The correct answer was **{country_name}**.')
                    await self.bot.db.execute("INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, 0, $3, 0) ON CONFLICT (user_id, game) DO UPDATE SET loses = gamestats.loses + $3", ctx.author.id, "flags", points)
                    break

                user_attempts = attempts_per_user.get(guess.author.id, 0)

                if user_attempts < max_attempts:
                    if guess.content.lower() == country_name.lower():
                        await guess.add_reaction('✅')
                        await ctx.send_success(f'Correct! It is **{country_name}**')
                        await self.bot.db.execute(
                            "INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, $3, 0, 0) "
                            "ON CONFLICT (user_id, game) DO UPDATE SET wins = gamestats.wins + $3",
                            guess.author.id, "flags", points
                        )
                        break
                    else:
                        await guess.add_reaction('❌')
                        attempts_per_user[guess.author.id] = user_attempts + 1
                        remaining_attempts = max_attempts - attempts_per_user[guess.author.id]
                        if remaining_attempts > 0:
                            await ctx.send_warning(f"Incorrect! **{guess.author.display_name}** has **{remaining_attempts} attempts** left")
                        else:
                            await ctx.send_warning(f"**{guess.author.display_name}** has used all attempts!")

                if all(attempts >= max_attempts for attempts in attempts_per_user.values()):
                    await ctx.cooldown_send(f'All players have used their attempts! The correct answer was **{country_name}**')
                    await self.bot.db.execute("INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, 0, $3, 0) ON CONFLICT (user_id, game) DO UPDATE SET loses = gamestats.loses + $3", ctx.author.id, "flags", points)
                    break
        except asyncio.TimeoutError:
            await ctx.cooldown_send(f'Time out! The correct answer was **{country_name}**')
            await self.bot.db.execute("INSERT INTO gamestats (user_id, game, wins, loses, ties) VALUES ($1, $2, 0, $3, 0) ON CONFLICT (user_id, game) DO UPDATE SET loses = gamestats.loses + $3", ctx.author.id, "flags", points)
        finally:
            self.active_games.pop(ctx.author.id, None)
            os.remove(f"data/images/tmp/{country_code}.png")

    @group(name="guessthenumner", aliases=["gtn"], description="Guess the number game", invoke_without_command=True, case_insensitive=True)
    async def guessthenumber(self, ctx: EvelinaContext):
        return await ctx.create_pages()
    
    @guessthenumber.command(name="start", usage="guessthenumber start #number 1 200", description="Start a guess the number game")
    @has_guild_permissions(manage_channels=True)
    async def guessthenumber_start(self, ctx: EvelinaContext, channel: TextChannel, min: int, max: int):
        if min > max:
            return await ctx.send_warning("The minimum number cannot be higher than the maximum number")
        check = await self.bot.db.fetchrow("SELECT * FROM guessthenumber WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if check:
            return await ctx.send_warning("There is already a guess the number game in this channel")
        number = random.randint(min, max)
        embed = Embed(color=colors.NEUTRAL, title="Guess the Number", description=f"Guess a number between **{min}** and **{max}**")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Game started by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await channel.send(embed=embed)
        await self.bot.db.execute("INSERT INTO guessthenumber (guild_id, channel_id, number) VALUES ($1, $2, $3)", ctx.guild.id, channel.id, number)
        try:
            await ctx.author.send(embed=Embed(color=colors.NEUTRAL, description=f"Guess the number game started in {channel.mention}, the number is **{number}**"))
        except Exception:
            pass
        return await ctx.send_success(f"Guess the number game started in {channel.mention}")
    
    @guessthenumber.command(name="stop", usage="gessthenumber stop #number", description="Stop the guess the number game")
    @has_guild_permissions(manage_channels=True)
    async def guessthenumber_stop(self, ctx: EvelinaContext, channel: TextChannel):
        check = await self.bot.db.fetchrow("SELECT * FROM guessthenumber WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if not check:
            return await ctx.send_warning("There is no guess the number game in this channel")
        embed = Embed(color=colors.NEUTRAL, title="Guess the Number", description="The game has been stopped")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Game stopped by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await channel.send(embed=embed)
        await self.bot.db.execute("DELETE FROM guessthenumber WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Guess the number game stopped in {channel.mention}")
    
    @guessthenumber.command(name="list", description="List all guess the number games")
    @has_guild_permissions(manage_channels=True)
    async def guessthenumber_list(self, ctx: EvelinaContext):
        check = await self.bot.db.fetch("SELECT * FROM guessthenumber WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There are no guess the number games in this server")
        content = []
        for entry in check:
            content.append(f"{self.bot.misc.humanize_channel(entry['channel_id'])} - {entry['number']}")
        if not content:
            return await ctx.send_warning("There are no guess the number games in this server")
        return await ctx.paginate(content, f"Guess the Number - Games", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})

    @guessthenumber.command(name="lock", usage="guessthenumber lock on", description="Change the lock status of the game")
    @has_guild_permissions(manage_channels=True)
    async def guessthenumber_lock(self, ctx: EvelinaContext, mode: str):
        if mode.lower() not in ["on", "off"]:
            return await ctx.send_warning("Invalid mode. Choose from `on` or `off`")
        check = await self.bot.db.fetchrow("SELECT * FROM guessthenumber_settings WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await self.bot.db.execute("INSERT INTO guessthenumber_settings (guild_id, lock) VALUES ($1, $2)", ctx.guild.id, True if mode.lower() == "on" else False)
        else:
            await self.bot.db.execute("UPDATE guessthenumber_settings SET lock = $1 WHERE guild_id = $2", True if mode.lower() == "on" else False, ctx.guild.id)
        if mode.lower() == "on":
            return await ctx.send_success("Guess the number games will be locked after a win")
        else:
            return await ctx.send_success("Guess the number games will not be locked after a win")

    @group(name="counting", description="Counting game commands", invoke_without_command=True, case_insensitive=True)
    async def counting(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @counting.command(name="set", usage="counting set #channel", description="Set the counting channel")
    @has_guild_permissions(manage_channels=True)
    async def counting_set(self, ctx: EvelinaContext, channel: TextChannel):
        counter_data = await self.bot.db.fetchrow("SELECT channel_id FROM number_counter WHERE guild_id = $1", ctx.guild.id)
        if counter_data:
            await self.bot.db.execute("UPDATE number_counter SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
            return await ctx.send_success(f"Counter channel has been updated to {channel.mention}")
        else:
            await self.bot.db.execute("INSERT INTO number_counter (guild_id, channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)
            return await ctx.send_success(f"Counter channel has been set to {channel.mention}")
        
    @counting.command(name="remove", description="Remove the counting channel")
    @has_guild_permissions(manage_channels=True)
    async def counting_remove(self, ctx: EvelinaContext):
        counter_data = await self.bot.db.fetchrow("SELECT channel_id FROM number_counter WHERE guild_id = $1", ctx.guild.id)
        if not counter_data:
            return await ctx.send_warning("Counter channel is not set")
        await self.bot.db.execute("DELETE FROM number_counter WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Counter channel has been removed")
    
    @counting.command(name="safemode", usage="counting safemode on", description="Enable or disable safe mode for the counting game")
    @has_guild_permissions(manage_channels=True)
    async def counting_safemode(self, ctx: EvelinaContext, mode: str):
        if mode.lower() not in ["on", "off"]:
            return await ctx.send_warning("Invalid mode. Choose from `on` or `off`")
        counter_data = await self.bot.db.fetchrow("SELECT * FROM number_counter WHERE guild_id = $1", ctx.guild.id)
        if not counter_data:
            return await ctx.send_warning("Counter channel is not set")
        if counter_data['current_number'] != 1:
            return await ctx.send_warning("Safe mode can only be changed when the current number is 1")
        if mode.lower() == "on":
            await self.bot.db.execute("UPDATE number_counter SET safemode = TRUE WHERE guild_id = $1", ctx.guild.id)
            return await ctx.send_success("Safe mode has been enabled")
        else:
            await self.bot.db.execute("UPDATE number_counter SET safemode = FALSE WHERE guild_id = $1", ctx.guild.id)
            return await ctx.send_success("Safe mode has been disabled")
    
    @counting.command(name="leaderboard", aliases=["lb", "top"], description="Displays the highest number counts across servers")
    async def counting_leaderboard(self, ctx: EvelinaContext):
        leaderboard_data = await self.bot.db.fetch("SELECT guild_id, highest_count FROM number_counter WHERE highest_count > 1 ORDER BY highest_count DESC")
        if not leaderboard_data:
            await ctx.send_warning("No data found for counting leaderboard")
            return
        content = []
        for entry in leaderboard_data:
            guild = self.bot.get_guild(entry["guild_id"])
            if guild:
                content.append(f"**{guild.name}** - {entry['highest_count']}")
        if not content:
            await ctx.send_warning("No data found for counting leaderboard")
            return
        await ctx.paginate(content, f"Counting Leaderboard", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})

    @group(name="stats", description="Check a member's stats for a certain game", invoke_without_command=True, case_insensitive=True)
    async def stats(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @stats.command(name="tictactoe", aliases=["ttt"], usage="stats tictactoe comminate", description="View a member's stats for tictactoe")
    async def stats_ttt(self, ctx: EvelinaContext, *, user: User = Author):
        await self.stats_execute(ctx, user)

    @stats.command(name="blacktea", aliases=["bt"], usage="stats blacktea comminate", description="View a member's stats for blacktea")
    async def stats_blacktea(self, ctx: EvelinaContext, *, user: User = Author):
        await self.stats_execute(ctx, user)

    @stats.command(name="rockpaperscissors", aliases=["rps"], usage="stats rockpaperscissors comminate", description="View a member's stats for rockpaperscissors")
    async def stats_rps(self, ctx: EvelinaContext, *, user: User = Author):
        await self.stats_execute(ctx, user)

    @stats.command(name="flags", usage="stats flags comminate", description="View a member's stats for flags")
    async def stats_flags(self, ctx: EvelinaContext, *, user: User = Author):
        await self.stats_execute(ctx, user)

    @stats.command(name="leaderboard", aliases=["lb"], usage="stats leaderboard blacktea", description="Get the leaderboard for a specific game")
    async def stats_leaderboard(self, ctx: EvelinaContext, game: str):
        await self.stats_leaderboard_execute(ctx, game)

    @command(name="quran", description="Get a random quran verse")
    async def quran(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/quran?key=X3pZmLq82VnHYTd6Cr9eAw")
        all_ayahs = []
        for surah in result['data']['surahs']:
            all_ayahs.extend(surah['ayahs'])
        ayah = random.choice(all_ayahs)
        surah = None
        for s in result['data']['surahs']:
            if ayah in s['ayahs']:
                surah = s
                break
        if not surah:
            return await ctx.send("Surah not found for this Ayah.")
        embed = Embed(color=colors.NEUTRAL, description=f"**{surah['number']}:{ayah['numberInSurah']}** - **{surah['name']}** (`{surah['englishName']}`)\n {ayah['text']}")
        return await ctx.send(embed=embed)
    
    @command(name="bible", description="Get a random bible verse")
    async def bible(self, ctx: EvelinaContext):
        params = {"format": "json", "order": "random"}
        result = await self.bot.session.get_json("https://beta.ourmanna.com/api/v1/get", params=params)
        embed = Embed(color=colors.NEUTRAL, description=f"**{result['verse']['details']['reference']}**\n {result['verse']['details']['text']}")
        await ctx.send(embed=embed)

    @command(name="eightball", aliases=["8ball"], usage="8ball Are you gay?", description="Ask the 8ball a question")
    async def eightball(self, ctx: EvelinaContext, *, question: str):
        embed = Embed(color=colors.NEUTRAL, description=f"**Question:** {question}{'?' if not question.endswith('?') else ''}\n**Answer:** {random.choice(['yes', 'no', 'never', 'most likely', 'absolutely', 'absolutely not', 'of course not'])}")
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.reply(embed=embed)

    @command(name="choose", usage="choose Austria, Vienna, Italy", description="Choose between options")
    async def choose(self, ctx: EvelinaContext, *, choices: str):
        if len(choices := choices.split(", ")) == 1:
            return await ctx.send_warning(f"Not enough **choices** seperate your choices with a `,`")
        final = random.choice(choices).strip()
        return await ctx.evelina_send(f"Choosed **{final}**")
    
    @command(name="roll", usage="roll 1 20", description="Get a random number between the given range")
    async def roll(self, ctx: EvelinaContext, min: int, max: int):
        if min > max:
            return await ctx.send_warning("The minimum number cannot be higher than the maximum number")
        result = random.randint(min, max)
        return await ctx.evelina_send(f"🎲 You rolled **{result}**")

    @command(name="quickpoll", aliases=["poll", "qp"], usage="quickpoll Should we start a giveaway?", description="Create a quick poll")
    async def quickpoll(self, ctx: EvelinaContext, *, question: str):
        message = await ctx.reply(embed=Embed(color=colors.NEUTRAL, description=f"**Question:** {question}").set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else None))
        for m in ["👍", "👎"]:
            await message.add_reaction(m)

    @command(name="dog", description="Get a random dog image")
    async def dog(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/dog?key=X3pZmLq82VnHYTd6Cr9eAw")
        if isinstance(result, list):
            result = result[0]
        embed = Embed(color=colors.NEUTRAL)
        embed.set_image(url=result["url"])
        return await ctx.send(embed=embed)

    @command(name="cat", description="Get a random cat image")
    async def cat(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/cat?key=X3pZmLq82VnHYTd6Cr9eAw")
        if isinstance(result, list):
            result = result[0]
        if "url" not in result:
            return await ctx.send_warning("Failed to retrieve cat image.")
        embed = Embed(color=colors.NEUTRAL)
        embed.set_image(url=result["url"])
        return await ctx.send(embed=embed)

    @command(name="bird", description="Get a random bird image")
    async def bird(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/bird?key=X3pZmLq82VnHYTd6Cr9eAw")
        if isinstance(result, list):
            result = result[0]
        embed = Embed(color=colors.NEUTRAL)
        embed.set_image(url=result["file"])
        return await ctx.send(embed=embed)

    @command(name="capybara", description="Get a random capybara image")
    async def capybara(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/capybara?key=X3pZmLq82VnHYTd6Cr9eAw")
        if isinstance(result, list):
            result = result[0]
        embed = Embed(color=colors.NEUTRAL)
        embed.set_image(url=result["data"]["url"])
        return await ctx.send(embed=embed)
    
    @command(name="monkey", description="Get a random monkey image")
    async def monkey(self, ctx: EvelinaContext):
        result = await self.bot.session.get_bytes(f"https://www.placemonkeys.com/500/350?random")
        embed = Embed(color=colors.NEUTRAL)
        embed.set_image(url="attachment://monkey.png")
        with open("data/images/tmp/monkey.png", "wb") as f:
            f.write(result)
        file = File("data/images/tmp/monkey.png", filename="monkey.png")
        return await ctx.send(embed=embed, file=file)

    @command(name="meme", description="Get a random meme")
    async def meme(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/meme?key=X3pZmLq82VnHYTd6Cr9eAw")
        if isinstance(result, list):
            result = result[0]
        embed = Embed(color=colors.NEUTRAL)
        embed.set_image(url=result["url"])
        return await ctx.send(embed=embed)

    @command(name="dadjoke", aliases=["cringejoke"], description="Get a random dad joke")
    async def dadjoke(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/dadjoke?key=X3pZmLq82VnHYTd6Cr9eAw")
        return await ctx.evelina_send(f"{result['attachments'][0]['text']}")
    
    @command(name="advice", description="Get a random advice")
    async def advice(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/advice?key=X3pZmLq82VnHYTd6Cr9eAw")
        return await ctx.evelina_send(f"{result['slip']['advice']}")

    @command(name="uselessfact", aliases=["fact", "uf"], description="Get a random useless fact")
    async def uselessfact(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/uselessfact?key=X3pZmLq82VnHYTd6Cr9eAw")
        if isinstance(result, list):
            result = result[0]
        return await ctx.evelina_send(f"{result['text']}")
    
    @command(name="rizz", description="Get a random rizz")
    async def rizz(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/rizz?key=X3pZmLq82VnHYTd6Cr9eAw")
        if isinstance(result, list):
            result = result[0]
        return await ctx.evelina_send(f"{result['text']}")

    @command(name="gay", usage="gay comminate", description="Gay rate yourself or a given member")
    async def gay(self, ctx: EvelinaContext, *, member: Member = Author):
        a = 1
        b = 100
        if member.id in self.bot.owner_ids or member.id in [416328937891823616]:
            a = 0
            b = 0
        embed = Embed(color=colors.NEUTRAL, description=f"{member.mention} is **{random.randint(a, b)}%** gay 🏳️‍🌈")
        return await ctx.send(embed=embed)

    @command(name="furry", usage="furry comminate", description="Furry rate yourself or a given member")
    async def furry(self, ctx: EvelinaContext, *, member: Member = Author):
        a = 1
        b = 100
        if member.id in self.bot.owner_ids or member.id in [416328937891823616]:
            a = 0
            b = 0
        embed = Embed(color=colors.NEUTRAL, description=f"{member.mention} is **{random.randint(a, b)}%** a furry 🦊")
        return await ctx.send(embed=embed)

    @command(name="pp", usage="pp comminate", description="Check pp size from yourself or a given member")
    async def pp(self, ctx: EvelinaContext, *, member: Member = Author):
        a = 1
        b = 15
        if member.id in self.bot.owner_ids or member.id in [416328937891823616]:
            a = 15
            b = 30
        embed = Embed(color=colors.NEUTRAL, description=f"{member.mention}'s Penis\n8{'=' * random.randint(a, b)}D")
        return await ctx.send(embed=embed)

    @command(name="song", aliases=["music", "beat", "songinfo"], usage="song ufo361, allein", description="Get information about a song")
    async def song(self, ctx: EvelinaContext, *, title: str):
        headers = {"X-RapidAPI-Key": str(config.RAPIDAPI), "X-RapidAPI-Host": "genius-song-lyrics1.p.rapidapi.com"}
        query = {"q": title, "per_page": 1, "page": 1}
        response = await self.bot.session.get_json("https://genius-song-lyrics1.p.rapidapi.com/search/", headers=headers, params=query)
        if not response or not response.get("hits"):
            return await ctx.send_warning(f"No results found for **{title}**")
        info = response["hits"][0]["result"]
        try:
            thumbnail = info["song_art_image_url"]
        except Exception:
            thumbnail = None
        if info["stats"]["hot"] == True:
            hot = emojis.APPROVE
        else:
            hot = emojis.DENY
        if info["instrumental"] == True:
            instrumental = emojis.APPROVE
        else:
            instrumental = emojis.DENY
        embed = (
            discord.Embed(title=info["title"], url=info["url"], color=colors.NEUTRAL, timestamp=datetime.datetime.now())
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            .add_field(name="Artists", value=self.shorten(info["artist_names"], 50), inline=False)
            .add_field(name="Release Date", value=info["release_date_for_display"], inline=True)
            .add_field(name="Hot", value=hot, inline=True)
            .add_field(name="Instrumental", value=instrumental, inline=True)
            .set_footer(text=f"{int(info.get('stats', {}).get('pageviews', 0)):,} views")
            .set_thumbnail(url=thumbnail)
        )
        if rows := info["featured_artists"]:
            artists = []
            for row in rows:
                artists.append(row["name"])
            embed.add_field(name="More Artists", value=", ".join(artists))
        return await ctx.send(embed=embed)

    @group(name="vape", aliases=["juul"], description="Hit the vape", case_insensitive=True)
    async def vape(self, ctx: EvelinaContext):
        if ctx.invoked_subcommand is None and len(ctx.message.content.split()) == 1:
            return await self.vape_hit(ctx)
        elif ctx.invoked_subcommand is None:
            return await ctx.create_pages()

    @vape.command(name="hit", aliases=["smoke"], description="Hit the vape")
    @cooldown(1, 30, BucketType.member)
    async def vape_hit(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM vape WHERE guild_id = $1", ctx.guild.id)
        if (check and check["user_id"] != ctx.author.id and ctx.guild.get_member(check["user_id"])):
            return await ctx.send_warning(f"You don't have the **vape**! Steal it from {ctx.guild.get_member(check['user_id']).mention}")
        if check:
            await self.bot.db.execute("UPDATE vape SET hits = hits + 1 WHERE guild_id = $1", ctx.guild.id)
        else:
            await self.bot.db.execute("INSERT INTO vape VALUES ($1, $2, $3)", ctx.guild.id, ctx.author.id, 1)
        res = await self.bot.db.fetchrow("SELECT * FROM vape WHERE guild_id = $1", ctx.guild.id)
        embed = discord.Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Hit the **vape**! The server now has `{res['hits']}` hits", color=colors.SUCCESS)
        return await ctx.send(embed=embed)

    @vape.command(name="steal", aliases=["take"], description="Steal the vape from a member")
    @cooldown(1, 30, BucketType.guild)
    async def vape_steal(self, ctx: EvelinaContext):
        """Steal the vape from a member"""
        check = await self.bot.db.fetchrow("SELECT * FROM vape WHERE guild_id = $1", ctx.guild.id)
        if check is None:
            return await ctx.send_warning("No vape record found for this guild.")
        if check["user_id"] == ctx.author.id:
            return await ctx.send_warning("You already have the **vape**!")
        await self.bot.db.execute("UPDATE vape SET user_id = $1 WHERE guild_id = $2", ctx.author.id, ctx.guild.id)
        if ctx.guild.get_member(check["user_id"]):
            return await ctx.send_success(f"Stole the **vape** from {ctx.guild.get_member(check['user_id']).mention}")
        else:
            return await ctx.send_success(f"Found the **vape** somewhere and took it")

    @vape.command(name="hits", description="View the amount of hits in the server")
    async def vape_hits(self, ctx: EvelinaContext):
        result = await self.bot.db.fetchrow("SELECT * FROM vape WHERE guild_id = $1", ctx.guild.id)
        if not result:
            return await ctx.send_warning("There are no **vape hits** in this server")
        return await ctx.evelina_send(f"This server has `{result['hits']}` **vape hits**")
    
    @vape.command(name="leaderboard", aliases=["lb"], description="Global leaderboard for vape hits across all servers")
    async def vape_leaderboard(self, ctx: EvelinaContext):
        results = await self.bot.db.fetch("SELECT guild_id, hits FROM vape")
        if not results:
            return await ctx.send_warning("There are no **vape hits** recorded in any server.")
        sorted_results = sorted(results, key=lambda x: x["hits"], reverse=True)
        to_show = []
        for result in sorted_results:
            guild = self.bot.get_guild(result["guild_id"])
            if guild:
                to_show.append(f"**{guild.name}** has `{result['hits']}` vape hits")
        await ctx.paginate(to_show, f"Global Vape Leaderboard", {"name": ctx.author, "icon_url": ctx.author.avatar})
    
    @command(name="smoke", description="Hit the vape")
    @cooldown(1, 30, BucketType.member)
    async def smoke(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM smoke WHERE user_id = $1", ctx.author.id)
        loading_msg = await ctx.evelina_send(f"Hitting the **blunt**...")
        if check:
            await self.bot.db.execute("UPDATE smoke SET hits = hits + 1 WHERE user_id = $1", ctx.author.id)
        else:
            await self.bot.db.execute("INSERT INTO smoke VALUES ($1, $2)", ctx.author.id, 1)
        res = await self.bot.db.fetchrow("SELECT * FROM smoke WHERE user_id = $1", ctx.author.id)
        embed = discord.Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Took a hit from the blunt! You have `{res['hits']}` hits", color=colors.SUCCESS)
        await asyncio.sleep(random.randint(2, 5))
        try:
            return await loading_msg.edit(embed=embed)
        except discord.NotFound:
            return await ctx.send(embed=embed)
    
    @command(name="quote", usage="quote .../channels/... true", description="Create a quote out of a user's message")
    async def quote(self, ctx: EvelinaContext, message: discord.Message = None, bw: bool = False):
        """Create a quote out of a user's message"""
        if message is None:
            if ctx.message.reference is not None:
                try:
                    message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                except discord.NotFound:
                    await ctx.send_warning("The referenced message was not found.")
                    return
            else:
                await ctx.send_warning("Please provide a message or reply to a message.")
                return
        image_binary = await self.bot.misc.create_quote_image(
            message.author.display_avatar.url,
            message.content,
            bw=bw,
            name=message.author.name
        )
        quote_channel_id = await self.bot.db.fetchval("SELECT channel_id FROM quotes WHERE guild_id = $1", ctx.guild.id)
        quote_channel = ctx.guild.get_channel(quote_channel_id) if quote_channel_id else None
        if quote_channel:
            await quote_channel.send(file=discord.File(fp=image_binary, filename="quote.png"))
            await ctx.send_success(f"The quote has been sent to {quote_channel.mention}.")
        else:
            await ctx.send(file=discord.File(fp=image_binary, filename="quote.png"))
    
    @command(name="customquote", aliases=["cq"], usage="customquote comminate Hello world", description="Create a custom quote")
    async def customquote(self, ctx: EvelinaContext, user: User, *, text: str):
        image_binary = await self.bot.misc.create_quote_image(user.display_avatar.url, text, False, user.name)
        await ctx.send(file=discord.File(fp=image_binary, filename="quote.png"))
        try:
            return await ctx.message.delete()
        except Exception:
            pass
    
    @command(name="quotechannel", aliases=["qc"], usage="quotechannel #quotes", description="Create or remove a quote channel")
    async def quotechannel(self, ctx: EvelinaContext, *, channel: TextChannel = None):
        """Set or remove a default quote channel"""
        existing_entry = await self.bot.db.fetchval("SELECT channel_id FROM quotes WHERE guild_id = $1", ctx.guild.id)
        if channel is None:
            if existing_entry:
                await self.bot.db.execute("DELETE FROM quotes WHERE guild_id = $1", ctx.guild.id)
                return await ctx.send_success("Removed the default quote channel.")
            else:
                return await ctx.send_warning("This server does not have a quote channel set.")
        if existing_entry:
            await self.bot.db.execute("UPDATE quotes SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
            await ctx.send_success(f"Updated the default quote channel to {channel.mention}.")
        else:
            await self.bot.db.execute("INSERT INTO quotes (guild_id, channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)
            await ctx.send_success(f"Set {channel.mention} as the default quote channel.")
    
    @command(name="tweet", usage="tweet comminate Whats up?", description="Create a tweet")
    async def tweet(self, ctx: EvelinaContext, user: Optional[Member] = None, *, comment: str):
        if user is None:
            user = ctx.author
        displayname = user.display_name
        username = user.name
        avatar = user.avatar.url if user.avatar else user.default_avatar.url
        url = f"https://some-random-api.com/canvas/misc/tweet?username={username}&displayname={displayname}&avatar={avatar}&comment={comment}"
        response = await self.bot.session.get_bytes(url)
        if response:
            file = discord.File(io.BytesIO(response), filename='tweet.png')
            await ctx.send(file=file)
        else:
            await ctx.send_warning("Failed to create tweet image")

    @command(name="trueorfalse", aliases=["tof"], description="Check if a statement is true or false")
    async def trueorfalse(self, ctx: EvelinaContext):
        if ctx.message.reference is None:
            return await ctx.send_warning("You have to reply to a message to use this command")
        if ctx.message.reference.resolved.content is None:
            return await ctx.send_warning("You can't check if an empty message is true or false")
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.add_field(name="Statement", value=f"```{ctx.message.reference.resolved.content[:1024]}```", inline=False)
        embed.add_field(name="Author", value=ctx.message.reference.resolved.author.mention, inline=True)
        embed.add_field(name="Is it true?", value=random.choice([f'{emojis.APPROVE}', f'{emojis.DENY}']), inline=True)
        return await ctx.send(embed=embed)
    
    @group(name="media", description="Media commands", invoke_without_command=True, case_insensitive=True)
    async def media(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @media.command(name="jail", description="Apply a jail filter onto your photo")
    async def media_jail(self, ctx: EvelinaContext, image: Union[User, str] = None):
        if isinstance(image, User):
            url = image.avatar.url if image.avatar else image.default_avatar.url
        elif isinstance(image, str):
            url = image
        elif ctx.message.attachments:
            url = ctx.message.attachments[0].url
        elif ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.attachments:
                url = replied_message.attachments[0].url
            else:
                return await ctx.send_warning("Replied message doesn't have an attachment")
        else:
            return await ctx.send_warning("You must provide an image URL, mention a user, attach an image, or reply to a message with an attachment")
        response = await self.bot.session.get_bytes(url)
        if not response:
            return await ctx.send_warning("Failed to download the image. Please try again later...")
        data = BytesIO(response)
        code = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        input_path = f"/var/www/html/generation/{code}.png"
        with open(input_path, "wb") as f:
            f.write(data.getbuffer())
        url = f"https://{self.bot.transcript}/generation/{code}.png"
        response = await self.bot.session.get_bytes(f"https://some-random-api.com/canvas/overlay/jail?avatar={url}")
        if not response:
            return await ctx.send_warning("Failed to apply the jail filter. Please try again later...")
        file_data = BytesIO(response)
        file = File(file_data, filename="jail.png")
        await ctx.send(file=file)
        os.remove(input_path)

    @media.command(name="gay", description="Apply a gay filter onto your photo")
    async def media_gay(self, ctx: EvelinaContext, image: Union[User, str] = None):
        if isinstance(image, User):
            url = image.avatar.url if image.avatar else image.default_avatar.url
        elif isinstance(image, str):
            url = image
        elif ctx.message.attachments:
            url = ctx.message.attachments[0].url
        elif ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.attachments:
                url = replied_message.attachments[0].url
            else:
                return await ctx.send_warning("Replied message doesn't have an attachment")
        else:
            return await ctx.send_warning("You must provide an image URL, mention a user, attach an image, or reply to a message with an attachment")
        data = await self.bot.getbyte(url)
        code = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        input_path = f"/var/www/html/generation/{code}.png"
        with open(input_path, "wb") as f:
            f.write(data.getbuffer())
        url = f"https://{self.bot.transcript}/generation/{code}.png"
        response = await self.bot.session.get_bytes(f"https://some-random-api.com/canvas/overlay/gay?avatar={url}")
        if not response:
            return await ctx.send_warning("Failed to apply the gay filter. Please try again later...")
        file_data = BytesIO(response)
        file = File(file_data, filename="gay.png")
        await ctx.send(file=file)
        os.remove(input_path)

    @media.command(name="passed", description="Apply a passed filter onto your photo")
    async def media_passed(self, ctx: EvelinaContext, image: Union[User, str] = None):
        if isinstance(image, User):
            url = image.avatar.url if image.avatar else image.default_avatar.url
        elif isinstance(image, str):
            url = image
        elif ctx.message.attachments:
            url = ctx.message.attachments[0].url
        elif ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.attachments:
                url = replied_message.attachments[0].url
            else:
                return await ctx.send_warning("Replied message doesn't have an attachment")
        else:
            return await ctx.send_warning("You must provide an image URL, mention a user, attach an image, or reply to a message with an attachment")
        data = await self.bot.getbyte(url)
        code = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        input_path = f"/var/www/html/generation/{code}.png"
        with open(input_path, "wb") as f:
            f.write(data.getbuffer())
        url = f"https://{self.bot.transcript}/generation/{code}.png"
        response = await self.bot.session.get_bytes(f"https://some-random-api.com/canvas/overlay/passed?avatar={url}")
        if not response:
            return await ctx.send_warning("Failed to apply the passed filter. Please try again later...")
        file_data = BytesIO(response)
        file = File(file_data, filename="passed.png")
        await ctx.send(file=file)
        os.remove(input_path)

    @media.command(name="triggered", description="Apply a triggered filter onto your photo")
    async def media_triggered(self, ctx: EvelinaContext, image: Union[User, str] = None):
        if isinstance(image, User):
            url = image.avatar.url if image.avatar else image.default_avatar.url
        elif isinstance(image, str):
            url = image
        elif ctx.message.attachments:
            url = ctx.message.attachments[0].url
        elif ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.attachments:
                url = replied_message.attachments[0].url
            else:
                return await ctx.send_warning("Replied message doesn't have an attachment")
        else:
            return await ctx.send_warning("You must provide an image URL, mention a user, attach an image, or reply to a message with an attachment")
        data = await self.bot.getbyte(url)
        code = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        input_path = f"/var/www/html/generation/{code}.png"
        with open(input_path, "wb") as f:
            f.write(data.getbuffer())
        url = f"https://{self.bot.transcript}/generation/{code}.png"
        response = await self.bot.session.get_bytes(f"https://some-random-api.com/canvas/overlay/triggered?avatar={url}")
        if not response:
            return await ctx.send_warning("Failed to apply the triggered filter. Please try again later...")
        file_data = BytesIO(response)
        file = File(file_data, filename="triggered.png")
        await ctx.send(file=file)
        os.remove(input_path)

    @media.command(name="wasted", description="Apply a wasted filter onto your photo")
    async def media_wasted(self, ctx: EvelinaContext, image: Union[User, str] = None):
        if isinstance(image, User):
            url = image.avatar.url if image.avatar else image.default_avatar.url
        elif isinstance(image, str):
            url = image
        elif ctx.message.attachments:
            url = ctx.message.attachments[0].url
        elif ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.attachments:
                url = replied_message.attachments[0].url
            else:
                return await ctx.send_warning("Replied message doesn't have an attachment")
        else:
            return await ctx.send_warning("You must provide an image URL, mention a user, attach an image, or reply to a message with an attachment")
        data = await self.bot.getbyte(url)
        code = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        input_path = f"/var/www/html/generation/{code}.png"
        with open(input_path, "wb") as f:
            f.write(data.getbuffer())
        url = f"https://{self.bot.transcript}/generation/{code}.png"
        response = await self.bot.session.get_bytes(f"https://some-random-api.com/canvas/overlay/wasted?avatar={url}")
        if not response:
            return await ctx.send_warning("Failed to apply the wasted filter. Please try again later...")
        file_data = BytesIO(response)
        file = File(file_data, filename="wasted.png")
        await ctx.send(file=file)
        os.remove(input_path)

    @media.command(name="blur", description="Apply a blur filter onto your photo")
    async def media_blur(self, ctx: EvelinaContext, image: Union[User, str] = None):
        if isinstance(image, User):
            url = image.avatar.url if image.avatar else image.default_avatar.url
        elif isinstance(image, str):
            url = image
        elif ctx.message.attachments:
            url = ctx.message.attachments[0].url
        elif ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.attachments:
                url = replied_message.attachments[0].url
            else:
                return await ctx.send_warning("Replied message doesn't have an attachment")
        else:
            return await ctx.send_warning("You must provide an image URL, mention a user, attach an image, or reply to a message with an attachment")
        data = await self.bot.getbyte(url)
        code = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        input_path = f"/var/www/html/generation/{code}.png"
        with open(input_path, "wb") as f:
            f.write(data.getbuffer())
        url = f"https://{self.bot.transcript}/generation/{code}.png"
        response = await self.bot.session.get_bytes(f"https://some-random-api.com/canvas/misc/jpg?avatar={url}")
        if not response:
            return await ctx.send_warning("Failed to apply the blur filter. Please try again later...")
        file_data = BytesIO(response)
        file = File(file_data, filename="blur.png")
        await ctx.send(file=file)
        os.remove(input_path)

    @command(name="caption", description="Add a caption to an image")
    async def caption(self, ctx: EvelinaContext, *, input_text: str = "pls god strike this man down"):
        text, url = self.extract_text_and_url(input_text)
        img_bytes = None
        if ctx.message.attachments and not url:
            attachment = ctx.message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith('image/'):
                img_bytes = await attachment.read()
            else:
                return await ctx.send_warning("The uploaded file is not an Image/GIF!")
        if not url and not img_bytes and ctx.message.reference:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if ref_msg.attachments:
                ref_attachment = ref_msg.attachments[0]
                if ref_attachment.content_type and ref_attachment.content_type.startswith('image/'):
                    img_bytes = await ref_attachment.read()
            elif ref_msg.content:
                url_match = re.search(r"(https?://[^\s]+)", ref_msg.content)
                if url_match:
                    url = url_match.group(1)
            elif ref_msg.stickers:
                url = ref_msg.stickers[0].url
        if url and "tenor.com/view" in url:
            tenor_gif = await self.get_gif_from_tenor(url)
            if not tenor_gif:
                return await ctx.send_warning("Couldn't extract Tenor GIF.")
            url = tenor_gif
        if not img_bytes and url:
            img_bytes = await self.bot.session.get_bytes(url)
            if not img_bytes:
                return await ctx.send_warning("Failed to download the image or file is not a valid image.")
        if not img_bytes:
            return await ctx.send_warning("You must provide an image/GIF via attachment, link, or reply.")
        output_buffer = io.BytesIO()
        try:
            with Image.open(io.BytesIO(img_bytes)) as img:
                if img.format == "GIF" and getattr(img, "is_animated", False):
                    durations = []
                    tasks = []
                    for frame in ImageSequence.Iterator(img):
                        frame = frame.convert("RGBA")
                        tasks.append(self.process_frame(frame, text))
                        durations.append(frame.info.get('duration', 100))
                    processed_frames = await asyncio.gather(*tasks)
                    final_frames = [frame.convert("P", palette=Image.ADAPTIVE, dither=Image.NONE) for frame in processed_frames]
                    final_frames[0].save(
                        output_buffer,
                        format="GIF",
                        save_all=True,
                        append_images=final_frames[1:],
                        duration=durations,
                        loop=0,
                        optimize=False,
                        quality=95
                    )
                else:
                    result_img = await self.process_frame(img, text)
                    result_img.save(output_buffer, format="GIF", quality=95)
            output_buffer.seek(0)
            file = discord.File(fp=output_buffer, filename="caption.gif")
            message = await ctx.send(file=file)
            channel = self.bot.get_channel(1314678504973140021)
            if channel:
                try:
                    return await message.forward(channel)
                except Exception:
                    pass
        except UnidentifiedImageError:
            await ctx.send_warning(f"The file could not be processed as an image/GIF.")

    async def get_gif_from_tenor(self, url: str) -> str | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                match = re.search(r'"(https://media1\.tenor\.com/[^"]+\.gif)"', html)
                if match:
                    return match.group(1)
                return None

    def extract_text_and_url(self, input_text: str) -> tuple[str, str | None]:
        url_match = re.search(r"(https?://[^\s]+)", input_text)
        url = url_match.group(1) if url_match else None
        text = input_text.replace(url, "").strip() if url else input_text.strip()
        return text, url

    def parse_text_for_emojis(self, text: str):
        emoji_regex = r"<:(\w+):(\d+)>"
        parts = []
        last_pos = 0
        for match in re.finditer(emoji_regex, text):
            start, end = match.span()
            if start > last_pos:
                parts.append(('text', text[last_pos:start]))
            emoji_id = match.group(2)
            parts.append(('emoji', emoji_id))
            last_pos = end
        if last_pos < len(text):
            parts.append(('text', text[last_pos:]))
        return parts

    async def render_text_with_emojis_centered(self, draw, font, base_img, text, y, emoji_size, image_width):
        parts = self.parse_text_for_emojis(text)
        total_width = 0
        async with aiohttp.ClientSession() as session:
            for part_type, content in parts:
                if part_type == 'text':
                    bbox = draw.textbbox((0, 0), content, font=font)
                    total_width += (bbox[2] - bbox[0]) + 5
                elif part_type == 'emoji':
                    total_width += emoji_size + 5
        total_width -= 5
        start_x = (image_width - total_width) // 2
        x = start_x
        async with aiohttp.ClientSession() as session:
            for part_type, content in parts:
                if part_type == 'text':
                    draw.text((x, y), content, font=font, fill='black')
                    bbox = draw.textbbox((x, y), content, font=font)
                    x = bbox[2] + 5
                elif part_type == 'emoji':
                    emoji_url = f"https://cdn.discordapp.com/emojis/{content}.png"
                    async with session.get(emoji_url) as resp:
                        if resp.status == 200:
                            emoji_bytes = await resp.read()
                            emoji_img = Image.open(io.BytesIO(emoji_bytes)).convert("RGBA")
                            emoji_img = emoji_img.resize((emoji_size, emoji_size), Image.LANCZOS)
                            base_img.paste(emoji_img, (x, y), emoji_img)
                            x += emoji_size + 5

    async def process_frame(self, img: Image.Image, text: str) -> Image.Image:
        img = img.convert("RGBA")
        try:
            font_size = max(int(img.height * 0.07), 30)
            font = ImageFont.truetype("data/fonts/ChocolatesBold.otf", size=font_size)
        except:
            font = ImageFont.load_default()
        dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        max_width = img.width - 40
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = dummy_draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        line_height = dummy_draw.textbbox((0, 0), "Ag", font=font)[3]
        min_bar_height = int(img.height * 0.15)
        bar_height = max(min_bar_height, line_height * len(lines) + 20)
        total_height = img.height + bar_height
        new_img = Image.new("RGBA", (img.width, total_height), (255, 255, 255, 255))
        new_img.paste(img, (0, bar_height), img)
        draw = ImageDraw.Draw(new_img)
        emoji_size = max(int(line_height * 1.1), 30)
        tasks = []
        for idx, line in enumerate(lines):
            y_text = (bar_height - (len(lines) * line_height)) // 2 + idx * line_height
            tasks.append(self.render_text_with_emojis_centered(draw, font, new_img, line, y_text, emoji_size, img.width))
        await asyncio.gather(*tasks)
        return new_img

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Fun(bot))