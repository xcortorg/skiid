import os

import discord
import jishaku
from discord import Activity, ActivityType, Embed
from discord.ext import commands
from discord.gateway import DiscordWebSocket
from dotenv import load_dotenv

load_dotenv()
allowed_ids = [598125772754124823]

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.presences = True
intents.message_content = True


class MyBot(commands.Bot):
    async def on_ready(self):
        print(f"Logged in as {self.user.name} - {self.user.id}")
        await self.load_extension("jishaku")


async def is_owner(user: discord.User):
    return user.id in allowed_ids


bot = MyBot(
    command_prefix=",",
    intents=intents,
    allowed_mentions=discord.AllowedMentions(
        everyone=False, roles=False, replied_user=False, users=True
    ),
    owner_ids=set(allowed_ids),
)

bot.is_owner = is_owner


@bot.command()
async def ping(ctx):
    """
    Displays the bot's latency.
    """
    await ctx.reply(
        embed=Embed(
            color=0x729BB0,
            description=f"📡 {ctx.author.mention}: ping `{round(bot.latency * 1000)}ms`",
        )
    )


bot.run(os.getenv("TOKEN"))
