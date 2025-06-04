import asyncpg
import discord
from config import color, emoji
from discord.ext import commands
from system.base.context import Context


class Events(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        ignored = (commands.CommandNotFound,)

        if isinstance(error, ignored):
            return

        skip = (
            commands.MissingRequiredArgument,
            commands.MissingPermissions,
            commands.BotMissingPermissions,
            commands.MemberNotFound,
            commands.BadArgument,
            commands.MissingRequiredArgument,
            commands.BadUnionArgument,
            commands.BotMissingPermissions,
            commands.CommandOnCooldown,
            commands.TooManyArguments,
            commands.ChannelNotFound,
            commands.UserNotFound,
            commands.RoleNotFound,
            commands.EmojiNotFound,
        )

        if not isinstance(error, skip):
            try:
                err_msg = f"{type(error).__name__}: {error}"
                err_id = await self.client.get_cog("Developer").log_error(err_msg)

                await ctx.warn(
                    f"Uh oh, an **error** occurred join the [support server](https://discord.gg/strict) to get help \n> Error ID: ```{err_id}```"
                )

                channel = self.client.get_channel(1294659379303415878)
                if channel:
                    embed = discord.Embed(
                        description=f"> Error ID: `{err_id}` \n```{err_msg}```",
                        color=color.default,
                    )
                    embed.set_footer(
                        text=f"Occurred in {ctx.guild.name} ({ctx.guild.id})"
                    )
                    embed.set_thumbnail(
                        url=ctx.guild.icon.url if ctx.guild.icon else None
                    )
                    user_pfp = (
                        ctx.author.avatar.url
                        if ctx.author.avatar
                        else ctx.author.default_avatar.url
                    )
                    embed.set_author(
                        name=f"{ctx.author.name} | Error Occurred", icon_url=user_pfp
                    )
                    await channel.send(embed=embed)

            except Exception as e:
                await ctx.deny("Could **not** log the error")

        if isinstance(error, commands.CommandOnCooldown):
            cmd = ctx.command.name
            time = error.retry_after
            await ctx.deny(f"**{cmd}** is on cooldown, try again in `{time:.2f}s`")

        elif isinstance(error, commands.MissingPermissions):
            perms = (
                format(error.missing_permissions)
                .replace("[", "")
                .replace("'", "")
                .replace("]", "")
                .replace("_", " ")
            )
            await ctx.deny(f"You're **missing** `{perms}` permission(s)")

        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.deny(f"I'm **missing** `{perms}` to execute that command")

        elif isinstance(error, commands.BadArgument):
            await ctx.deny(
                f"**Invalid** argument \n> ```{type(error).__name__}: {error}```"
            )

        elif isinstance(error, commands.BadUnionArgument):
            await ctx.deny(
                f"**Invalid** union argument \n> ```{type(error).__name__}: {error}```"
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.deny(
                f"**Missing** a required argument \n> ```{error.param.name}```"
            )

        elif isinstance(error, commands.TooManyArguments):
            await ctx.deny("Too **many** arguments provided")

        elif isinstance(error, commands.ChannelNotFound):
            await ctx.deny("**Could not** find the channel")

        elif isinstance(error, commands.UserNotFound):
            await ctx.deny("**Could not** find the user")

        elif isinstance(error, commands.RoleNotFound):
            await ctx.deny("**Could not** find the role")

        elif isinstance(error, commands.EmojiNotFound):
            await ctx.deny("**Could not** find the emoji")

        elif isinstance(error, commands.MemberNotFound):
            await ctx.deny("**Could not** find the user")

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.client.get_context(message)

        if message.author == self.client.user or not ctx:
            return

        if self.client.user.mentioned_in(message) and message.content.strip() in [
            f"<@{self.client.user.id}>",
            f"<@!{self.client.user.id}>",
        ]:
            if message.mention_everyone:
                return
            if isinstance(message.channel, discord.DMChannel):
                return

            user_id = str(message.author.id)
            result = await self.client.pool.fetchrow(
                "SELECT prefix FROM prefixes WHERE user_id = $1", user_id
            )
            prefix = result["prefix"] if result else ";"

            embed = discord.Embed(
                description=f"> <a:repent_iii:1298392198076694559> {message.author.mention}: **Selfprefix:** `{prefix}`",
                color=color.default,
            )
            await message.channel.send(embed=embed)


async def setup(client):
    await client.add_cog(Events(client))
