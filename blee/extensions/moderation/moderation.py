import datetime

import discord
from discord import Embed, Member, User
from discord.ext.commands import Cog, command, has_permissions
from extensions.moderation.classes import ModConfig
from tools.bleed import Bleed
from tools.client.context import Context


class Moderation(Cog):
    def __init__(self, bot: Bleed) -> None:
        self.bot: Bleed = bot

    @command(aliases=["setme"])
    @has_permissions(administrator=True)
    async def setup(self, ctx: Context):
        """Start process for setting up the moderation system"""

        check = await self.bot.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
        )

        if check:
            return await ctx.warn(
                "The jail system is **already** enabled in this server!"
            )

        await ctx.typing()

        role = await ctx.guild.create_role(name="jail")

        for channel in ctx.guild.channels:
            await channel.set_permissions(role, view_channel=False)

        overwrite = {
            role: discord.PermissionOverwrite(view_channel=True),
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }

        over = {ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)}

        text = await ctx.guild.create_text_channel(name="mod-logs", overwrites=over)
        jai = await ctx.guild.create_text_channel(name="jail", overwrites=overwrite)

        await self.bot.db.execute(
            "INSERT INTO mod VALUES ($1,$2,$3,$4)",
            ctx.guild.id,
            text.id,
            jai.id,
            role.id,
        )

        await self.bot.db.execute("INSERT INTO cases VALUES ($1,$2)", ctx.guild.id, 0)
        return await ctx.approve(
            "Moderation system set up has been completed. Please make sure that all of your channels and roles have been configured properly."
        )

    @command(example="johndoe Being mean")
    @has_permissions(manage_messages=True)
    async def warn(self, ctx: Context, member: Member, reason: str):
        """Warns the mentioned user and private messages them the warning"""

        embed = Embed(title="Warned", color=0xFADB5E, timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=ctx.guild.icon.url)  # type: ignor
        embed.add_field(name="You have been warned in", value=f"{ctx.guild.name}")
        embed.add_field(name="Moderator", value=f"{ctx.author.name}")
        embed.add_field(name="Reason", value=f"{reason}")

        await ctx.send(
            f"{member.mention} you have been warned for doing something stupid, specifically {reason}, which this broke the rules. Couldn't DM you more information."
        )
        await member.send(embed=embed)
        await ModConfig.sendlogs(self.bot, "warn", ctx.author, member, reason)  # type: ignore
