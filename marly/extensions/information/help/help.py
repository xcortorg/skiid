from typing import Optional

from discord import Message
from discord.ext.commands import command

from system.tools.metaclass import CompositeMetaClass, MixinMeta
from system.base.context import Context
from discord.ext.commands.core import Command, Group
from discord.ext.commands import FlagConverter
from discord.ext.commands.flags import FlagsMeta, MISSING
from discord import Embed
import config
from discord import Status


class help(MixinMeta, metaclass=CompositeMetaClass):
    def _add_flag_formatting(self, annotation: FlagConverter, embed: Embed):
        optional = [
            f"`--{name}{' on/off' if isinstance(flag.annotation, Status) else ''}`"
            for name, flag in annotation.get_flags().items()
            if flag.default is not MISSING
        ]
        required = [
            f"`--{name}{' on/off' if isinstance(flag.annotation, Status) else ''}`"
            for name, flag in annotation.get_flags().items()
            if flag.default is MISSING
        ]

        if required:
            embed.add_field(
                name="Required Flags", value="\n".join(required), inline=False
            )

        if optional:
            embed.add_field(
                name="Optional Flags", value="\n".join(optional), inline=False
            )

    async def _create_command_embed(
        self, ctx: Context, command: Command, index: int = None, total: int = None
    ) -> Embed:
        """Helper method to create command embeds"""
        embed = Embed(
            color=config.Color.info,
            title=(
                ("Group Command: " if isinstance(command, Group) else "Command: ")
                + command.qualified_name
            ),
            description=(command.help or "")
            + (
                f"\n{command.customdescription}"
                if hasattr(command, "customdescription") and command.customdescription
                else ""
            ),
        )

        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        embed.add_field(
            name="**Aliases**",
            value=(", ".join(a for a in command.aliases) if command.aliases else "n/a"),
            inline=True,
        )

        embed.add_field(
            name="**Parameters**",
            value=(
                ", ".join(param.replace("_", " ") for param in command.clean_params)
                if command.clean_params
                else "n/a"
            ),
            inline=True,
        )

        embed.add_field(
            name="**Information**",
            value=(
                " ".join(
                    [
                        (
                            f"\n{config.Emojis.Embeds.COOLDOWN} {int(command._buckets._cooldown.per)} seconds"
                            if command._buckets._cooldown
                            else ""
                        ),
                        (
                            f"\n{config.Emojis.Embeds.WARN} {', '.join(perm.replace('_', ' ').title() for perm in (await command.permissions()))}{' & ' + command.brief if command.brief else ''}"
                            if await command.permissions()
                            else (
                                f"\n{config.Emojis.Embeds.WARN} {command.brief}"
                                if command.brief
                                else ""
                            )
                        ),
                        (
                            f"\n{config.Emojis.Embeds.NOTES} {command.notes}"
                            if command.notes
                            else ""
                        ),
                    ]
                ).strip()
                or "n/a"
            ),
            inline=True,
        )

        embed.add_field(
            name="",
            value=(
                "```\n"
                + (
                    f"Syntax: {ctx.prefix}{command.qualified_name} "
                    + (
                        command.usage
                        or " ".join(
                            [
                                (
                                    f"<{name}>"
                                    if param.default == param.empty
                                    else f"({name})"
                                )
                                for name, param in command.clean_params.items()
                            ]
                        )
                    )
                )
                + "\n"
                + (
                    f"Example: {ctx.prefix}{command.qualified_name} {command.example}"
                    if command.example
                    else ""
                )
                + "```"
            ),
            inline=False,
        )

        for param in command.clean_params.values():
            if isinstance(param.annotation, FlagsMeta):
                self._add_flag_formatting(param.annotation, embed)

        if hasattr(command, "_flag") and command._flag:
            flags = [f"`--{flag}`" for flag in command._flag.__annotations__]
            # Add newline after every 3 flags
            flags_description = ""
            for i in range(0, len(flags), 3):
                chunk = flags[i : i + 3]
                flags_description += ", ".join(chunk)
                if i + 3 < len(flags):  # Don't add newline for the last group
                    flags_description += "\n"
            embed.add_field(name="**Flags**", value=flags_description, inline=False)

        footer_text = (
            f"Module: {command.cog_name.lower() if command.cog_name else 'n/a'}"
        )
        if index is not None and total is not None:
            footer_text = f"Command {index + 1}/{total} • {footer_text}"

        embed.set_footer(text=footer_text)

        return embed

    @command(
        name="help",
        aliases=["commands", "h"],
        usage="command",
        example="ban",
        notes="h -simple",
    )
    async def help(self, ctx: Context, *, command: str = None) -> Message:
        """
        View command information
        """
        if not command:
            return await ctx.send(
                f"{ctx.author.mention}: <https://marlywebsite.vercel.app/>, join the discord server @ <https://discord.gg/ua38ZnHApH>"
            )

        if command == "-simple":
            embed = Embed(description="")
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )

            total_commands = 0
            for cog_name, cog in self.bot.cogs.items():
                # Skip developer cogs and hidden cogs
                if getattr(cog, "hidden", False) or cog_name.lower() in [
                    "developer",
                    "jishaku",
                ]:
                    continue

                commands = [
                    cmd for cmd in cog.get_commands() if not cmd.hidden and cmd.enabled
                ]

                if not commands:
                    continue

                # Count subcommands
                command_count = len(commands)
                for cmd in commands:
                    if isinstance(cmd, Group):
                        # Count all nested subcommands
                        for subcmd in cmd.walk_commands():
                            if not subcmd.hidden and subcmd.enabled:
                                command_count += 1
                total_commands += command_count

                command_list = ", ".join(
                    f"{cmd.name}{'*' if isinstance(cmd, Group) else ''}"
                    for cmd in commands
                )
                embed.add_field(
                    name=f"__**{cog_name}**__ ({command_count})",
                    value=command_list,
                    inline=False,
                )
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            embed.set_footer(
                text=f"{total_commands} commands in total including subcommands"
            )
            return await ctx.send(embed=embed)

        command_obj: Command | Group = self.bot.get_command(command)
        if not command_obj:
            return await ctx.warn(f"Command `{command}` does **not** exist")

        embeds = []
        commands_list = []
        if isinstance(command_obj, Group):
            commands_list.append(command_obj)
            for subcmd in command_obj.walk_commands():
                if not subcmd.hidden and subcmd.enabled and subcmd not in commands_list:
                    commands_list.append(subcmd)
        else:
            commands_list = [command_obj]

        # Create embeds with proper numbering
        for idx, command in enumerate(commands_list):
            embed = await self._create_command_embed(
                ctx, command, idx, len(commands_list)
            )
            embeds.append(embed)

        await ctx.paginate(embeds)
