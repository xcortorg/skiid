from discord.ext.commands import Cog, command, group, CommandError, has_permissions
from discord import Client, Embed, File, Member, User, Guild
from lib.patch.context import Context


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot

    @Cog.listener("on_valid_message")
    async def on_auto_reaction(self, ctx: Context):
        words = [r.lower() for r in ctx.message.content.split(" ")]
        words.append(str(ctx.channel.id))
        records = await self.bot.db.fetch(
            """SELECT * FROM auto_reactions WHERE guild_id = $1 AND trigger = ANY($2)""",
            ctx.guild.id,
            words,
        )
        for record in records:
            for reaction in record.response:
                await ctx.message.add_reaction(str(reaction))
