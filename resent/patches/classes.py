import asyncio
import datetime
import json
import random
import re
from contextlib import suppress
from typing import Any, Coroutine, List, Optional, Union

import aiohttp
import arrow
import discord
import emoji
import humanize
import pomice
from discord import Embed, HTTPException, Message
from discord.ext import commands
from discord.ext.commands import Context
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from resent import NeoContext as ResentContext


async def bday_send(self, ctx: Context, message: str) -> discord.Message:
    return await ctx.reply(
        embed=discord.Embed(
            color=self.bot.color,
            description=f"{self.cake} {ctx.author.mention}: {message}",
        )
    )


async def do_again(self, url: str):
    re = await self.make_request(url)
    if re["status"] == "converting":
        return await self.do_again(url)
    elif re["status"] == "failed":
        return None
    else:
        return tuple([re["url"], re["filename"]])


async def make_request(self, url: str, action: str = "get", params: dict = None):
    r = await self.bot.session.get(url, params=params)
    if action == "get":
        return await r.json()
    if action == "read":
        return await r.read()


def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%d:%02d:%02d" % (hour, minutes, seconds)


def human_format(number):
    if number > 999:
        return humanize.naturalsize(number, False, True)
    return number


class PositionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            position = int(argument)
        except ValueError:
            raise commands.BadArgument("The position must be an integer.")
        max_guild_text_channels_position = len(
            [c for c in ctx.guild.channels if isinstance(c, discord.TextChannel)]
        )
        if position <= 0 or position >= max_guild_text_channels_position + 1:
            raise commands.BadArgument(
                f"The indicated position must be between 1 and {max_guild_text_channels_position}."
            )
        position -= 1
        return position


class Time:
    def format_duration(self, timestamp):
        duration = datetime.datetime.now() - datetime.datetime.fromtimestamp(timestamp)
        years = duration.days // 365
        months = duration.days % 365 // 30
        days = duration.days % 30
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if years > 0:
            parts.append(f"{years} {'year' if years == 1 else 'years'}")
        if months > 0:
            parts.append(f"{months} {'month' if months == 1 else 'months'}")
        if days > 0:
            parts.append(f"{days} {'day' if days == 1 else 'days'}")
        if hours > 0:
            parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
        if minutes > 0:
            parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
        if seconds > 0:
            parts.append(f"{seconds} {'second' if seconds == 1 else 'seconds'}")

        return ", ".join(parts)


class EmojiPatch:
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Union[discord.Emoji, str]:
        match = self._get_id_match(argument) or re.match(
            r"<a?:[a-zA-Z0-9\_]{1,32}:([0-9]{15,20})>$", argument
        )
        result = None
        bot = ctx.bot
        guild = ctx.guild

        if match is None:
            # Try to get the emoji by name. Try local guild first.
            if guild:
                result = discord.utils.get(guild.emojis, name=argument)

            if result is None:
                result = discord.utils.get(bot.emojis, name=argument)
        else:
            emoji_id = int(match.group(1))

            # Try to look up emoji by id.
            result = bot.get_emoji(emoji_id)

        match = re.match(
            r"(?:\U0001f1e6[\U0001f1e8-\U0001f1ec\U0001f1ee\U0001f1f1\U0001f1f2\U0001f1f4\U0001f1f6-\U0001f1fa\U0001f1fc\U0001f1fd\U0001f1ff])|(?:\U0001f1e7[\U0001f1e6\U0001f1e7\U0001f1e9-\U0001f1ef\U0001f1f1-\U0001f1f4\U0001f1f6-\U0001f1f9\U0001f1fb\U0001f1fc\U0001f1fe\U0001f1ff])|(?:\U0001f1e8[\U0001f1e6\U0001f1e8\U0001f1e9\U0001f1eb-\U0001f1ee\U0001f1f0-\U0001f1f5\U0001f1f7\U0001f1fa-\U0001f1ff])|(?:\U0001f1e9[\U0001f1ea\U0001f1ec\U0001f1ef\U0001f1f0\U0001f1f2\U0001f1f4\U0001f1ff])|(?:\U0001f1ea[\U0001f1e6\U0001f1e8\U0001f1ea\U0001f1ec\U0001f1ed\U0001f1f7-\U0001f1fa])|(?:\U0001f1eb[\U0001f1ee-\U0001f1f0\U0001f1f2\U0001f1f4\U0001f1f7])|(?:\U0001f1ec[\U0001f1e6\U0001f1e7\U0001f1e9-\U0001f1ee\U0001f1f1-\U0001f1f3\U0001f1f5-\U0001f1fa\U0001f1fc\U0001f1fe])|(?:\U0001f1ed[\U0001f1f0\U0001f1f2\U0001f1f3\U0001f1f7\U0001f1f9\U0001f1fa])|(?:\U0001f1ee[\U0001f1e8-\U0001f1ea\U0001f1f1-\U0001f1f4\U0001f1f6-\U0001f1f9])|(?:\U0001f1ef[\U0001f1ea\U0001f1f2\U0001f1f4\U0001f1f5])|(?:\U0001f1f0[\U0001f1ea\U0001f1ec-\U0001f1ee\U0001f1f2\U0001f1f3\U0001f1f5\U0001f1f7\U0001f1fc\U0001f1fe\U0001f1ff])|(?:\U0001f1f1[\U0001f1e6-\U0001f1e8\U0001f1ee\U0001f1f0\U0001f1f7-\U0001f1fb\U0001f1fe])|(?:\U0001f1f2[\U0001f1e6\U0001f1e8-\U0001f1ed\U0001f1f0-\U0001f1ff])|(?:\U0001f1f3[\U0001f1e6\U0001f1e8\U0001f1ea-\U0001f1ec\U0001f1ee\U0001f1f1\U0001f1f4\U0001f1f5\U0001f1f7\U0001f1fa\U0001f1ff])|\U0001f1f4\U0001f1f2|(?:\U0001f1f4[\U0001f1f2])|(?:\U0001f1f5[\U0001f1e6\U0001f1ea-\U0001f1ed\U0001f1f0-\U0001f1f3\U0001f1f7-\U0001f1f9\U0001f1fc\U0001f1fe])|\U0001f1f6\U0001f1e6|(?:\U0001f1f6[\U0001f1e6])|(?:\U0001f1f7[\U0001f1ea\U0001f1f4\U0001f1f8\U0001f1fa\U0001f1fc])|(?:\U0001f1f8[\U0001f1e6-\U0001f1ea\U0001f1ec-\U0001f1f4\U0001f1f7-\U0001f1f9\U0001f1fb\U0001f1fd-\U0001f1ff])|(?:\U0001f1f9[\U0001f1e6\U0001f1e8\U0001f1e9\U0001f1eb-\U0001f1ed\U0001f1ef-\U0001f1f4\U0001f1f7\U0001f1f9\U0001f1fb\U0001f1fc\U0001f1ff])|(?:\U0001f1fa[\U0001f1e6\U0001f1ec\U0001f1f2\U0001f1f8\U0001f1fe\U0001f1ff])|(?:\U0001f1fb[\U0001f1e6\U0001f1e8\U0001f1ea\U0001f1ec\U0001f1ee\U0001f1f3\U0001f1fa])|(?:\U0001f1fc[\U0001f1eb\U0001f1f8])|\U0001f1fd\U0001f1f0|(?:\U0001f1fd[\U0001f1f0])|(?:\U0001f1fe[\U0001f1ea\U0001f1f9])|(?:\U0001f1ff[\U0001f1e6\U0001f1f2\U0001f1fc])|(?:\U0001f3f3\ufe0f\u200d\U0001f308)|(?:\U0001f441\u200d\U0001f5e8)|(?:[\U0001f468\U0001f469]\u200d\u2764\ufe0f\u200d(?:\U0001f48b\u200d)?[\U0001f468\U0001f469])|(?:(?:(?:\U0001f468\u200d[\U0001f468\U0001f469])|(?:\U0001f469\u200d\U0001f469))(?:(?:\u200d\U0001f467(?:\u200d[\U0001f467\U0001f466])?)|(?:\u200d\U0001f466\u200d\U0001f466)))|(?:(?:(?:\U0001f468\u200d\U0001f468)|(?:\U0001f469\u200d\U0001f469))\u200d\U0001f466)|[\u2194-\u2199]|[\u23e9-\u23f3]|[\u23f8-\u23fa]|[\u25fb-\u25fe]|[\u2600-\u2604]|[\u2638-\u263a]|[\u2648-\u2653]|[\u2692-\u2694]|[\u26f0-\u26f5]|[\u26f7-\u26fa]|[\u2708-\u270d]|[\u2753-\u2755]|[\u2795-\u2797]|[\u2b05-\u2b07]|[\U0001f191-\U0001f19a]|[\U0001f1e6-\U0001f1ff]|[\U0001f232-\U0001f23a]|[\U0001f300-\U0001f321]|[\U0001f324-\U0001f393]|[\U0001f399-\U0001f39b]|[\U0001f39e-\U0001f3f0]|[\U0001f3f3-\U0001f3f5]|[\U0001f3f7-\U0001f3fa]|[\U0001f400-\U0001f4fd]|[\U0001f4ff-\U0001f53d]|[\U0001f549-\U0001f54e]|[\U0001f550-\U0001f567]|[\U0001f573-\U0001f57a]|[\U0001f58a-\U0001f58d]|[\U0001f5c2-\U0001f5c4]|[\U0001f5d1-\U0001f5d3]|[\U0001f5dc-\U0001f5de]|[\U0001f5fa-\U0001f64f]|[\U0001f680-\U0001f6c5]|[\U0001f6cb-\U0001f6d2]|[\U0001f6e0-\U0001f6e5]|[\U0001f6f3-\U0001f6f6]|[\U0001f910-\U0001f91e]|[\U0001f920-\U0001f927]|[\U0001f933-\U0001f93a]|[\U0001f93c-\U0001f93e]|[\U0001f940-\U0001f945]|[\U0001f947-\U0001f94b]|[\U0001f950-\U0001f95e]|[\U0001f980-\U0001f991]|\u00a9|\u00ae|\u203c|\u2049|\u2122|\u2139|\u21a9|\u21aa|\u231a|\u231b|\u2328|\u23cf|\u24c2|\u25aa|\u25ab|\u25b6|\u25c0|\u260e|\u2611|\u2614|\u2615|\u2618|\u261d|\u2620|\u2622|\u2623|\u2626|\u262a|\u262e|\u262f|\u2660|\u2663|\u2665|\u2666|\u2668|\u267b|\u267f|\u2696|\u2697|\u2699|\u269b|\u269c|\u26a0|\u26a1|\u26aa|\u26ab|\u26b0|\u26b1|\u26bd|\u26be|\u26c4|\u26c5|\u26c8|\u26ce|\u26cf|\u26d1|\u26d3|\u26d4|\u26e9|\u26ea|\u26fd|\u2702|\u2705|\u270f|\u2712|\u2714|\u2716|\u271d|\u2721|\u2728|\u2733|\u2734|\u2744|\u2747|\u274c|\u274e|\u2757|\u2763|\u2764|\u27a1|\u27b0|\u27bf|\u2934|\u2935|\u2b1b|\u2b1c|\u2b50|\u2b55|\u3030|\u303d|\u3297|\u3299|\U0001f004|\U0001f0cf|\U0001f170|\U0001f171|\U0001f17e|\U0001f17f|\U0001f18e|\U0001f201|\U0001f202|\U0001f21a|\U0001f22f|\U0001f250|\U0001f251|\U0001f396|\U0001f397|\U0001f56f|\U0001f570|\U0001f587|\U0001f590|\U0001f595|\U0001f596|\U0001f5a4|\U0001f5a5|\U0001f5a8|\U0001f5b1|\U0001f5b2|\U0001f5bc|\U0001f5e1|\U0001f5e3|\U0001f5e8|\U0001f5ef|\U0001f5f3|\U0001f6e9|\U0001f6eb|\U0001f6ec|\U0001f6f0|\U0001f930|\U0001f9c0|[#|0-9]\u20e3",
            argument,
        )
        if match:
            result = argument

        if result is None:
            raise commands.EmojiNotFound(argument)

        return result


class BlackTea:
    """BlackTea backend variables"""

    MatchStart = {}
    lifes = {}

    async def get_string():
        lis = await BlackTea.get_words()
        word = random.choice([l for l in lis if len(l) > 3])
        return word[:3]

    async def get_words():
        async with aiohttp.ClientSession() as cs:
            async with cs.get("https://www.mit.edu/~ecprice/wordlist.100000") as r:
                byte = await r.read()
                data = str(byte, "utf-8")
                return data.splitlines()


class RockPaperScissors(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.get_emoji = {"rock": "🪨", "paper": "📰", "scissors": "✂️"}
        self.status = False
        super().__init__(timeout=10)

    async def action(self, interaction: discord.Interaction, selection: str):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.client.ext.send_warning(
                interaction, "This is not your game", ephemeral=True
            )
        botselection = random.choice(["rock", "paper, scissors"])

        def getwinner():
            if botselection == "rock" and selection == "scissors":
                return interaction.client.user.id
            elif botselection == "rock" and selection == "paper":
                return interaction.user.id
            elif botselection == "paper" and selection == "rock":
                return interaction.client.user.id
            elif botselection == "paper" and selection == "scissors":
                return interaction.user.id
            elif botselection == "scissors" and selection == "rock":
                return interaction.user.id
            elif botselection == "scissors" and selection == "paper":
                return interaction.client.user.id
            else:
                return "tie"

        if getwinner() == "tie":
            await interaction.response.edit_message(
                embed=discord.Embed(
                    color=interaction.client.color,
                    title="Tie!",
                    description=f"You both picked {self.get_emoji.get(selection)}",
                )
            )
        elif getwinner() == interaction.user.id:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    color=interaction.client.color,
                    title="You won!",
                    description=f"You picked {self.get_emoji.get(selection)} and the bot picked {self.get_emoji.get(botselection)}",
                )
            )
        else:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    color=interaction.client.color,
                    title="Bot won!",
                    description=f"You picked {self.get_emoji.get(selection)} and the bot picked {self.get_emoji.get(botselection)}",
                )
            )
        await self.disable_buttons()
        self.status = True

    @discord.ui.button(emoji="🪨")
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        return await self.action(interaction, "rock")

    @discord.ui.button(emoji="📰")
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        return await self.action(interaction, "paper")

    @discord.ui.button(emoji="✂️")
    async def scissors(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        return await self.action(interaction, "scissors")

    async def on_timeout(self):
        if self.status == False:
            await self.disable_buttons()


class TicTacToeButton(discord.ui.Button["TicTacToe"]):
    def __init__(
        self, x: int, y: int, player1: discord.Member, player2: discord.Member
    ):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y
        self.player1 = player1
        self.player2 = player2

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == view.X:
            if interaction.user != self.player1:
                return await interaction.response.send_message(
                    "you can't interact with this button", ephemeral=True
                )
            self.style = discord.ButtonStyle.danger
            self.label = "X"
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            content = f"It is now **{self.player2.name}**'s turn"
        else:
            if interaction.user != self.player2:
                return await interaction.response.send_message(
                    "you can't interact with this button", ephemeral=True
                )
            self.style = discord.ButtonStyle.success
            self.label = "O"
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            content = f"It is now **{self.player1.name}'s** turn"

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = f"**{self.player1.name}** won!"
            elif winner == view.O:
                content = "**{}** won!".format(self.player2.name)
            else:
                content = "It's a tie!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(content=content, view=view)


class TicTacToe(discord.ui.View):
    children: List[TicTacToeButton]
    X = -1
    O = 1
    Tie = 2

    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__()
        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y, player1, player2))

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

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self.view)

    async def disable_buttons(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)


class Modals:
    class Name(discord.ui.Modal, title="change the role name"):
        name = discord.ui.TextInput(
            label="role name",
            placeholder="your new role name here",
            style=discord.TextStyle.short,
            required=True,
        )

        async def on_submit(self, interaction: discord.Interaction):
            check = await interaction.client.db.fetchrow(
                "SELECT * FROM booster_roles WHERE guild_id = {} AND user_id = {}".format(
                    interaction.guild.id, interaction.user.id
                )
            )
            if check is None:
                return await interaction.client.ext.send_warning(
                    interaction,
                    "You don't have a booster role. Please use `boosterrole create` command first",
                    ephemeral=True,
                )
            role = interaction.guild.get_role(check["role_id"])
            await role.edit(name=self.name.value)
            return await interaction.client.ext.send_success(
                interaction,
                "Changed the **booster role** name in **{}**".format(self.name.value),
                ephemeral=True,
            )

    class Icon(discord.ui.Modal, title="change the role icon"):
        name = discord.ui.TextInput(
            label="role icon",
            placeholder="this should be an emoji",
            style=discord.TextStyle.short,
            required=True,
        )

        async def on_submit(self, interaction: discord.Interaction):
            try:
                check = await interaction.client.db.fetchrow(
                    "SELECT * FROM booster_roles WHERE guild_id = {} AND user_id = {}".format(
                        interaction.guild.id, interaction.user.id
                    )
                )
                if check is None:
                    return await interaction.client.ext.send_warning(
                        interaction,
                        "You don't have a booster role. Please use `boosterrole create` command first",
                        ephemeral=True,
                    )
                role = interaction.guild.get_role(check["role_id"])
                icon = ""
                if emoji.is_emoji(self.name.value):
                    icon = self.name.value
                else:
                    emojis = re.findall(
                        r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>",
                        self.name.value,
                    )
                    emoj = emojis[0]
                    format = ".gif" if emoj[0] == "a" else ".png"
                    url = "https://cdn.discordapp.com/emojis/{}{}".format(
                        emoj[2], format
                    )
                    icon = await interaction.client.session.read(url)
                await role.edit(display_icon=icon)
                return await interaction.client.ext.send_success(
                    interaction, "Changed the **booster role** icon", ephemeral=True
                )
            except:
                return await interaction.client.ext.send_error(
                    interaction, "Unable to change the role icon", ephemeral=True
                )

    class Color(discord.ui.Modal, title="change the role colors"):
        name = discord.ui.TextInput(
            label="role color",
            placeholder="this should be a hex code",
            style=discord.TextStyle.short,
            required=True,
        )

        async def on_submit(self, interaction: discord.Interaction):
            try:
                check = await interaction.client.db.fetchrow(
                    "SELECT * FROM booster_roles WHERE guild_id = {} AND user_id = {}".format(
                        interaction.guild.id, interaction.user.id
                    )
                )
                if check is None:
                    return await interaction.client.ext.send_warning(
                        interaction,
                        "You don't have a booster role. Please use `boosterrole create` command first",
                        ephemeral=True,
                    )
                role = interaction.guild.get_role(check["role_id"])
                color = self.name.value.replace("#", "")
                color = int(color, 16)
                await role.edit(color=color)
                return await interaction.client.ext.send_success(
                    interaction, "Changed the **booster role** color", ephemeral=True
                )
            except:
                return await interaction.client.ext.send_error(
                    interaction, "Unable to change the role color", ephemeral=True
                )


class Timezone(object):
    def __init__(self, bot: commands.AutoShardedBot):
        """
        Get timezones of people
        """
        self.bot = bot
        self.clock = "🕑"
        self.months = {
            "01": "January",
            "02": "February",
            "03": "March",
            "04": "April",
            "05": "May",
            "06": "June",
            "07": "July",
            "08": "August",
            "09": "September",
            "10": "October",
            "11": "November",
            "12": "December",
        }

    async def timezone_send(self, ctx: Context, message: str):
        return await ctx.reply(
            embed=discord.Embed(
                color=self.bot.color,
                description=f"{self.clock} {ctx.author.mention}: {message}",
            )
        )

    async def timezone_request(self, member: discord.Member):
        coord = await self.get_user_lat_long(member)
        if coord is None:
            return None
        utc = arrow.utcnow()
        local = utc.to(coord)
        timestring = local.format("YYYY-MM-DD HH:mm").split(" ")
        date = timestring[0][5:].split("-")
        try:
            hours, minutes = [int(x) for x in timestring[1].split(":")[:2]]
        except IndexError:
            return "N/A"

        if hours >= 12:
            suffix = "PM"
            hours -= 12
        else:
            suffix = "AM"
        if hours == 0:
            hours = 12
        return f"{self.months.get(date[0])} {self.bot.ext.ordinal(date[1])} {hours}:{minutes:02d} {suffix}"

    async def get_user_lat_long(self, member: discord.Member):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM timezone WHERE user_id = $1", member.id
        )
        if check is None:
            return None
        return check["zone"]

    async def tz_set_cmd(self, ctx: Context, location: str):
        await ctx.typing()
        geolocator = Nominatim(
            user_agent="Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36"
        )
        lad = location
        location = geolocator.geocode(lad)
        if location is None:
            return await ctx.send_warning(
                "Couldn't find a **timezone** for that location"
            )
        check = await self.bot.db.fetchrow(
            "SELECT * FROM timezone WHERE user_id = $1", ctx.author.id
        )
        obj = TimezoneFinder()
        result = obj.timezone_at(lng=location.longitude, lat=location.latitude)
        if not check:
            await self.bot.db.execute(
                "INSERT INTO timezone VALUES ($1,$2)", ctx.author.id, result
            )
        else:
            await self.bot.db.execute(
                "DELETE FROM timezone WHERE user_id = $1", ctx.author.id
            )
            await self.bot.db.execute(
                "INSERT INTO timezone VALUES ($1,$2)", ctx.author.id, result
            )
        embed = Embed(
            color=self.bot.color,
            description=f"Saved your timezone as **{result}**\n{self.clock} Current time: **{await self.timezone_request(ctx.author)}**",
        )
        await ctx.reply(embed=embed)

    async def get_user_timezone(self, ctx: Context, member: discord.Member):
        if await self.timezone_request(member) is None:
            if member.id == ctx.author.id:
                return await ctx.send_warning(
                    f"You don't have a **timezone** set. Use `{ctx.clean_prefix}tz set` command instead"
                )
            else:
                return await ctx.send_warning(
                    f"**{member.name}** doesn't have their **timezone** set"
                )
        if member.id == ctx.author.id:
            return await self.timezone_send(
                ctx, f"Your current time: **{await self.timezone_request(member)}**"
            )
        else:
            return await self.timezone_send(
                ctx,
                f"**{member.name}'s** current time: **{await self.timezone_request(member)}**",
            )


class MarryView(discord.ui.View):
    def __init__(self, ctx: commands.Context, member: discord.Member):
        super().__init__()
        self.ctx = ctx
        self.member = member
        self.status = False

    @discord.ui.button(emoji="<:check:1083455835189022791>")
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.ctx.author:
            return await interaction.client.ext.send_warning(
                interaction,
                "you can't accept your own marriage".capitalize(),
                ephemeral=True,
            )
        elif interaction.user != self.member:
            return await self.ctx.bot.ext.send_warning(
                interaction,
                "you are not the author of this embed".capitalize(),
                ephemeral=True,
            )
        else:
            await interaction.client.db.execute(
                "INSERT INTO marry VALUES ($1, $2, $3)",
                self.ctx.author.id,
                self.member.id,
                datetime.datetime.now().timestamp(),
            )
            embe = discord.Embed(
                color=interaction.client.color,
                description=f"<a:milk_love:1208459088069922937> **{self.ctx.author}** succesfully married with **{self.member}**",
            )
            await interaction.response.edit_message(content=None, embed=embe, view=None)
            self.status = True

    @discord.ui.button(emoji="<:stop:1083455877450834041>")
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.ctx.author:
            return await self.ctx.bot.ext.send_warning(
                interaction,
                "you can't reject your own marriage".capitalize(),
                ephemeral=True,
            )
        elif interaction.user != self.member:
            return await self.ctx.bot.ext.send_warning(
                interaction,
                "you are not the author of this embed".capitalize(),
                ephemeral=True,
            )
        else:
            embe = discord.Embed(
                color=interaction.client.color,
                description=f"**{self.ctx.author}** i'm sorry, but **{self.member}** is probably not the right person for you",
            )
            await interaction.response.edit_message(content=None, embed=embe, view=None)
            self.status = True

    async def on_timeout(self):
        if self.status == False:
            embed = discord.Embed(
                color=0xD3D3D3, description=f"**{self.member}** didn't reply in time :("
            )
            try:
                await self.message.edit(content=None, embed=embed, view=None)
            except:
                pass


class DiaryModal(discord.ui.Modal, title="Create a diary page"):
    titl = discord.ui.TextInput(
        label="Your diary title",
        placeholder="Give your diary page a short name",
        style=discord.TextStyle.short,
    )
    text = discord.ui.TextInput(
        label="Your diary text",
        placeholder="Share your feelings or thoughts here",
        max_length=2000,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.datetime.now()
        date = f"{now.month}/{now.day}/{str(now.year)[2:]}"
        await interaction.client.db.execute(
            "INSERT INTO diary VALUES ($1,$2,$3,$4)",
            interaction.user.id,
            self.text.value,
            self.titl.value,
            date,
        )
        embed = discord.Embed(
            color=interaction.client.color,
            description=f"> {interaction.client.yes} {interaction.user.mention}: Added a diary page for today",
        )
        return await interaction.response.edit_message(embed=embed, view=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        embed = discord.Embed(
            color=interaction.client.color,
            description=f"> {interaction.client.no} {interaction.user.mention}: Unable to create the diary",
        )
        return await interaction.response.edit_message(embed=embed, view=None)


class Player(pomice.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx: ResentContext = None
        self.queue = pomice.Queue()
        self.loop: bool = False
        self.current_track: pomice.Track = None
        self.awaiting = False

    def set_context(self, ctx: ResentContext):
        self.context = ctx

    def shuffle(self) -> None:
        return random.shuffle(self.queue)

    async def set_pause(self, pause: bool) -> Coroutine[Any, Any, bool]:
        if pause is True:
            self.awaiting = True
        else:
            if self.awaiting:
                self.awaiting = False

        return await super().set_pause(pause)

    async def do_next(self, track: pomice.Track = None) -> None:
        if not self.loop:
            if not track:
                try:
                    track: pomice.Track = self.queue.get()
                except pomice.QueueEmpty:
                    return await self.kill()

            self.current_track = track

        await self.play(self.current_track)
        await self.context.send(
            embed=Embed(
                color=self.context.bot.color,
                description=f"🎵 {self.context.author.mention}: Now playing [**{track.title}**]({track.uri})",
            )
        )

        if self.awaiting:
            self.awaiting = False

    async def kill(self) -> Message:
        with suppress((HTTPException), (KeyError)):
            await self.destroy()
            return await self.context.send_success("Left the voice channel")


class Joint:

    def check_joint():
        async def predicate(ctx: commands.Context):
            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM joint WHERE guild_id = $1", ctx.guild.id
            )
            if not check:
                await ctx.bot.ext.send_error(
                    ctx,
                    f"This server **doesn't** have a **joint**. Use `{ctx.clean_prefix}joint toggle` to get one",
                )
            return check is not None

        return commands.check(predicate)

    def joint_owner():
        async def predicate(ctx: commands.Context):
            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM joint WHERE guild_id = $1", ctx.guild.id
            )
            if check["holder"] != ctx.author.id:
                await ctx.send_warning(
                    f"You don't have the **joint**. Steal it from <@{check['holder']}>"
                )
            return check["holder"] == ctx.author.id

        return commands.check(predicate)


class Boosts:

    def get_level(boosts: int):
        async def predicate(ctx: commands.Context):
            if ctx.guild.premium_subscription_count < boosts:
                await ctx.send_warning(
                    f"This server needs to have more than **{boosts}** boosts in order to use this command"
                )
            return ctx.guild.premium_subscription_count >= boosts

        return commands.check(predicate)


class Mod:

    def is_mod_configured():
        async def predicate(ctx: commands.Context):
            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
            )
            if not check:
                await ctx.send_warning(
                    f"Moderation isn't **enabled** in this server. Enable it using `{ctx.clean_prefix}setmod` command"
                )
                return False
            return True

        return commands.check(predicate)

    async def check_role_position(ctx: commands.Context, role: discord.Role) -> bool:
        if (
            role.position >= ctx.author.top_role.position
            and ctx.author.id != ctx.guild.owner_id
        ) or not role.is_assignable():
            await ctx.send_warning("I cannot manage this role for you")
            return False
        return True

    async def check_hieracy(ctx: commands.Context, member: discord.Member) -> bool:
        if member.id == ctx.bot.user.id:
            if ctx.command.name != "nickname":
                await ctx.reply("leave me alone <:mmangry:1081633006923546684>")
                return False
        if (
            (
                ctx.author.top_role.position <= member.top_role.position
                and ctx.guild.owner_id != ctx.author.id
            )
            or ctx.guild.me.top_role <= member.top_role
            or (member.id == ctx.guild.owner_id and ctx.author.id != member.id)
        ):
            await ctx.send_warning("You can't do this action on **{}**".format(member))
            return False
        return True


class Perms:

    def server_owner():
        async def predicate(ctx: commands.Context):
            if ctx.author.id != ctx.guild.owner_id:
                await ctx.send_warning(
                    f"This command can be used only by **{ctx.guild.owner}**"
                )
                return False
            return True

        return commands.check(predicate)

    def check_whitelist(module: str):
        async def predicate(ctx: commands.Context):
            if ctx.guild is None:
                return False
            if ctx.author.id == ctx.guild.owner.id:
                return True
            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM whitelist WHERE guild_id = $1 AND object_id = $2 AND mode = $3 AND module = $4",
                ctx.guild.id,
                ctx.author.id,
                "user",
                module,
            )
            if check is None:
                await ctx.send_warning(f"You are not **whitelisted** for **{module}**")
                return False
            return True

        return commands.check(predicate)

    def get_perms(perm: str = None):
        async def predicate(ctx: commands.Context):
            if perm is None:
                return True
            if ctx.guild.owner == ctx.author:
                return True
            if ctx.author.guild_permissions.administrator:
                return True
            for r in ctx.author.roles:
                if perm in [str(p[0]) for p in r.permissions if p[1] is True]:
                    return True
                check = await ctx.bot.db.fetchrow(
                    "SELECT permissions FROM fake_permissions WHERE role_id = $1 and guild_id = $2",
                    r.id,
                    r.guild.id,
                )
                if check is None:
                    continue
                permissions = json.loads(check[0])
                if perm in permissions or "administrator" in permissions:
                    return True
            raise commands.MissingPermissions([perm])

        return commands.check(predicate)

    async def has_perms(ctx: commands.Context, perm: str = None):
        if perm is None:
            return True
        if ctx.guild.owner == ctx.author:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        for r in ctx.author.roles:
            if perm in [str(p[0]) for p in r.permissions if p[1] is True]:
                return True
            check = await ctx.bot.db.fetchrow(
                "SELECT permissions FROM fake_permissions WHERE role_id = $1 and guild_id = $2",
                r.id,
                r.guild.id,
            )
            if check is None:
                continue
            permissions = json.loads(check[0])
            if perm in permissions or "administrator" in permissions:
                return True
        return False


class Messages:

    def good_message(message: discord.Message) -> bool:
        if not message.guild or message.author.bot or message.content == "":
            return False
        return True


class LastFMHandler(object):
    def __init__(self, api_key: str):
        self.apikey = api_key
        self.baseurl = "https://ws.audioscrobbler.com/2.0/"

    async def do_request(self, data: dict):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(self.baseurl, params=data) as r:
                return await r.json()

    async def get_track_playcount(self, user: str, track: dict) -> int:
        data = {
            "method": "track.getInfo",
            "api_key": self.apikey,
            "artist": track["artist"]["#text"],
            "track": track["name"],
            "format": "json",
            "username": user,
        }
        return (await self.do_request(data))["track"]["userplaycount"]

    async def get_album_playcount(self, user: str, track: dict) -> int:
        data = {
            "method": "album.getInfo",
            "api_key": self.apikey,
            "artist": track["artist"]["#text"],
            "album": track["album"]["#text"],
            "format": "json",
            "username": user,
        }
        return (await self.do_request(data))["album"]["userplaycount"]

    async def get_artist_playcount(self, user: str, artist: str) -> int:
        data = {
            "method": "artist.getInfo",
            "api_key": self.apikey,
            "artist": artist,
            "format": "json",
            "username": user,
        }
        return (await self.do_request(data))["artist"]["stats"]["userplaycount"]

    async def get_album(self, track: dict) -> dict:
        data = {
            "method": "album.getInfo",
            "api_key": self.apikey,
            "artist": track["artist"]["#text"],
            "album": track["album"]["#text"],
            "format": "json",
        }
        return (await self.do_request(data))["album"]

    async def get_track(self, track: dict) -> dict:
        data = {
            "method": "album.getInfo",
            "api_key": self.apikey,
            "artist": track["artist"]["#text"],
            "track": track["track"]["#text"],
            "format": "json",
        }
        return await self.do_request(data)

    async def get_user_info(self, user: str) -> dict:
        data = {
            "method": "user.getinfo",
            "user": user,
            "api_key": self.apikey,
            "format": "json",
        }
        return await self.do_request(data)

    async def get_top_artists(self, user: str, count: int) -> dict:
        data = {
            "method": "user.getTopArtists",
            "user": user,
            "api_key": self.apikey,
            "format": "json",
            "limit": count,
        }
        return await self.do_request(data)

    async def get_top_tracks(self, user: str, count: int) -> dict:
        data = {
            "method": "user.getTopTracks",
            "user": user,
            "api_key": self.apikey,
            "format": "json",
            "period": "overall",
            "limit": count,
        }
        return await self.do_request(data)

    async def get_top_albums(self, user: str, count: int) -> dict:
        params = {
            "api_key": self.apikey,
            "user": user,
            "period": "overall",
            "limit": count,
            "method": "user.getTopAlbums",
            "format": "json",
        }
        return await self.do_request(params)

    async def get_tracks_recent(self, user: str, count: int) -> dict:
        data = {
            "method": "user.getrecenttracks",
            "user": user,
            "api_key": self.apikey,
            "format": "json",
            "limit": count,
        }
        return await self.do_request(data)


class TimeConverter(object):
    def convert_datetime(self, date: datetime.datetime = None):
        if date is None:
            return None
        month = f"0{date.month}" if date.month < 10 else date.month
        day = f"0{date.day}" if date.day < 10 else date.day
        year = date.year
        minute = f"0{date.minute}" if date.minute < 10 else date.minute
        if date.hour < 10:
            hour = f"0{date.hour}"
            meridian = "AM"
        elif date.hour > 12:
            hour = f"0{date.hour - 12}" if date.hour - 12 < 10 else f"{date.hour - 12}"
            meridian = "PM"
        else:
            hour = date.hour
            meridian = "PM"
        return f"{month}/{day}/{year} at {hour}:{minute} {meridian} ({discord.utils.format_dt(date, style='R')})"

    def ordinal(self, num: int) -> str:
        """Convert from number to ordinal (10 - 10th)"""
        numb = str(num)
        if numb.startswith("0"):
            numb = numb.strip("0")
        if numb in ["11", "12", "13"]:
            return numb + "th"
        if numb.endswith("1"):
            return numb + "st"
        elif numb.endswith("2"):
            return numb + "nd"
        elif numb.endswith("3"):
            return numb + "rd"
        else:
            return numb + "th"


class Cache:
    def __init__(self):
        self.cache_inventory = {}

    def __repr__(self) -> str:
        return str(self.cache_inventory)

    async def do_expiration(self, key: str, expiration: int) -> None:
        await asyncio.sleep(expiration)
        self.cache_inventory.pop(key)

    def get(self, key: str) -> Any:
        """Get the object that is associated with the given key"""
        return self.cache_inventory.get(key)

    async def set(self, key: str, object: Any, expiration: Optional[int] = None) -> Any:
        """Set any object associatng with the given key"""
        self.cache_inventory[key] = object
        if expiration:
            asyncio.ensure_future(self.do_expiration(key, expiration))
        return object

    def remove(self, key: str) -> None:
        """An alias for delete method"""
        return self.delete(key)

    def delete(self, key: str) -> None:
        """Delete a key from the cache"""
        if self.get(key):
            del self.cache_inventory[key]
            return None


class OwnerConfig:
    async def send_dm(
        ctx: commands.Context, member: discord.Member, action: str, reason: str
    ):
        embed = discord.Embed(
            color=ctx.bot.color,
            description=f"You have been **{action}** in every server resent is in.\n{f'**Reason:** {reason}' if reason != 'No reason provided' else ''}",
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=f"sent from {ctx.author}", disabled=True))
        try:
            await member.send(embed=embed, view=view)
        except:
            pass
