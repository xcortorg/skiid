import discord
from discord.ext import commands
from managers.bot import Luma
from managers.handlers.embed import Script
from managers.helpers import Context
from managers.validators import (RoleConvert, ValidAlias, ValidCommand,
                                 ValidPermission)


class Config(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot

    @commands.command(aliases=["ce"])
    async def createembed(self: "Config", ctx: Context, *, code: Script):
        """
        Create an embed using the embed parser
        """
        await ctx.send(**code)

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix(self: "Config", ctx: Context, *, prefix: str):
        """
        Update the bot prefix for your guild
        """

        if len(prefix) > 7:
            return await ctx.error("This prefix is too long")

        await self.bot.db.execute(
            """INSERT INTO prefix VALUES ($1,$2)
      ON CONFLICT (guild_id) DO UPDATE SET
      prefix = $2""",
            ctx.guild.id,
            prefix,
        )
        await ctx.confirm(f"Guild prefix changed to `{prefix}`")

    @commands.group(invoke_without_command=True, aliases=["fakeperms", "fp"])
    async def fakepermissions(self: "Config", ctx: Context):
        """
        Allow members to have permissions strictly on the bot
        """
        return await ctx.send_help(ctx.command)

    @fakepermissions.command(name="remove")
    @commands.has_guild_permissions(administrator=True)
    async def fakeperms_remove(
        self: "Config", ctx: Context, permission: ValidPermission, *, role: RoleConvert
    ):
        """
        Remove a permission from a role
        """

        permissions = (
            await self.bot.db.fetchval(
                "SELECT permissions FROM fakeperms WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )
            or []
        )

        if not permission in permissions:
            return await ctx.error(
                "This permission is **not** in this role's permissions list"
            )

        permissions.remove(permission)
        await self.bot.db.execute(
            "UPDATE fakeperms SET permissions = $1 WHERE guild_id = $2 AND role_id = $3",
            permissions,
            ctx.guild.id,
            role.id,
        )
        await ctx.confirm(f"Removed `{permission}` from {role.mention}'s permissions")

    @fakepermissions.command(name="add")
    @commands.has_guild_permissions(administrator=True)
    async def fakeperms_add(
        self: "Config", ctx: Context, permission: ValidPermission, *, role: RoleConvert
    ):
        """
        Add a permission to a role
        """

        permissions = (
            await self.bot.db.fetchval(
                "SELECT permissions FROM fakeperms WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )
            or []
        )

        if permission in permissions:
            return await ctx.error("This permission is **already** added to this role")

        permissions.append(permission)
        await self.bot.db.execute(
            """
      INSERT INTO fakeperms VALUES ($1,$2,$3)
      ON CONFLICT (guild_id, role_id) DO UPDATE SET 
      permissions = $3 
      """,
            ctx.guild.id,
            role.id,
            permissions,
        )

        await ctx.confirm(
            f"Added `{permission}` to the {role.mention}'s fake permissions"
        )

    @commands.group(invoke_without_command=True)
    async def alias(self: "Config", ctx: Context):
        """
        Allow custom aliases for commands
        """
        return await ctx.send_help(ctx.command)

    @alias.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    async def alias_add(
        self: "Config", ctx: Context, alias: ValidAlias, command: ValidCommand
    ):
        """
        Add an alias for a command
        """

        check = await self.bot.db.execute(
            """
      INSERT INTO aliases VALUES ($1,$2,$3)
      ON CONFLICT (guild_id, alias)
      DO NOTHING
      """,
            ctx.guild.id,
            alias,
            command,
        )
        if check == "INSERT 0 0":
            return await ctx.error("This is already an existing alias")

        await ctx.confirm(f"Added `{alias}` as an alias for **{command}** command")

    @alias.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def alias_remove(self: "Config", ctx: Context, alias: str):
        """
        Remove an alias from a command
        """
        check = await self.bot.db.execute(
            "DELETE FROM aliases WHERE guild_id = $1 AND alias = $2",
            ctx.guild.id,
            alias,
        )
        if check == "DELETE 0":
            return await ctx.error("This is not an alias")

        await ctx.confirm(f"Removed the alias `{alias}`")

    @alias.command(name="list")
    async def alias_list(self: "Config", ctx: Context):
        """
        A list with the aliases in this server
        """
        results = await self.bot.db.fetch(
            "SELECT * FROM aliases WHERE guild_id = $1", ctx.guild.id
        )

        if not results:
            return await ctx.error("This server doesnt have any aliases")

        await ctx.paginate(
            [
                f"**{result['alias']}** is an alias for **{result['command']}**"
                for result in results
            ],
            title=f"Aliases ({len(results)})",
        )

    @commands.group(invoke_without_command=True)
    async def autorole(self: "Config", ctx: Context):
        """
        Give roles to people that joins ur server
        """
        return await ctx.send_help(ctx.command)

    @autorole.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    async def autorole_add(self: "Config", ctx: Context, *, role: RoleConvert):
        """
        Add a role to autorole
        """
        if await self.bot.db.fetchrow(
            "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        ):
            return await ctx.error("U already added this dummy")

        await self.bot.db.execute(
            "INSERT INTO autorole VALUES ($1,$2)", ctx.guild.id, role.id
        )
        await ctx.confirm(f"Added {role.mention} to autorole")

    @autorole.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def autorole_remove(self: "Config", ctx: Context, *, role: RoleConvert):
        """
        Remove a role from autorole
        """
        if not await self.bot.db.fetchrow(
            "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        ):
            return await ctx.error("This role is not added")

        await self.bot.db.execute(
            "DELETE FROM autorole WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        )
        await ctx.confirm(f"Removed {role.mention} from autorole")

    @autorole.command(name="list")
    async def autorole_list(self: "Config", ctx: Context):
        """
        Get a list of autoroles
        """
        results = await self.bot.db.fetch(
            "SELECT * FROM autorole WHERE guild_id = $1", ctx.guild.id
        )
        if not results:
            return await ctx.error("This server doesnt have any autoroles")

        await ctx.paginate(
            [f"<@&{role['role_id']}> - `({role['role_id']})`" for role in results],
            title=f"Autoroles ({len(results)})",
        )

    @commands.group(invoke_without_command=True, aliases=["poj"])
    async def pingonjoin(self: "Config", ctx: Context):
        """
        Ping the user that joins ur server in a channel
        """
        return await ctx.send_help(ctx.command)

    @pingonjoin.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    async def poj_add(self: "Config", ctx: Context, *, channel: discord.TextChannel):
        """
        Add a channel to ping the users when they join
        """
        if await self.bot.db.fetchrow(
            "SELECT * FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            return await ctx.error("This channel is already added")

        await self.bot.db.execute(
            "INSERT INTO pingonjoin VALUES ($1,$2)", ctx.guild.id, channel.id
        )
        await ctx.confirm(f"Added {channel.mention} to poj")

    @pingonjoin.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def poj_remove(self: "Config", ctx: Context, *, channel: discord.TextChannel):
        """
        Remove a channel from poj
        """
        if not await self.bot.db.fetchrow(
            "SELECT * FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            return await ctx.error("This channel is not added")

        await self.bot.db.execute(
            "DELETE FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        await ctx.confirm(f"Removed {channel.mention} from poj")

    @pingonjoin.command(name="list")
    async def poj_list(self: "Config", ctx: Context):
        """
        See a list where people get pinged
        """
        results = await self.bot.db.fetch(
            "SELECT * FROM pingonjoin WHERE guild_id = $1", ctx.guild.id
        )
        if not results:
            return await ctx.error("There are no poj channels")

        await ctx.paginate(
            [f"<#{result['channel_id']}>" for result in results],
            title=f"Pingonjoin ({len(results)})",
        )

    @commands.group(invoke_without_command=True, aliases=["ar"])
    async def autoresponder(self: "Config", ctx: Context):
        """
        Add a response for a response
        """
        return await ctx.send_help(ctx.command)

    @autoresponder.command(name="add", usage="example ;ar add Luma, hi im luma")
    @commands.has_guild_permissions(manage_guild=True)
    async def ar_add(self: "Config", ctx: Context, *, response: str):
        """
        Add an autoresponder
        """
        args = response.split(",")
        if len(args) == 1:
            return await ctx.error("U forgot to put `,` dummy")

        trigger = args[0].strip()
        if trigger == "":
            return await ctx.error("No trigger ???")

        responsee = args[1].strip()

        await self.bot.db.execute(
            """
      INSERT INTO autoresponder VALUES ($1,$2,$3)
      ON CONFLICT (guild_id, trigger) DO UPDATE SET 
      response = $3 
      """,
            ctx.guild.id,
            trigger.lower(),
            responsee,
        )
        await ctx.confirm(
            f"Added trigger `{trigger.lower()}` and response `{responsee}`"
        )

    @autoresponder.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def ar_remove(self: "Config", ctx: Context, *, trigger: str):
        """
        Remove an autoresponder
        """
        if not await self.bot.db.fetchrow(
            "SELECT * FROM autoresponder WHERE guild_id = $1 AND trigger = $2",
            ctx.guild.id,
            trigger,
        ):
            return await ctx.error("This trigger doesnt exists")

        await self.bot.db.execute(
            "DELETE FROM autoresponder WHERE guild_id = $1 AND trigger = $2",
            ctx.guild.id,
            trigger,
        )
        await ctx.confirm(f"Removed autoresponder for trigger `{trigger}`")

    @autoresponder.command(name="list")
    async def ar_list(self: "Config", ctx: Context):
        """
        See a list with autoresponders for this server
        """
        results = await self.bot.db.fetch(
            "SELECT * FROM autoresponder WHERE guild_id = $1", ctx.guild.id
        )
        if not results:
            return await ctx.error("This server has no autoresponders")

        await ctx.paginate(
            [f"{result['trigger']} - {result['response']}" for result in results],
            title=f"Autoresponders ({len(results)})",
        )

    @commands.command(aliases=["disablecmd"])
    @commands.has_guild_permissions(manage_guild=True)
    async def disablecommand(self: "Config", ctx: Context, *, command: ValidCommand):
        """
        Disable a command in the server
        """
        if await self.bot.db.fetchrow(
            "SELECT * FROM disablecmd WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.error("This command is already disabled")

        await self.bot.db.execute(
            "INSERT INTO disablecmd VALUES ($1,$2)", ctx.guild.id, command
        )
        await ctx.confirm(f"Disabled **{command}**")

    @commands.command(aliases=["enablecmd"])
    @commands.has_guild_permissions(manage_guild=True)
    async def enablecommand(self: "Config", ctx: Context, *, command: ValidCommand):
        """
        Enable a disabled command
        """
        if not await self.bot.db.fetchrow(
            "SELECT * FROM disablecmd WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.error("This command is not disabled")

        await self.bot.db.execute(
            "DELETE FROM disablecmd WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            command,
        )
        await ctx.confirm(f"Enabled **{command}**")


async def setup(bot: Luma):
    return await bot.add_cog(Config(bot))
