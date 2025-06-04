import datetime
import json
import traceback
from typing import Union

import discord
from discord import (ChannelType, Embed, Interaction, Member, Message,
                     PartialEmoji, PermissionOverwrite, Role, SelectOption,
                     TextChannel, User)
from discord.ext.commands import AutoShardedBot as AB
from discord.ext.commands import (Cog, Context, command, group,
                                  has_guild_permissions, hybrid_command,
                                  hybrid_group)
from discord.ui import Button, Select, View
from get.checks import Boosts
from get.checks import Perms as utils
from get.pretend import Pretend, PretendContext
from get.utils import EmbedBuilder, EmbedScript, InvokeClass


async def dm_cmds(ctx: Context, embed: str) -> Message:
    res = await ctx.bot.db.fetchrow(
        "SELECT embed FROM dm WHERE guild_id = $1 AND command = $2",
        ctx.guild.id,
        ctx.command.name,
    )
    if res:
        name = res["embed"]
        if embed == "none":
            await ctx.bot.db.execute(
                "DELETE FROM dm WHERE guild_id = $1 AND command = $2",
                ctx.guild.id,
                ctx.command.name,
            )
            return await ctx.send_success(
                f"Deleted the **{ctx.command.name}** custom response"
            )
        elif embed == "view":
            em = Embed(
                color=ctx.bot.color,
                title=f"dm {ctx.command.name} message",
                description=f"```{name}```",
            )
            return await ctx.reply(embed=em)
        elif embed == name:
            return await ctx.send_warning(
                f"This embed is already **configured** as the {ctx.command.name} custom dm"
            )
        else:
            await ctx.bot.db.execute(
                "UPDATE dm SET embed = $1 WHERE guild_id = $2 AND command = $3",
                embed,
                ctx.guild.id,
                ctx.command.name,
            )
            return await ctx.send_success(
                f"Updated your custom **{ctx.command.name}** message to\n```{embed}```"
            )
    else:
        await ctx.bot.db.execute(
            "INSERT INTO dm VALUES ($1,$2,$3)", ctx.guild.id, ctx.command.name, embed
        )
        return await ctx.send_success(
            f"Added your custom **{ctx.command.name}** direct message to\n```{embed}```"
        )


class Config(Cog):
    def __init__(self, bot: AB):
        self.bot = bot

    def is_dangerous(self, role: discord.Role) -> bool:
        permissions = role.permissions
        return any(
            [
                permissions.kick_members,
                permissions.ban_members,
                permissions.administrator,
                permissions.manage_channels,
                permissions.manage_guild,
                permissions.manage_messages,
                permissions.manage_roles,
                permissions.manage_webhooks,
                permissions.manage_emojis_and_stickers,
                permissions.manage_threads,
                permissions.mention_everyone,
                permissions.moderate_members,
            ]
        )

    @group(invoke_without_command=True)
    async def autopfp(self, ctx):
        await ctx.create_pages()

    @autopfp.command(help="config", description="shows variables for the autopost")
    async def genres(self, ctx: Context):
        embed = Embed(color=self.bot.color, title="autoimages related genres")
        embed.add_field(name="autopfp", value=">>> male\nfemale\nanime\nrandom\nbanner")
        embed.add_field(name="autogif", value=">>> male\nfemale\nanime\nrandom")
        await ctx.reply(embed=embed)

    @autopfp.command(
        name="clear",
        description="clear the whole autopfp module",
        help="config",
        brief="manage server",
    )
    @utils.get_perms("manage_guild")
    async def autopfp_clear(self, ctx: Context):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM autopfp WHERE guild_id = $1", ctx.guild.id
        )
        if not check:
            return await ctx.send_warning("Autopfp module is **not** configured")
        embed = Embed(
            color=self.bot.color,
            description="Are you sure you want to clear the autopfps module?",
        )
        yes = Button(emoji=self.bot.yes)
        no = Button(emoji=self.bot.no)

        async def yes_callback(interaction: Interaction):
            if interaction.user.id != ctx.author.id:
                return await self.bot.ext.send_warning(
                    interaction,
                    "You are not the **author** of this embed",
                    ephemeral=True,
                )
            await self.bot.db.execute(
                "DELETE FROM autopfp WHERE guild_id = $1", ctx.guild.id
            )
            return await interaction.response.edit_message(
                embed=Embed(color=self.bot.color, description="Autopfp module cleared"),
                view=None,
            )

        async def no_callback(interaction: Interaction):
            if interaction.user.id != ctx.author.id:
                return await self.bot.ext.send_warning(
                    interaction,
                    "You are not the **author** of this embed",
                    ephemeral=True,
                )
            return await interaction.response.edit_message(
                embed=Embed(color=self.bot.color, description="aborting action..."),
                view=None,
            )

        yes.callback = yes_callback
        no.callback = no_callback
        view = View()
        view.add_item(yes)
        view.add_item(no)
        return await ctx.reply(embed=embed, view=view)

    @autopfp.command(
        name="add",
        description="add the autopfp module",
        help="config",
        usage="[channel] [genre] [type]\nexample: autopfp add #boys male pfp",
        brief="manage guild",
    )
    @utils.get_perms("manage_guild")
    async def autopfp_add(
        self, ctx: Context, channel: TextChannel, genre: str, typ: str = "none"
    ):
        try:
            if genre in ["female", "male", "anime"]:
                if typ in ["pfp", "gif"]:
                    check = await self.bot.db.fetchrow(
                        "SELECT * FROM autopfp WHERE guild_id = $1 AND genre = $2 AND type = $3",
                        ctx.guild.id,
                        genre,
                        typ,
                    )
                    if check is not None:
                        return await ctx.send_warning(
                            f"A channel is already **configured** for {genre} {typ}s"
                        )
                    await self.bot.db.execute(
                        "INSERT INTO autopfp VALUES ($1,$2,$3,$4)",
                        ctx.guild.id,
                        channel.id,
                        genre,
                        typ,
                    )
                    return await ctx.send_success(
                        f"Configured {channel.mention} as {genre} {typ}s"
                    )
                else:
                    return await ctx.send_warning(
                        "The **type** passed wasn't one of the following: pfp, gif"
                    )
            elif genre in ["random", "banner"]:
                check = await self.bot.db.fetchrow(
                    "SELECT * FROM autopfp WHERE channel_id = $1 AND guild_id = $2 AND genre = $3",
                    channel.id,
                    ctx.guild.id,
                    genre,
                )
                if check is not None:
                    return await ctx.send_warning(
                        f"A channel is already **configured** for {genre}"
                    )
                await self.bot.db.execute(
                    "INSERT INTO autopfp VALUES ($1,$2,$3,$4)",
                    ctx.guild.id,
                    channel.id,
                    genre,
                    typ,
                )
                return await ctx.send_success(
                    f"Configured {channel.mention} as {genre} pictures"
                )
            else:
                return await ctx.send_error(
                    "The **genre** passed wasn't one of the following: male, female, anime, banner, random"
                )
        except:
            traceback.print_exc()

    @autopfp.command(
        name="remove",
        description="remove the autopfp module",
        help="config",
        usage="[genre] [type]\nexample: autopfp remove male gif",
        brief="manage guild",
    )
    @utils.get_perms("manage_guild")
    async def autopfp_remove(self, ctx: Context, genre: str, typ: str = "none"):
        try:
            check = await self.bot.db.fetchrow(
                "SELECT * FROM autopfp WHERE guild_id = $1 AND genre = $2 AND type = $3",
                ctx.guild.id,
                genre,
                typ,
            )
            if check is None:
                return await ctx.send_warning(
                    f"No autopfp channel found for **{genre} {typ if typ != 'none' else ''}**"
                )
            await self.bot.db.execute(
                "DELETE FROM autopfp WHERE guild_id = $1 AND genre = $2 AND type = $3",
                ctx.guild.id,
                genre,
                typ,
            )
            await ctx.send_success(
                f"Removed **{genre} {typ if typ != 'none' else ''}** posting"
            )
        except:
            traceback.print_exc()

    @group(invoke_without_command=True)
    async def mediaonly(self, ctx: Context):
        await ctx.create_pages()

    @mediaonly.command(
        name="add",
        description="delete messages that are not images",
        help="config",
        usage="[channel]",
        brief="manage_guild",
    )
    @utils.get_perms("manage_guild")
    async def mediaonly_add(self, ctx: Context, *, channel: TextChannel):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM mediaonly WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        if check is not None:
            return await ctx.send_warning(f"{channel.mention} is already added")
        elif check is None:
            await self.bot.db.execute(
                "INSERT INTO mediaonly VALUES ($1,$2)", ctx.guild.id, channel.id
            )
            return await ctx.send_success(
                f"added {channel.mention} as a mediaonly channel"
            )

    @mediaonly.command(
        name="remove",
        description="unset media only",
        help="config",
        usage="[channel]",
        brief="manage_guild",
    )
    @utils.get_perms("manage_guild")
    async def mediaonly_remove(self, ctx: Context, *, channel: TextChannel = None):
        if channel is not None:
            check = await self.bot.db.fetchrow(
                "SELECT * FROM mediaonly WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id,
                channel.id,
            )
            if check is None:
                return await ctx.send_warning(f"{channel.mention} is not added")
            await self.bot.db.execute(
                "DELETE FROM mediaonly WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id,
                channel.id,
            )
            return await ctx.send_success(
                f"{channel.mention} isn't a **mediaonly** channel anymore"
            )

        res = await self.bot.db.fetch(
            "SELECT * FROM mediaonly WHERE guild_id = $1", ctx.guild.id
        )
        if res is None:
            return await ctx.send_warning(
                "There is no **mediaonly** channel in this server"
            )
        await self.bot.db.execute(
            "DELETE FROM mediaonly WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.send_success("Removed all channels")

    @mediaonly.command(
        name="list", description="return a list of mediaonly channels", help="config"
    )
    async def mediaonly_list(self, ctx: Context):
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        results = await self.bot.db.fetch(
            "SELECT * FROM mediaonly WHERE guild_id = {}".format(ctx.guild.id)
        )
        if len(results) == 0:
            return await ctx.reply("there are no mediaonly channels")
        for result in results:
            mes = f"{mes}`{k}` <#{result['channel_id']}> ({result['channel_id']})\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"mediaonly channels ({len(results)})",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        number.append(
            Embed(
                color=self.bot.color,
                title=f"mediaonly channels ({len(results)})",
                description=messages[i],
            )
        )
        if len(number) > 1:
            return await ctx.paginator(number)
        return await ctx.send(embed=number[0])

    @group(invoke_without_command=True, aliases=["fakeperms"])
    async def fakepermissions(self, ctx):
        await ctx.create_pages()

    @fakepermissions.command(
        description="edit fake permissions for a role",
        help="config",
        usage="[role]",
        brief="server owner",
    )
    @utils.server_owner()
    async def edit(self, ctx: Context, *, role: Union[Role, str] = None):
        if isinstance(role, str):
            role = ctx.find_role(role)
            if role is None:
                return await ctx.send_warning("This is not a valid role")

        perms = [
            "administrator",
            "manage_guild",
            "manage_roles",
            "manage_channels",
            "manage_messages",
            "manage_nicknames",
            "manage_emojis",
            "ban_members",
            "kick_members",
            "moderate_members",
        ]
        options = [
            SelectOption(label=perm.replace("_", " "), value=perm) for perm in perms
        ]
        embed = Embed(
            color=self.bot.color,
            description="> Which **permissions** would you like to add to {}?".format(
                role.mention
            ),
        )
        select = Select(
            placeholder="select permissions", max_values=10, options=options
        )

        async def select_callback(interaction: Interaction):
            if ctx.author != interaction.user:
                return await self.bot.ext.send_warning(
                    interaction, "This is not your embed", ephemeral=True
                )
            data = json.dumps(select.values)
            check = await self.bot.db.fetchrow(
                "SELECT permissions FROM fake_permissions WHERE guild_id = $1 AND role_id = $2",
                interaction.guild.id,
                role.id,
            )
            if not check:
                await self.bot.db.execute(
                    "INSERT INTO fake_permissions VALUES ($1,$2,$3)",
                    interaction.guild.id,
                    role.id,
                    data,
                )
            else:
                await self.bot.db.execute(
                    "UPDATE fake_permissions SET permissions = $1 WHERE guild_id = $2 AND role_id = $3",
                    data,
                    interaction.guild.id,
                    role.id,
                )
            await interaction.response.edit_message(
                embed=Embed(
                    color=self.bot.color,
                    description=f"{self.bot.yes} {interaction.user.mention}: Added **{len(select.values)}** permission{'s' if len(select.values) > 1 else ''} to {role.mention}",
                ),
                view=None,
            )

        select.callback = select_callback
        view = View()
        view.add_item(select)
        await ctx.reply(embed=embed, view=view)

    @fakepermissions.command(
        name="list",
        description="list the permissions of a specific role",
        help="config",
        usage="[role]",
    )
    async def fakeperms_list(self, ctx: Context, *, role: Union[Role, str]):
        if isinstance(role, str):
            role = ctx.find_role(role)
            if role is None:
                return await ctx.send_warning("This is not a valid role")

        check = await self.bot.db.fetchrow(
            "SELECT permissions FROM fake_permissions WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        )
        if check is None:
            return await ctx.send_error("This role has no fake permissions")
        permissions = json.loads(check["permissions"])
        embed = Embed(
            color=self.bot.color,
            title=f"@{role.name}'s fake permissions",
            description="\n".join(
                [f"`{permissions.index(perm)+1}` {perm}" for perm in permissions]
            ),
        )
        embed.set_thumbnail(url=role.display_icon)
        return await ctx.reply(embed=embed)

    @fakepermissions.command(
        aliases=["perms"],
        description="list all the available permissions",
        help="config",
    )
    async def permissions(self, ctx: Context):
        perms = [
            "administrator",
            "manage_guild",
            "manage_roles",
            "manage_channels",
            "manage_messages",
            "manage_nicknames",
            "manage_emojis",
            "ban_members",
            "kick_members",
            "moderate_members",
        ]
        embed = Embed(
            color=self.bot.color,
            description="\n".join(
                [f"`{perms.index(perm)+1}` {perm}" for perm in perms]
            ),
        ).set_author(
            icon_url=self.bot.user.display_avatar.url, name="fakepermissions perms list"
        )
        await ctx.reply(embed=embed)

    @command(
        help="config",
        description="react to a message using the bot",
        brief="manage messages",
        usage="[message id / message link] [emoji]",
    )
    @utils.get_perms("manage_messages")
    async def react(self, ctx: Context, link: str, reaction: str):
        try:
            mes = await ctx.channel.fetch_message(int(link))
        except:
            mes = None
        if mes:
            try:
                await mes.add_reaction(reaction)
                view = View()
                view.add_item(Button(label="jump to message", url=mes.jump_url))
                return await ctx.reply(view=view)
            except:
                return await ctx.send_warning(
                    "Unable to add the reaction to that message"
                )
        message = await self.bot.ext.link_to_message(link)
        if not message:
            return await ctx.send_warning("No **message** found")
        if message.guild != ctx.guild:
            return await ctx.send_warning("This **message** is not from this server")
        elif message.channel.type != ChannelType.text:
            return await ctx.send_error("I can only react in text channels")
        try:
            await message.add_reaction(reaction)
            v = View()
            v.add_item(Button(label="jump to message", url=message.jump_url))
            return await ctx.reply(view=v)
        except:
            return await ctx.send_warning("Unable to add the reaction to that message")

    @group(invoke_without_command=True)
    async def bumpreminder(self, ctx):
        await ctx.create_pages()

    @bumpreminder.command(
        name="add",
        help="config",
        description="reminder to bump your server via disboard",
        brief="manage guild",
    )
    @utils.get_perms("manage_guild")
    async def bumpreminder_add(self, ctx: Context):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM bumps WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is not None:
            return await ctx.send_warning(
                "bump reminder is already enabled".capitalize()
            )
        await self.bot.db.execute(
            "INSERT INTO bumps VALUES ($1, $2)", ctx.guild.id, "true"
        )
        return await ctx.send_success("bump reminder is now enabled".capitalize())

    @bumpreminder.command(
        name="remove",
        help="config",
        description="remove bump reminder",
        brief="manage guild",
    )
    @utils.get_perms("manage_guild")
    async def bumpreminder_remove(self, ctx: Context):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM bumps WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is None:
            return await ctx.send_warning("bump reminder isn't enabled".capitalize())
        await self.bot.db.execute(
            "DELETE FROM bumps WHERE guild_id = {}".format(ctx.guild.id)
        )
        return await ctx.send_success("bump reminder is now disabled".capitalize())

    @command(
        aliases=["disablecmd"],
        description="disable a command",
        help="config",
        usage="[command name]",
    )
    @utils.get_perms("administrator")
    async def disablecommand(self, ctx: Context, *, cmd: str):
        found_command = self.bot.get_command(cmd)
        if found_command is None:
            return await ctx.send_warning(f"Command **{cmd}** not found")
        if found_command.name in [
            "ping",
            "help",
            "uptime",
            "disablecommand",
            "disablecmd",
            "enablecommand",
            "enablecmd",
        ]:
            return await ctx.send_warning("This command can't be disabled")
        check = await self.bot.db.fetchrow(
            "SELECT * FROM disablecommand WHERE command = $1 AND guild_id = $2",
            found_command.name,
            ctx.guild.id,
        )
        if check:
            return await ctx.send_error("This command is **already** disabled")
        await self.bot.db.execute(
            "INSERT INTO disablecommand VALUES ($1,$2)",
            ctx.guild.id,
            found_command.name,
        )
        await ctx.send_success(f"Disabled command **{found_command.name}**")

    @command(
        aliases=["enablecmd"],
        help="enable a command that was previously disabled in this server",
        description="config",
        usage="[command name]",
    )
    @utils.get_perms("administrator")
    async def enablecommand(self, ctx: Context, *, cmd: str):
        found_command = self.bot.get_command(cmd)
        if found_command is None:
            return await ctx.send_warning(f"Command **{cmd}** not found")
        check = await self.bot.db.fetchrow(
            "SELECT * FROM disablecommand WHERE command = $1 AND guild_id = $2",
            found_command.name,
            ctx.guild.id,
        )
        if not check:
            return await ctx.send_error("This command is **not** disabled")
        await self.bot.db.execute(
            "DELETE FROM disablecommand WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            found_command.name,
        )
        await ctx.send_success(f"Enabled command **{found_command.name}**")

    @hybrid_command(
        description="changes the guild prefix",
        usage="[prefix]",
        help="config",
        brief="manage guild",
    )
    @utils.get_perms("manage_guild")
    async def prefix(self, ctx: Context, prefix: str):
        if len(prefix) > 3:
            return await ctx.send_error("Uh oh! The prefix is too long")
        check = await self.bot.db.fetchrow(
            "SELECT * FROM prefixes WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is not None:
            await self.bot.db.execute(
                "UPDATE prefixes SET prefix = $1 WHERE guild_id = $2",
                prefix,
                ctx.guild.id,
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO prefixes VALUES ($1, $2)", ctx.guild.id, prefix
            )
        return await ctx.send_success(
            f"guild prefix changed to `{prefix}`".capitalize()
        )

    @hybrid_command(description="set your own prefix", usage="[prefix]", help="config")
    async def selfprefix(self, ctx: Context, prefix: str):
        if len(prefix) > 3 and prefix.lower() != "none":
            return await ctx.send_error("Uh oh! The prefix is too long")
        if prefix.lower() == "none":
            check = await self.bot.db.fetchrow(
                "SELECT * FROM selfprefix WHERE user_id = {}".format(ctx.author.id)
            )
            if check is not None:
                await self.bot.db.execute(
                    "DELETE FROM selfprefix WHERE user_id = {}".format(ctx.author.id)
                )
                return await ctx.send_success("Removed your self prefix")
            elif check is None:
                return await ctx.send_error("you don't have a self prefix".capitalize())
        else:
            result = await self.bot.db.fetchrow(
                "SELECT * FROM selfprefix WHERE user_id = {}".format(ctx.author.id)
            )
            if result is not None:
                await self.bot.db.execute(
                    "UPDATE selfprefix SET prefix = $1 WHERE user_id = $2",
                    prefix,
                    ctx.author.id,
                )
            elif result is None:
                await self.bot.db.execute(
                    "INSERT INTO selfprefix VALUES ($1, $2)", ctx.author.id, prefix
                )
            return await ctx.send_success(
                f"self prefix changed to `{prefix}`".capitalize()
            )

    @group(invoke_without_command=True)
    async def autorole(self, ctx):
        await ctx.create_pages()

    @autorole.command(
        name="add",
        description="Give a role to new members that join the server",
        help="config",
        usage="[role]",
        brief="manage_guild",
    )
    @utils.get_perms("manage_guild")
    async def autorole_add(self, ctx: Context, *, role: Union[Role, str]):
        if isinstance(role, str):
            role = ctx.find_role(role)
            if role is None:
                return await ctx.send_error(
                    f"Couldn't find a role named **{ctx.message.clean_content[-len(ctx.clean_prefix) + 11:]}**"
                )

        if self.is_dangerous(role):
            return await ctx.send_warning("This role can't be an autorole")

        check = await self.bot.db.fetchrow(
            "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        )
        if check is not None:
            return await ctx.send_error(f"{role.mention} is already added")

        await self.bot.db.execute(
            "INSERT INTO autorole (role_id, guild_id) VALUES ($1, $2)",
            role.id,
            ctx.guild.id,
        )
        return await ctx.send_success(f"Added {role.mention} as autorole")

    @autorole.command(
        name="remove",
        description="Remove a role from autoroles",
        help="config",
        usage="<role>",
        brief="manage_guild",
    )
    @utils.get_perms("manage_guild")
    async def autorole_remove(self, ctx: Context, *, role: Union[Role, str] = None):
        if isinstance(role, str):
            role = ctx.find_role(role)
            if role is None:
                return await ctx.send_error(
                    f"Couldn't find a role named **{ctx.message.clean_content[-len(ctx.clean_prefix) + 14:]}**"
                )

        if role is not None:
            check = await self.bot.db.fetchrow(
                "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )
            if check is None:
                return await ctx.send_error(f"{role.mention} is not added")

            await self.bot.db.execute(
                "DELETE FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )
            return await ctx.send_success(f"Removed {role.mention} from autorole")

        check = await self.bot.db.fetch(
            "SELECT * FROM autorole WHERE guild_id = $1", ctx.guild.id
        )
        if check is None:
            return await ctx.send_error("There are no roles added".capitalize())

        await self.bot.db.execute(
            "DELETE FROM autorole WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.send_success("Removed all roles from autorole")

    @autorole.command(name="list", description="List of autoroles", help="config")
    async def autorole_list(self, ctx: Context):
        results = await self.bot.db.fetch(
            "SELECT * FROM autorole WHERE guild_id = $1", ctx.guild.id
        )
        if not results:
            return await ctx.send_warning("There are no autoroles")

        embeds = []
        description = ""
        for i, result in enumerate(results, start=1):
            role = ctx.guild.get_role(int(result["role_id"]))
            description += f"`{i}` {role.mention if role else result['role_id']}\n"

            if i % 10 == 0 or i == len(results):
                embeds.append(
                    Embed(
                        color=self.bot.color,
                        title=f"Autoroles ({len(results)})",
                        description=description,
                    )
                )
                description = ""

        return await ctx.paginator(embeds)

    @command(
        name="createembed",
        aliases=["ce"],
        help="config",
        description="create embed",
        usage="[code]",
    )
    async def createembed(self, ctx: Context, *, code: EmbedScript):
        await ctx.send(**code)

    @group(invoke_without_command=True)
    async def starboard(self, ctx):
        await ctx.create_pages()

    @starboard.command(
        help="config",
        description="modify the starboard count",
        brief="manage guild",
        usage="[count]",
        aliases=["amount"],
    )
    @utils.get_perms("manage_guild")
    async def count(self, ctx: Context, count: int):
        if count < 1:
            return await ctx.send_warning("Count can't be **less** than 1")
        check = await self.bot.db.fetchrow(
            "SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id
        )
        if check is None:
            await self.bot.db.execute(
                "INSERT INTO starboard (guild_id, count) VALUES ($1, $2)",
                ctx.guild.id,
                count,
            )
        else:
            await self.bot.db.execute(
                "UPDATE starboard SET count = $1 WHERE guild_id = $2",
                count,
                ctx.guild.id,
            )
        await ctx.send_success(f"Starboard **count** set to **{count}**")

    @starboard.command(
        name="channel",
        help="config",
        description="configure the starboard channel",
        brief="manage guild",
        usage="[channel]",
    )
    @utils.get_perms("manage_guild")
    async def starboard_channel(self, ctx: Context, *, channel: TextChannel):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id
        )
        if check is None:
            await self.bot.db.execute(
                "INSERT INTO starboard (guild_id, channel_id) VALUES ($1, $2)",
                ctx.guild.id,
                channel.id,
            )
        else:
            await self.bot.db.execute(
                "UPDATE starboard SET channel_id = $1 WHERE guild_id = $2",
                channel.id,
                ctx.guild.id,
            )
        await ctx.send_success(f"Starboard **channel** set to {channel.mention}")

    @starboard.command(
        name="emoji",
        help="config",
        description="configure the starboard emoji",
        brief="manage guild",
        usage="[emoji]",
    )
    @utils.get_perms("manage_guild")
    async def starboard_emoji(self, ctx: Context, emoji: Union[PartialEmoji, str]):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id
        )
        emoji_id = emoji.id if isinstance(emoji, PartialEmoji) else ord(str(emoji))
        if check is None:
            await self.bot.db.execute(
                "INSERT INTO starboard (guild_id, emoji_id, emoji_text) VALUES ($1,$2,$3)",
                ctx.guild.id,
                emoji_id,
                str(emoji),
            )
        else:
            await self.bot.db.execute(
                "UPDATE starboard SET emoji_id = $1 WHERE guild_id = $2",
                emoji_id,
                ctx.guild.id,
            )
            await self.bot.db.execute(
                "UPDATE starboard SET emoji_text = $1 WHERE guild_id = $2",
                str(emoji),
                ctx.guild.id,
            )
        await ctx.send_success(f"Starboard **emoji** set to {emoji}")

    @starboard.command(
        name="remove",
        help="config",
        description="remove starboard",
        brief="manage guild",
        aliases=["disable"],
    )
    @utils.get_perms("manage_guild")
    async def starboard_remove(self, ctx: Context):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id
        )
        if check is None:
            return await ctx.send_warning("Starboard is not **enabled**")
        await self.bot.db.execute(
            "DELETE FROM starboard WHERE guild_id = $1", ctx.guild.id
        )
        await self.bot.db.execute(
            "DELETE FROM starboardmes WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.send_success("Disabled starboard **succesfully**")

    @group(
        invoke_without_command=True,
        description="manage custom punishment responses",
        help="config",
    )
    async def invoke(self, ctx):
        await ctx.create_pages()

    @invoke.command(
        name="unban",
        help="config",
        description="add a custom unban message",
        brief="manage guild",
        usage="[--embed embed name | message]\nexample 1: ;invoke unban --embed test\nexample 2: ;invoke unban {user.mention} unbanned {member.mention}",
    )
    @utils.get_perms("manage_guild")
    async def invoke_unban(self, ctx: Context, *, code: str):
        await InvokeClass.invoke_cmds(ctx, ctx.guild.me, code)

    @invoke.command(
        name="ban",
        help="config",
        description="add a custom ban command",
        brief="manage guild",
        usage="[--embed embed name | message]\nexample 1: ;invoke ban --embed test\nexample 2: ;invoke ban {user.mention} banned {member.mention}",
    )
    @utils.get_perms("manage_guild")
    async def invoke_ban(self, ctx: Context, *, code: str):
        await InvokeClass.invoke_cmds(ctx, ctx.guild.me, code)

    @invoke.command(
        name="kick",
        help="config",
        description="add a custom kick command",
        brief="manage guild",
        usage="[--embed embed name | message]\nexample 1: ;invoke kick --embed test\nexample 2: -invoke kick {user.mention} kicked {member.mention}",
    )
    @utils.get_perms("manage_guild")
    async def invoke_kick(self, ctx: Context, *, code: str):
        await InvokeClass.invoke_cmds(ctx, ctx.guild.me, code)

    @invoke.command(
        name="mute",
        help="config",
        description="add a custom mute command",
        brief="manage guild",
        usage="[--embed embed name | message]\nexample 1: ;invoke mute --embed test\nexample 2: ;invoke mute {user.mention} muted {member.mention}",
    )
    @utils.get_perms("manage_guild")
    async def invoke_mute(self, ctx: Context, *, code: str):
        await InvokeClass.invoke_cmds(ctx, ctx.guild.me, code)

    @invoke.command(
        name="unmute",
        help="config",
        description="add a custom unmute command",
        brief="manage guild",
        usage="[--embed embed name | message]\nexample 1: ;invoke unmute --embed test\nexample 2: ;invoke unmute {user.mention} unmuted {member.mention}",
    )
    @utils.get_perms("manage_guild")
    async def invoke_unmute(self, ctx: Context, *, code: str):
        await InvokeClass.invoke_cmds(ctx, ctx.guild.me, code)

    @invoke.command(
        name="warn",
        help="config",
        description="add a custom warn command",
        brief="manage guild",
        usage="[--embed embed name | message]\nexample 1: ;invoke warn --embed test\nexample 2: ;invoke warn {user.mention} warned {member.mention}",
    )
    @utils.get_perms("manage_guild")
    async def invoke_warn(self, ctx: Context, *, code: str):
        await InvokeClass.invoke_cmds(ctx, ctx.guild.me, code)

    @invoke.command(
        name="jail",
        help="config",
        description="add a custom jail command",
        brief="manage guild",
        usage="[--embed embed name | message]\nexample 1: ;invoke jail --embed test\nexample 2: ;invoke jail {user.mention} jailed {member.mention}",
    )
    @utils.get_perms("manage_guild")
    async def invoke_jail(self, ctx: Context, *, code: str):
        await InvokeClass.invoke_cmds(ctx, ctx.guild.me, code)

    @invoke.command(
        name="unjail",
        help="config",
        description="add a custom unjail command",
        brief="manage guild",
        usage="[--embed embed name | message]\nexample 1: ;invoke unjail --embed test\nexample 2: ;invoke unjail {user.mention} unjailed {member.mention}",
    )
    @utils.get_perms("manage_guild")
    async def invoke_unjail(self, ctx: Context, *, code: str):
        await InvokeClass.invoke_cmds(ctx, ctx.guild.me, code)


async def setup(bot):
    await bot.add_cog(Config(bot))
