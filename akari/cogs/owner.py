import asyncio
import datetime
import importlib
import json
import os

import discord
from discord import Guild, Member, User
from discord.ext import tasks
from discord.ext.commands import Cog, command, group, is_owner
from jishaku.codeblocks import codeblock_converter
from tools.bot import Akari
from tools.helpers import AkariContext


class Owner(Cog):
    def __init__(self, bot: Akari):
        self.bot = bot

    async def add_donor_role(self, member: User):
        """add the donor role to a donator"""
        guild = self.bot.get_guild(950153022405763124)
        user = guild.get_member(member.id)
        if user:
            role = guild.get_role(1274564894997610568)
            await user.add_roles(role, reason="member got donator perks")

    async def remove_donor_role(self, member: User):
        """remove the donator role from a donator"""
        guild = self.bot.get_guild(950153022405763124)
        user = guild.get_member(member.id)
        if user:
            role = guild.get_role(1274564894997610568)
            await user.remove_roles(role, reason="member got donator perks")

    @Cog.listener()
    async def on_member_join(self, member: Member):
        reason = await self.bot.db.fetchval(
            "SELECT reason FROM globalban WHERE user_id = $1", member.id
        )
        if reason:
            if member.guild.me.guild_permissions.ban_members:
                await member.ban(reason=reason)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id == 950153022405763124:
            check = await self.bot.db.fetchrow(
                "SELECT * FROM donor WHERE user_id = $1 AND status = $2",
                member.id,
                "boosted",
            )
            if check:
                await self.bot.db.execute(
                    "DELETE FROM donor WHERE user_id = $1", member.id
                )
                await self.bot.db.execute(
                    "DELETE FROM reskin WHERE user_id = $1", member.id
                )

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if before.guild.id == 950153022405763124:
            if (
                before.guild.premium_subscriber_role in before.roles
                and not before.guild.premium_subscriber_role in after.roles
            ):
                check = await self.bot.db.fetchrow(
                    "SELECT * FROM donor WHERE user_id = $1 AND status = $2",
                    before.id,
                    "boosted",
                )
                if check:
                    await self.bot.db.execute(
                        "DELETE FROM reskin WHERE user_id = $1", before.id
                    )
                    await self.bot.db.execute(
                        "DELETE FROM donor WHERE user_id = $1", before.id
                    )

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM blacklist WHERE id = $1 AND type = $2", guild.id, "server"
        )
        if check:
            await guild.leave()

    @command(aliases=["py"])
    @is_owner()
    async def eval(self, ctx: AkariContext, *, argument: codeblock_converter):
        return await ctx.invoke(self.bot.get_command("jsk py"), argument=argument)

    @command()
    @is_owner()
    async def restart(self, ctx: AkariContext):
        await ctx.reply("restarting the bot...")
        os.system("pm2 restart 0")

    @command()
    @is_owner()
    async def portal(self, ctx: AkariContext, id: int):

        guild = self.bot.get_guild(id)

        if guild is None:
            return await ctx.warning(f"I could not find a a guild for ``{id}``.")

        embed = discord.Embed(
            description=f"> The invite for ``{ctx.guild.name}`` is listed above.",
            color=self.bot.color,
        )

        for c in guild.text_channels:

            if c.permissions_for(guild.me).create_instant_invite:
                invite = await c.create_invite()

                await ctx.author.send(f"{invite}", embed=embed)
                break

    @command()
    @is_owner()
    async def anowner(self, ctx: AkariContext, guild: Guild, member: User):
        """change the antinuke owner in case the real owner cannot access discord"""
        if await self.bot.db.fetchrow(
            "SELECT * FROM antinuke WHERE guild_id = $1", guild.id
        ):
            await self.bot.db.execute(
                "UPDATE antinuke SET owner_id = $1 WHERE guild_id = $2",
                member.id,
                guild.id,
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO antinuke (guild_id, configured, owner_id) VALUES ($1,$2,$3)",
                guild.id,
                "false",
                member.id,
            )
        return await ctx.success(
            f"{member.mention} is the **new** antinuke owner for **{guild.name}**"
        )

    @command()
    @is_owner()
    async def guilds(self, ctx: AkariContext):
        """all guilds the bot is in, sorted from the biggest to the smallest"""
        servers = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        return await ctx.paginate(
            [f"{g.name} - {g.member_count:,} members" for g in servers],
            "Akari's servers",
        )

    @group(invoke_without_command=True)
    @is_owner()
    async def donor(self, ctx):
        await ctx.create_pages()

    @donor.command(name="add")
    @is_owner()
    async def donor_add(self, ctx: AkariContext, *, member: User):
        """add donator perks to a member"""

        check = await self.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = $1", member.id
        )

        if check:
            return await ctx.error("This member is **already** a donor")

        await self.add_donor_role(member)

        await self.bot.db.execute(
            "INSERT INTO donor VALUES ($1,$2,$3)",
            member.id,
            datetime.datetime.now().timestamp(),
            "purchased",
        )

        return await ctx.success(f"{member.mention} can use donator perks now!")

    @donor.command(name="remove")
    @is_owner()
    async def donor_remove(self, ctx: AkariContext, *, member: User):
        """Remove donator perks from a member"""

        check = await self.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = $1 AND status = $2",
            member.id,
            "purchased",
        )

        if not check:
            return await ctx.error("This member cannot have their perks removed")

        await self.remove_donor_role(member)
        await self.bot.db.execute("DELETE FROM donor WHERE user_id = $1", member.id)

        return await ctx.success(f"Removed {member.mention}'s perks")

    @command()
    @is_owner()
    async def mutuals(self, ctx: AkariContext, *, user: User):
        """Returns mutual servers between the member and the bot"""

        if len(user.mutual_guilds) == 0:

            return await ctx.reply(
                f"This member doesn't share any server with {self.bot.user.name}"
            )

        await ctx.paginate(
            [f"{g.name} ({g.id})" for g in user.mutual_guilds],
            f"Mutual guilds ({len(user.mutual_guilds)})",
            {"name": user.name, "icon_url": user.display_avatar.url},
        )

    @command(name="globalenable")
    @is_owner()
    async def globalenable(self, ctx: AkariContext, cmd: str = ""):
        """
        Globally enable a command.
        """

        if not cmd:
            return await ctx.warning("Please provide a command to enable.")

        if cmd in ["*", "all", "ALL"]:

            await self.bot.db.execute("DELETE FROM global_disabled_cmds;")
            return await ctx.success(f"All commands have been globally enabled.")

        if not self.bot.get_command(cmd):

            return await ctx.warning("Command does not exist.")

        cmd = self.bot.get_command(cmd).name

        await self.bot.db.execute(
            "DELETE FROM global_disabled_cmds WHERE cmd = $1;", cmd
        )

        return await ctx.success(f"The command {cmd} has been globally enabled.")

    @command(name="globaldisable")
    @is_owner()
    async def globaldisable(self, ctx: AkariContext, cmd: str = ""):
        """
        Globally disable a command.
        """
        if not cmd:
            return await ctx.warning("Please provide a command to disable.")

        if cmd in ["globalenable", "globaldisable"]:
            return await ctx.warning("Unable to globally disable this command.")

        if not self.bot.get_command(cmd):
            return await ctx.warning("Command does not exist.")

        cmd = self.bot.get_command(cmd).name
        result = await self.bot.db.fetchrow(
            "SELECT disabled FROM global_disabled_cmds WHERE cmd = $1;", cmd
        )

        if result:
            if result.get("disabled"):
                return await ctx.warning("This command is already globally disabled.")

        await self.bot.db.execute(
            "INSERT INTO global_disabled_cmds (cmd, disabled, disabled_by) VALUES ($1, $2, $3) "
            "ON CONFLICT (cmd) DO UPDATE SET disabled = EXCLUDED.disabled, disabled_by = EXCLUDED.disabled_by;",
            cmd,
            True,
            str(ctx.author.id),
        )

        return await ctx.success(f"The command {cmd} has been globally disabled.")

    @command(name="globaldisabledlist", aliases=["gdl"])
    @is_owner()
    async def globaldisabledlist(self, ctx: AkariContext):
        """
        Show all commands that are globally disabled.
        """

        global_disabled_cmds = await self.bot.db.fetch(
            "SELECT * FROM global_disabled_cmds;"
        )

        if len(global_disabled_cmds) <= 0:
            return await ctx.warning("There are no globally disabled commands.")

        disabled_list = [
            f"{obj.get('cmd')} - disabled by <@{obj.get('disabled_by')}>"
            for obj in global_disabled_cmds
        ]

        return await ctx.paginate(
            disabled_list,
            f"Globally Disabled Commands:",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @command(aliases=["trace"])
    async def error(self, ctx: AkariContext, code: str):
        """
        View information about an error code
        """

        if not ctx.author.id in self.bot.owner_ids:
            return await ctx.warning("You are not authorized to use this command.")

        fl = await self.bot.db.fetch("SELECT * FROM error_codes;")
        error_details = [x for x in fl if x.get("code") == code]

        if len(error_details) == 0 or len(code) != 6:
            return await ctx.warning("Please provide a **valid** error code")

        error_details = error_details[0]
        error_details = json.loads(error_details.get("info"))

        guild = self.bot.get_guild(error_details["guild_id"])

        embed = (
            discord.Embed(description=str(error_details["error"]), color=self.bot.color)
            .add_field(name="Guild", value=f"{guild.name}\n`{guild.id}`", inline=True)
            .add_field(
                name="Channel",
                value=f"<#{error_details['channel_id']}>\n`{error_details['channel_id']}`",
                inline=True,
            )
            .add_field(
                name="User",
                value=f"<@{error_details['user_id']}>\n`{error_details['user_id']}`",
                inline=True,
            )
            .add_field(name="Command", value=f"**{error_details['command']}**")
            .add_field(name="Timestamp", value=f"{error_details['timestamp']}")
            .set_author(name=f"Error Code: {code}")
        )

        return await ctx.reply(embed=embed)

    @command(aliases=["gban"])
    @is_owner()
    async def globalban(
        self,
        ctx: AkariContext,
        user: User,
        *,
        reason: str = "Globally banned by a bot owner",
    ):
        """Ban an user globally"""

        if user.id in [598125772754124823, 863914425445908490]:
            return await ctx.error("Do not global ban a bot owner, retard")

        check = await self.bot.db.fetchrow(
            "SELECT * FROM globalban WHERE user_id = $1", user.id
        )
        if check:
            await self.bot.db.execute(
                "DELETE FROM globalban WHERE user_id = $1", user.id
            )
            return await ctx.success(
                f"{user.mention} was succesfully globally unbanned"
            )

        mutual_guilds = len(user.mutual_guilds)

        tasks = [
            g.ban(user, reason=reason)
            for g in user.mutual_guilds
            if g.me.guild_permissions.ban_members
            and g.me.top_role > g.get_member(user.id).top_role
            and g.owner_id != user.id
        ]

        await asyncio.gather(*tasks)
        await self.bot.db.execute(
            "INSERT INTO globalban VALUES ($1,$2)", user.id, reason
        )

        return await ctx.success(
            f"{user.mention} was succesfully global banned in {len(tasks)}/{mutual_guilds} servers"
        )

    @group(invoke_without_command=True)
    @is_owner()
    async def blacklist(self, ctx):
        await ctx.create_pages()

    @blacklist.command(name="user")
    @is_owner()
    async def blacklist_user(self, ctx: AkariContext, *, user: User):
        """blacklist or unblacklist a member"""

        if user.id in self.bot.owner_ids:
            return await ctx.error("Do not blacklist a bot owner, retard")

        try:
            await self.bot.db.execute(
                "INSERT INTO blacklist VALUES ($1,$2)", user.id, "user"
            )
            return await ctx.success(f"Blacklisted {user.mention} from Akari")

        except:
            await self.bot.db.execute("DELETE FROM blacklist WHERE id = $1", user.id)
            return await ctx.success(f"Unblacklisted {user.mention} from Akari")

    @blacklist.command(name="server")
    @is_owner()
    async def blacklist_server(self, ctx: AkariContext, *, server_id: int):
        """blacklist a server"""
        if server_id in [950153022405763124]:
            return await ctx.error("Cannot blacklist this server")

        try:
            await self.bot.db.execute(
                "INSERT INTO blacklist VALUES ($1,$2)", server_id, "server"
            )

            guild = self.bot.get_guild(server_id)
            if guild:
                await guild.leave()
            return await ctx.success(f"Blacklisted server {server_id} from Akari")

        except:
            await self.bot.db.execute("DELETE FROM blacklist WHERE id = $1", server_id)
            return await ctx.success(f"Unblacklisted server {server_id} from Akari")

    @command(name="reload", aliases=["rl"])
    @is_owner()
    async def reload(self, ctx: AkariContext, *, module: str):
        """
        Reload a module
        """

        reloaded = []
        if module.endswith(" --pull"):
            os.system("git pull")
        module = module.replace(" --pull", "")

        if module == "~":
            for module in list(self.bot.extensions):
                try:
                    await self.bot.reload_extension(module)
                except Exception as e:
                    return await ctx.warning(f"Couldn't reload **{module}**\n```{e}```")
                reloaded.append(module)

                return await ctx.success(f"Reloaded **{len(reloaded)}** modules")
        else:
            module = module.replace("%", "cogs").replace("!", "tools").strip()
            if module.startswith("cogs"):
                try:
                    await self.bot.reload_extension(module)
                except Exception as e:
                    return await ctx.warning(f"Couldn't reload **{module}**\n```{e}```")
            else:
                try:
                    _module = importlib.import_module(module)
                    importlib.reload(_module)
                except Exception as e:
                    return await ctx.warning(f"Couldn't reload **{module}**\n```{e}```")
            reloaded.append(module)

        await ctx.success(
            f"Reloaded **{reloaded[0]}**"
            if len(reloaded) == 1
            else f"Reloaded **{len(reloaded)}** modules"
        )


async def setup(bot: Akari) -> None:
    await bot.add_cog(Owner(bot))
