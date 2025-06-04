import os

import discord
import psycopg2
from discord import Embed
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB"),
            user=os.getenv("DBUSER"),
            password=os.getenv("PASSW"),
            host=os.getenv("HOST"),
            port=os.getenv("PORT"),
        )

    @commands.command()
    async def stats(self, ctx):
        """
        Displays the number of people who have the vanity in their status.
        """
        count = 0
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT vanity FROM servers WHERE guild_id = %s", (ctx.guild.id,)
        )
        result = cursor.fetchone()
        cursor.close()
        if result:
            vanity = result[0]
            for member in ctx.guild.members:
                current_status = member.activity.name if member.activity else "None"
                has_vanity = vanity.lower() in current_status.lower()
                if has_vanity:
                    count += 1
        embed = Embed(
            description=f"Currently, **there** are `{count}` people **with** the vanity in their **status**.",
            color=0x729BB0,
        )
        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(info(bot))
