from discord.ext.commands import Cog, group, Context, has_permissions
from discord import (
    Embed,
    TextStyle,
    Interaction,
    TextChannel,
    app_commands,
)
from discord.ui import Modal, TextInput
import datetime
import re
from typing_extensions import Self


class ConfessionModel(Modal, title="confess"):
    name = TextInput(
        label="confession",
        placeholder="the confession is anonymous",
        style=TextStyle.long,
    )

    async def on_submit(self: Self, interaction: Interaction):
        check = await interaction.client.db.fetchrow(
            "SELECT * FROM confess WHERE guild_id = $1", interaction.guild.id
        )
        if check:
            if re.search(
                r"[(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)",
                self.name.value,
            ):
                return await interaction.response.send_message(
                    "You cannot use links in a confession", ephemeral=True
                )

            channel = interaction.guild.get_channel(check["channel_id"])
            if not channel:
                return await interaction.response.send_message(
                    "The confession channel no longer exists.", ephemeral=True
                )
            count = check["confession"] + 1
            embed = Embed(
                color=interaction.client.color,
                description=f"{interaction.user.mention}: sent your confession in {channel.mention}",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            e = Embed(
                color=interaction.client.color,
                description=f"{self.name.value}",
                timestamp=datetime.datetime.now(),
            )
            e.set_author(
                name=f"anonymous confession #{count}",
                url="https://discord.gg/greedbot",
            )

            e.set_footer(text="type /confess to send a confession")
            await channel.send(embed=e)
            await interaction.client.db.execute(
                "UPDATE confess SET confession = $1 WHERE guild_id = $2",
                count,
                interaction.guild.id,
            )
            await interaction.client.db.execute(
                "INSERT INTO confess_members VALUES ($1,$2,$3)",
                interaction.guild.id,
                interaction.user.id,
                count,
            )


class Confessions(Cog):
    def __init__(self, bot):
        self.bot = bot

    @group(
        name="confessions",
        invoke_without_command=True,
        brief="View the commands for confessions",
        example=",confessions",
    )
    async def confessions(self, ctx):
        return await ctx.send_help()

    @confessions.command(
        name="mute",
        brief="mute a member that sent a specified confession",
        example=",confessions mute @sudosql",
    )
    @has_permissions(manage_messages=True)
    async def confessions_mute(self, ctx: Context, *, confession: int):
        """mute a member that sent a specific confession"""
        check = await self.bot.db.fetchrow(
            "SELECT channel_id FROM confess WHERE guild_id = $1", ctx.guild.id
        )

        if check is None:
            return await ctx.warning("Confessions aren't **enabled** in this server")

        re = await self.bot.db.fetchrow(
            "SELECT * FROM confess_members WHERE guild_id = $1 AND confession = $2",
            ctx.guild.id,
            confession,
        )

        if re is None:
            return await ctx.warning("Couldn't find that confession")

        member_id = re["user_id"]
        r = await self.bot.db.fetchrow(
            "SELECT * FROM confess_mute WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member_id,
        )

        if r:
            return await ctx.warning("This **member** is **already** confession muted")

        await self.bot.db.execute(
            "INSERT INTO confess_mute VALUES ($1,$2)", ctx.guild.id, member_id
        )
        return await ctx.success(f"The author of confession #{confession} is muted")

    @confessions.command(
        name="unmute",
        brief="unmute a member that sent a specified confession",
        example="confessions unmute @sudosql",
    )
    @has_permissions(manage_messages=True)
    async def connfessions_unmute(self, ctx: Context, *, confession: str):
        check = await self.bot.db.fetchrow(
            "SELECT channel_id FROM confess WHERE guild_id = $1", ctx.guild.id
        )

        if check is None:
            return await ctx.warning("Confessions aren't **enabled** in this server")

        if confession == "all":
            await self.bot.db.execute(
                "DELETE FROM confess_mute WHERE guild_id = $1", ctx.guild.id
            )
            return await ctx.success("Unmuted **all** confession muted authors")

        num = int(confession)
        re = await self.bot.db.fetchrow(
            "SELECT * FROM confess_members WHERE guild_id = $1 AND confession = $2",
            ctx.guild.id,
            num,
        )

        if re is None:
            return await ctx.warning("Couldn't find that confession")

        member_id = re["user_id"]
        r = await self.bot.db.fetchrow(
            "SELECT * FROM confess_mute WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member_id,
        )

        if not r:
            return await ctx.warning("This **member** is **not** confession muted")

        await self.bot.db.execute(
            "DELETE FROM confess_mute WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member_id,
        )
        return await ctx.success(f"Unmuted the author of confession #{confession}")

    @confessions.command(
        name="setup",
        aliases=["add"],
        brief="Set the channel confessions will be sent to",
        example=",confessions setup #confess",
    )
    @has_permissions(manage_guild=True)
    async def confessions_add(self, ctx: Context, *, channel: TextChannel):
        """set the confessions channel"""
        check = await self.bot.db.fetchrow(
            "SELECT * FROM confess WHERE guild_id = $1", ctx.guild.id
        )
        if check is not None:
            await self.bot.db.execute(
                "UPDATE confess SET channel_id = $1 WHERE guild_id = $2",
                channel.id,
                ctx.guild.id,
            )
        elif check is None:
            await self.bot.db.execute(
                "INSERT INTO confess VALUES ($1,$2,$3)", ctx.guild.id, channel.id, 0
            )

        return await ctx.success(
            f"confession channel set to {channel.mention}".capitalize()
        )

    @confessions.command(
        name="reset",
        aliases=["disable", "delete"],
        brief="Remove and disable the confessions module",
        example=",confessions reset",
    )
    @has_permissions(manage_guild=True)
    async def confessions_remove(self, ctx: Context):
        """disable the confessions module"""
        check = await self.bot.db.fetchrow(
            "SELECT channel_id FROM confess WHERE guild_id = $1", ctx.guild.id
        )

        if check is None:
            return await ctx.warning("Confessions aren't **enabled** in this server")

        await self.bot.db.execute(
            "DELETE FROM confess WHERE guild_id = $1", ctx.guild.id
        )
        await self.bot.db.execute(
            "DELETE FROM confess_members WHERE guild_id = $1", ctx.guild.id
        )
        await self.bot.db.execute(
            "DELETE FROM confess_mute WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.success("Confessions disabled")

    @confessions.command(
        name="channel",
        brief="view statistics relating confessions",
        example=",confessions channel",
    )
    async def confessions_channel(self, ctx: Context):
        """get the confessions channel"""
        check = await self.bot.db.fetchrow(
            "SELECT * FROM confess WHERE guild_id = $1", ctx.guild.id
        )

        if check is not None:
            channel = ctx.guild.get_channel(check["channel_id"])
            embed = Embed(
                color=self.bot.color,
                description=f"confession channel: {channel.mention}\nconfessions sent: **{check['confession']}**",
            )
            return await ctx.reply(embed=embed)
        return await ctx.warning("Confessions aren't **enabled** in this server")

    @app_commands.command()
    async def confess(self, interaction: Interaction):
        """anonymously confess your thoughts"""
        if interaction.guild is None:
            return await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )

        re = await self.bot.db.fetchrow(
            "SELECT * FROM confess_mute WHERE guild_id = $1 AND user_id = $2",
            interaction.guild.id,
            interaction.user.id,
        )

        if re:
            await interaction.response.send_message(
                "You are **muted** from sending confessions in this server",
                ephemeral=True,
            )

        check = await self.bot.db.fetchrow(
            "SELECT channel_id FROM confess WHERE guild_id = $1", interaction.guild.id
        )
        if check:
            return await interaction.response.send_modal(ConfessionModel())

        return await interaction.response.send_message(
            "Confessions aren't enabled in this server", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Confessions(bot))
