import asyncio
from abc import ABC
from typing import Any, Dict, List, Optional, Union

import aiohttp

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

import discord
from AAA3A_utils import Cog, CogsUtils, Menu
from red_commons.logging import getLogger

from grief.core import Config, commands
from grief.core.bot import Grief
from grief.core.commands import Context
from grief.core.converters.converters import (RawUserIds,
                                              RoleHierarchyConverter,
                                              SelfRoleConverter)
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils import AsyncIter, bounded_gather
from grief.core.utils.chat_formatting import box, humanize_list, pagify

from .abc import RoleToolsMixin
from .events import RoleToolsEvents
from .exclusive import RoleToolsExclusive
from .inclusive import RoleToolsInclusive
from .menus import BaseMenu, ConfirmView, RolePages
from .settings import RoleToolsSettings

roletools = RoleToolsMixin.roletools

### roleutils
import logging
from collections import defaultdict
from colorsys import rgb_to_hsv
from typing import Dict, Generator, List, Optional, Sequence, Tuple

import discord
from TagScriptEngine import (Interpreter, LooseVariableGetterBlock,
                             MemberAdapter)

from grief.core import commands
from grief.core.utils.chat_formatting import humanize_number as hn
from grief.core.utils.chat_formatting import pagify, text_to_file
from grief.core.utils.mod import get_audit_reason

from .abcc import CompositeMetaClass, MixinMeta
from .converters import (FuzzyRole, RoleArgumentConverter, StrictRole,
                         TargeterArgs, TouchableMember)
from .utils import (can_run_command, guild_roughly_chunked, humanize_roles,
                    is_allowed_by_role_hierarchy)

log = getLogger("grief.roletools")
_ = Translator("RoleTools", __file__)


class EmojiOrUrlConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        try:
            return await discord.ext.commands.converter.CONVERTER_MAPPING[
                discord.Emoji
            ]().convert(ctx, argument)
        except commands.BadArgument:
            pass
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]
        return argument


class PositionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            position = int(argument)
        except ValueError:
            raise commands.BadArgument(_("The position must be an integer."))
        max_guild_roles_position = len(ctx.guild.roles)
        if position <= 0 or position >= max_guild_roles_position + 1:
            raise commands.BadArgument(
                _(
                    "The indicated position must be between 1 and {max_guild_roles_position}."
                ).format(max_guild_roles_position=max_guild_roles_position)
            )
        _list = list(range(max_guild_roles_position - 1))[::-1]
        position = _list[position - 1]
        return position + 1


class PermissionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        permissions = [
            key
            for key, value in dict(discord.Permissions.all_channel()).items()
            if value
        ]
        if argument not in permissions:
            raise commands.BadArgument(_("This permission is invalid."))
        return argument


ERROR_MESSAGE = _(
    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}"
)


def targeter_cog(ctx: commands.Context):
    cog = ctx.bot.get_cog("Targeter")
    return cog is not None and hasattr(cog, "args_to_list")


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


def custom_cooldown(ctx: commands.Context) -> Optional[discord.app_commands.Cooldown]:
    who = ctx.args[3:]
    members = []

    for entity in who:
        log.verbose("custom_cooldown entity: %s", entity)
        if isinstance(entity, discord.TextChannel) or isinstance(entity, discord.Role):
            members += entity.members
        elif isinstance(entity, discord.Member):
            members.append(entity)
        else:
            if entity not in ["everyone", "here", "bots", "humans"]:
                continue
            elif entity == "everyone":
                members = ctx.guild.members
                break
            elif entity == "here":
                members += [m for m in ctx.guild.members if str(m.status) == "online"]
            elif entity == "bots":
                members += [m for m in ctx.guild.members if m.bot]
            elif entity == "humans":
                members += [m for m in ctx.guild.members if not m.bot]
    members = list(set(members))
    log.debug("Returning cooldown of 1 per %s", min(len(members) * 10, 3600))
    return discord.app_commands.Cooldown(1, min(len(members) * 10, 3600))


@cog_i18n(_)
class RoleTools(
    RoleToolsEvents,
    RoleToolsExclusive,
    RoleToolsInclusive,
    RoleToolsSettings,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Role related tools for moderation
    """

    def __init__(self, bot: Grief):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=218773382617890828, force_registration=True
        )
        self.config.register_global(
            version="0.0.0",
            atomic=True,
            enable_slash=False,
        )
        self.config.register_guild(
            auto_roles=[],
            atomic=None,
            buttons={},
            select_options={},
            select_menus={},
        )
        self.config.register_role(
            sticky=False,
            auto=False,
            select_options=[],
            exclusive_to=[],
            inclusive_with=[],
            required=[],
            require_any=False,
        )
        self.config.register_member(sticky_roles=[])
        self.settings: Dict[int, Any] = {}
        self._ready: asyncio.Event = asyncio.Event()
        self.views: Dict[int, Dict[str, discord.ui.View]] = {}

    def cog_check(self, ctx: commands.Context) -> bool:
        return self._ready.is_set()

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """
        Thanks Sinbad!
        """
        pre_processed = super().format_help_for_context(ctx)
        ret = f"{pre_processed}"
        # we'll only have a repo if the cog was installed through Downloader at some point

    async def add_cog_to_dev_env(self):
        await self.bot.wait_until_red_ready()
        if self.bot.owner_ids and 392318365357834240 in self.bot.owner_ids:
            try:
                self.bot.add_dev_env_value("roletools", lambda x: self)
            except Exception:
                pass

    async def _get_commit(self):
        downloader = self.bot.get_cog("Downloader")
        if not downloader:
            return
        cogs = await downloader.installed_cogs()
        for cog in cogs:
            if cog.name == "roletools":
                if cog.repo is not None:
                    self._repo = cog.repo.clean_url
                self._commit = cog.commit

    async def load_views(self):
        self.settings = await self.config.all_guilds()
        await self.bot.wait_until_red_ready()
        try:
            await self.initialize_select()
        except Exception:
            log.exception("Error initializing Select")
        try:
            await self.initialize_buttons()
        except Exception:
            log.exception("Error initializing Buttons")
        for guild_id, guild_views in self.views.items():
            for msg_ids, view in guild_views.items():
                log.trace("Adding view %r to %s", view, guild_id)
                channel_id, message_id = msg_ids.split("-")
                self.bot.add_view(view, message_id=int(message_id))
                # These should be unique messages containing views
                # and we should track them seperately
        self._ready.set()

    async def cog_load(self) -> None:
        if await self.config.version() < "1.0.1":
            sticky_role_config = Config.get_conf(
                None, identifier=1358454876, cog_name="StickyRoles"
            )
            sticky_settings = await sticky_role_config.all_guilds()
            for guild_id, data in sticky_settings.items():
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue
                for role_id in data["sticky_roles"]:
                    role = guild.get_role(role_id)
                    if role:
                        await self.config.role(role).sticky.set(True)
            auto_role_config = Config.get_conf(
                None, identifier=45463543548, cog_name="Autorole"
            )
            auto_settings = await auto_role_config.all_guilds()
            for guild_id, data in auto_settings.items():
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue
                if ("ENABLED" in data and not data["ENABLED"]) or (
                    "AGREE_CHANNEL" in data and data["AGREE_CHANNEL"] is not None
                ):
                    continue
                if "ROLE" not in data:
                    continue
                for role_id in data["ROLE"]:
                    role = guild.get_role(role_id)
                    if role:
                        await self.config.role(role).auto.set(True)
                        async with self.config.guild_from_id(
                            int(guild_id)
                        ).auto_roles() as auto_roles:
                            if role.id not in auto_roles:
                                auto_roles.append(role.id)
        loop = asyncio.get_running_loop()
        loop.create_task(self.load_views())
        loop.create_task(self.add_cog_to_dev_env())
        loop.create_task(self._get_commit())

    async def cog_unload(self):
        for views in self.views.values():
            for view in views.values():
                # Don't forget to remove persistent views when the cog is unloaded.
                log.verbose("Stopping view %s", view)
                view.stop()
        try:
            self.bot.remove_dev_env_value("roletools")
        except Exception:
            pass

    async def confirm_selfassignable(
        self, ctx: commands.Context, roles: List[discord.Role]
    ) -> None:
        not_assignable = [
            r for r in roles if not await self.config.role(r).selfassignable()
        ]
        if not_assignable:
            role_list = "\n".join(f"- {role.mention}" for role in not_assignable)
            msg_str = _(
                "The following roles are not self assignable:\n{roles}\n"
                "Would you liked to make them self assignable and self removeable?"
            ).format(
                roles=role_list,
            )
            pred = ConfirmView(ctx.author)
            pred.message = await ctx.send(
                msg_str,
                view=pred,
                allowed_mentions=discord.AllowedMentions(roles=False),
            )
            await pred.wait()
            if pred.result:
                for role in not_assignable:
                    await self.config.role(role).selfassignable.set(True)
                    await self.config.role(role).selfremovable.set(True)
                await ctx.channel.send(
                    _(
                        "The following roles have been made self assignable and self removeable:\n{roles}"
                    ).format(roles=role_list)
                )
            else:
                await ctx.channel.send(
                    _(
                        "Okay I won't make the following rolesself assignable:\n{roles}"
                    ).format(roles=role_list)
                )

    @roletools.command(cooldown_after_parsing=True, with_app_command=False)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.guild)
    async def giverole(
        self,
        ctx: Context,
        role: RoleHierarchyConverter,
        *who: Union[discord.Role, discord.TextChannel, discord.Member, str],
    ) -> None:
        """
        Gives a role to designated members.

        `<role>` The role you want to give.
        `[who...]` Who you want to give the role to. This can include any of the following:```diff
        + Member
            A specified member of the server.
        + Role
            People who already have a specified role.
        + TextChannel
            People who have access to see the channel provided.
        Or one of the following:
        + everyone - everyone in the server.
        + here     - everyone who appears online in the server.
        + bots     - all the bots in the server.
        + humans   - all the humans in the server.
        ```
        **Note:** This runs through exclusive and inclusive role checks
        which may cause unintended roles to be removed/applied.

        **This command is on a cooldown of 10 seconds per member who receives
        a role up to a maximum of 1 hour.**
        """
        await ctx.typing()

        if len(who) == 0:
            await ctx.send_help()
            ctx.command.reset_cooldown(ctx)
            return
        async with ctx.typing():
            members = []
            for entity in who:
                if isinstance(entity, discord.TextChannel) or isinstance(
                    entity, discord.Role
                ):
                    members += entity.members
                elif isinstance(entity, discord.Member):
                    members.append(entity)
                else:
                    if entity not in ["everyone", "here", "bots", "humans"]:
                        msg = _("`{who}` cannot have roles assigned to them.").format(
                            who=entity
                        )
                        await ctx.send(msg)
                        ctx.command.reset_cooldown(ctx)
                        return
                    elif entity == "everyone":
                        members = ctx.guild.members
                        break
                    elif entity == "here":
                        members += [
                            m
                            async for m in AsyncIter(ctx.guild.members, steps=500)
                            if str(m.status) == "online"
                        ]
                    elif entity == "bots":
                        members += [
                            m
                            async for m in AsyncIter(ctx.guild.members, steps=500)
                            if m.bot
                        ]
                    elif entity == "humans":
                        members += [
                            m
                            async for m in AsyncIter(ctx.guild.members, steps=500)
                            if not m.bot
                        ]
            members = list(set(members))
            tasks = []
            async for m in AsyncIter(members, steps=500):
                if m.top_role >= ctx.me.top_role or role in m.roles:
                    continue
                # tasks.append(m.add_roles(role, reason=_("Roletools Giverole command")))
                tasks.append(
                    self.give_roles(
                        m,
                        [role],
                        _("Roletools Giverole command"),
                        check_cost=False,
                        atomic=False,
                    )
                )
            await bounded_gather(*tasks)
        added_to = humanize_list([getattr(en, "name", en) for en in who])
        msg = _("Added {role} to {added}.").format(role=role.mention, added=added_to)
        await ctx.send(msg)

    @roletools.command(with_app_command=False)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def removerole(
        self,
        ctx: Context,
        role: RoleHierarchyConverter,
        *who: Union[discord.Role, discord.TextChannel, discord.Member, str],
    ) -> None:
        """
        Removes a role from the designated members.

        `<role>` The role you want to give.
        `[who...]` Who you want to give the role to. This can include any of the following:```diff
        + Member
            A specified member of the server.
        + Role
            People who already have a specified role.
        + TextChannel
            People who have access to see the channel provided.
        Or one of the following:
        + everyone - everyone in the server.
        + here     - everyone who appears online in the server.
        + bots     - all the bots in the server.
        + humans   - all the humans in the server.
        ```
        **Note:** This runs through exclusive and inclusive role checks
        which may cause unintended roles to be removed/applied.

        **This command is on a cooldown of 10 seconds per member who receives
        a role up to a maximum of 1 hour.**
        """
        await ctx.typing()

        if len(who) == 0:
            return await ctx.send_help()
        async with ctx.typing():
            members = []
            for entity in who:
                if isinstance(entity, discord.TextChannel) or isinstance(
                    entity, discord.Role
                ):
                    members += entity.members
                elif isinstance(entity, discord.Member):
                    members.append(entity)
                else:
                    if entity not in ["everyone", "here", "bots", "humans"]:
                        msg = _("`{who}` cannot have roles removed from them.").format(
                            who=entity
                        )
                        await ctx.send(msg)
                        ctx.command.reset_cooldown(ctx)
                        return
                    elif entity == "everyone":
                        members = ctx.guild.members
                        break
                    elif entity == "here":
                        members += [
                            m
                            async for m in AsyncIter(ctx.guild.members, steps=500)
                            if str(m.status) == "online"
                        ]
                    elif entity == "bots":
                        members += [
                            m
                            async for m in AsyncIter(ctx.guild.members, steps=500)
                            if m.bot
                        ]
                    elif entity == "humans":
                        members += [
                            m
                            async for m in AsyncIter(ctx.guild.members, steps=500)
                            if not m.bot
                        ]
            members = list(set(members))
            tasks = []
            async for m in AsyncIter(members, steps=500):
                if m.top_role >= ctx.me.top_role or role not in m.roles:
                    continue
                # tasks.append(m.add_roles(role, reason=_("Roletools Giverole command")))
                tasks.append(
                    self.remove_roles(
                        m, [role], _("Roletools Removerole command"), atomic=False
                    )
                )
            await bounded_gather(*tasks)
        removed_from = humanize_list([getattr(en, "name", en) for en in who])
        msg = _("Removed the {role} from {removed}.").format(
            role=role.mention, removed=removed_from
        )
        await ctx.send(msg)

    @roletools.command()
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def forcerole(
        self,
        ctx: Context,
        users: commands.Greedy[Union[discord.Member, RawUserIds]],
        *,
        role: RoleHierarchyConverter,
    ) -> None:
        """
        Force a sticky role on one or more users.

        `<users>` The users you want to have a forced stickyrole applied to.
        `<roles>` The role you want to set.

        Note: The only way to remove this would be to manually remove the role from
        the user.
        """
        await ctx.typing()
        errors = []
        for user in users:
            if isinstance(user, int):
                async with self.config.member_from_ids(
                    ctx.guild.id, user
                ).sticky_roles() as setting:
                    if role.id not in setting:
                        setting.append(role.id)
            elif isinstance(user, discord.Member):
                async with self.config.member(user).sticky_roles() as setting:
                    if role.id not in setting:
                        setting.append(role.id)
                try:
                    await self.give_roles(user, [role], reason=_("Forced Sticky Role"))
                except discord.HTTPException:
                    errors.append(
                        _(
                            "There was an error force applying the role to {user}.\n"
                        ).format(user=user)
                    )
        msg = _("{users} will have the role {role} force applied to them.").format(
            users=humanize_list(users), role=role.name
        )
        await ctx.send(msg)
        if errors:
            await ctx.channel.send("".join([e for e in errors]))

    @roletools.command()
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def forceroleremove(
        self,
        ctx: Context,
        users: commands.Greedy[Union[discord.Member, RawUserIds]],
        *,
        role: RoleHierarchyConverter,
    ) -> None:
        """
        Force remove sticky role on one or more users.

        `<users>` The users you want to have a forced stickyrole applied to.
        `<roles>` The role you want to set.

        Note: This is generally only useful for users who have left the server.
        """
        await ctx.typing()

        errors = []
        for user in users:
            if isinstance(user, int):
                async with self.config.member_from_ids(
                    ctx.guild.id, user
                ).sticky_roles() as setting:
                    if role in setting:
                        setting.remove(role.id)
            elif isinstance(user, discord.Member):
                async with self.config.member(user).sticky_roles() as setting:
                    if role.id in setting:
                        setting.append(role.id)
                try:
                    await self.remove_roles(
                        user, [role], reason=_("Force removed sticky role")
                    )
                except discord.HTTPException:
                    errors.append(
                        _(
                            "There was an error force removing the role from {user}.\n"
                        ).format(user=user)
                    )
        msg = _("{users} will have the role {role} force removed from them.").format(
            users=humanize_list(users), role=role.name
        )
        await ctx.send(msg)
        if errors:
            await ctx.channel.send("".join([e for e in errors]))

    @roletools.command(aliases=["viewrole"])
    @commands.bot_has_permissions(
        read_message_history=True, add_reactions=True, embed_links=True
    )
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def viewroles(
        self, ctx: Context, *, role: Optional[discord.Role] = None
    ) -> None:
        """
        View current roletools setup for each role in the server

        `[role]` The role you want to see settings for.
        """
        page_start = 0
        if role:
            page_start = ctx.guild.roles.index(role)
        await BaseMenu(
            source=RolePages(
                roles=ctx.guild.roles,
            ),
            delete_message_after=False,
            clear_reactions_after=True,
            timeout=60,
            cog=self,
            page_start=page_start,
        ).start(ctx=ctx)

    # @roletools.group(name="slash")
    # @commands.admin_or_permissions(manage_guild=True)
    async def roletools_slash(self, ctx: Context) -> None:
        """
        Slash command toggling for roletools
        """
        pass

    # @roletools_slash.command(name="global")
    # @commands.is_owner()
    async def roletools_global_slash(self, ctx: Context) -> None:
        """Toggle this cog to register slash commands"""
        current = await self.config.enable_slash()
        await self.config.enable_slash.set(not current)
        verb = _("enabled") if not current else _("disabled")
        await ctx.send(_("Slash commands are {verb}.").format(verb=verb))
        if not current:
            self.bot.tree.add_command(self, override=True)
        else:
            self.bot.tree.remove_command("role-tools")

    ###### roleutils
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def role(
        self,
        ctx: commands.Context,
        member: TouchableMember(False),
        *,
        role: StrictRole(False),
    ):
        """Base command for modifying roles.

        Invoking this command will add or remove the given role from the member, depending on whether they already had it.
        """
        if role in member.roles and await can_run_command(ctx, "role remove"):
            com = self.bot.get_command("role remove")
            await ctx.invoke(
                com,
                member=member,
                role=role,
            )
        elif role not in member.roles and await can_run_command(ctx, "role add"):
            com = self.bot.get_command("role add")
            await ctx.invoke(
                com,
                member=member,
                role=role,
            )
        else:
            await ctx.send_help()

    def format_member(self, member: discord.Member, formatting: str) -> str:
        output = self.interpreter.process(formatting, {"member": MemberAdapter(member)})
        return output.body

    @staticmethod
    def get_hsv(role: discord.Role) -> Tuple[float, float, float]:
        return rgb_to_hsv(*role.color.to_rgb())

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command("create")
    async def role_create(
        self,
        ctx: commands.Context,
        color: Optional[discord.Color] = discord.Color.default(),
        hoist: Optional[bool] = False,
        *,
        name: Optional[str] = None,
    ):
        """
        Creates a role.
        Color and whether it is hoisted can be specified.
        """
        if len(ctx.guild.roles) >= 250:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: this server has 250 roles, delete one to make a new one..",
                color=0x313338,
            )
            return await ctx.reply(embed=embed, mention_author=False)
        role = await ctx.guild.create_role(name=name, colour=color, hoist=hoist)
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: **{role}** created.", color=0x313338
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command("color", aliases=["colour"])
    async def role_color(
        self,
        ctx: commands.Context,
        role: StrictRole(check_integrated=False),
        color: discord.Color,
    ):
        """Change a role's color."""
        await role.edit(color=color)
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: **{role}** color changed to **{color}**.",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command("hoist")
    async def role_hoist(
        self,
        ctx: commands.Context,
        role: StrictRole(check_integrated=False),
        hoisted: Optional[bool] = None,
    ):
        """Toggle whether a role should appear seperate from other roles."""
        hoisted = hoisted if hoisted is not None else not role.hoist
        await role.edit(hoist=hoisted)
        now = "now" if hoisted else "no longer"
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: **{role}** is {now} hoisted.",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @role.command(name="displayicon", aliases=["icon"])
    @commands.has_guild_permissions(manage_roles=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def role_display_icon(
        self,
        ctx: commands.Context,
        role: RoleHierarchyConverter,
        display_icon: EmojiOrUrlConverter = None,
    ) -> None:
        """Edit role display icon.

        `display_icon` can be an Unicode emoji, a custom emoji or an url. You can also upload an attachment.
        """
        if "ROLE_ICONS" not in ctx.guild.features:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This server doesn't have the `ROLE_ICONS` feature. This server needs more boosts to perform this action."
                )
            )
        if len(ctx.message.attachments) > 0:
            display_icon = await ctx.message.attachments[
                0
            ].read()  # Read an optional attachment.
        elif display_icon is not None:
            if isinstance(display_icon, discord.Emoji):
                # emoji_url = f"https://cdn.discordapp.com/emojis/{display_icon.id}.png"
                # async with aiohttp.ClientSession() as session:
                #     async with session.get(emoji_url) as r:
                #         display_icon = await r.read()  # Get emoji data.
                display_icon = await display_icon.read()
            elif display_icon.strip("\N{VARIATION SELECTOR-16}") in EMOJI_DATA:
                display_icon = display_icon
            else:
                url = display_icon
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(url) as r:
                            display_icon = await r.read()  # Get URL data.
                    except aiohttp.InvalidURL:
                        return await ctx.send("That URL is invalid.")
                    except aiohttp.ClientError:
                        return await ctx.send(
                            "Something went wrong while trying to get the image."
                        )
        else:
            await role.edit(
                display_icon=None,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: Cleared **{role}** role icon.",
                color=0x313338,
            )
            return await ctx.reply(embed=embed, mention_author=False)
        try:
            await role.edit(
                display_icon=display_icon,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: Updated **{role}** role icon.",
                color=0x313338,
            )
            return await ctx.reply(embed=embed, mention_author=False)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command("name")
    async def role_name(
        self,
        ctx: commands.Context,
        role: StrictRole(check_integrated=False),
        *,
        name: str,
    ):
        """Change a role's name."""
        old_name = role.name
        await role.edit(name=name)
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: Changed role name **{old_name}** to **{name}**.",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    @role.command("delete")
    async def role_delete(
        self,
        ctx: commands.Context,
        role: StrictRole(check_integrated=True),
    ):
        """Delete a role."""
        await role.delete()
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: Deleted the role **{role.name}**",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    @role.command("add")
    async def role_add(
        self, ctx: commands.Context, member: TouchableMember, *, role: StrictRole
    ):
        """Add a role to a member."""
        if role in member.roles:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: **{member}** already has the role **{role}**. Maybe try removing it instead.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return
        reason = get_audit_reason(ctx.author)
        await member.add_roles(role, reason=reason)
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: Added **{role.name}** to **{member}**.",
            color=0x313338,
        )
        return await ctx.reply(embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command("remove")
    async def role_remove(
        self, ctx: commands.Context, member: TouchableMember, *, role: StrictRole
    ):
        """Remove a role from a member."""
        if role not in member.roles:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: **{member}** doesn't have the role **{role}**.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return
        reason = get_audit_reason(ctx.author)
        await member.remove_roles(role, reason=reason)
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: Removed **{role.name}** from **{member}**.",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command(require_var_positional=True)
    async def addmulti(
        self, ctx: commands.Context, role: StrictRole, *members: TouchableMember
    ):
        """Add a role to multiple members."""
        reason = get_audit_reason(ctx.author)
        already_members = []
        success_members = []
        for member in members:
            if role not in member.roles:
                await member.add_roles(role, reason=reason)
                success_members.append(member)
            else:
                already_members.append(member)
        msg = []
        if success_members:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: Added **{role}** to {humanize_roles(success_members)}.",
                color=0x313338,
            )
        if already_members:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: {humanize_roles(already_members)} already had **{role}**.",
                color=0x313338,
            )
        await ctx.reply("\n".join(msg), embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command(require_var_positional=True)
    async def removemulti(
        self, ctx: commands.Context, role: StrictRole, *members: TouchableMember
    ):
        """Remove a role from multiple members."""
        reason = get_audit_reason(ctx.author)
        already_members = []
        success_members = []
        for member in members:
            if role in member.roles:
                await member.remove_roles(role, reason=reason)
                success_members.append(member)
            else:
                already_members.append(member)
        msg = []
        if success_members:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: Removed **{role}** from {humanize_roles(success_members)}.",
                color=0x313338,
            )
        if already_members:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: {humanize_roles(already_members)} didn't have **{role}**.",
                color=0x313338,
            )
        await ctx.reply("\n".join(msg), embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.group(invoke_without_command=True, require_var_positional=True)
    async def multirole(
        self, ctx: commands.Context, member: TouchableMember, *roles: StrictRole
    ):
        """Add multiple roles to a member."""
        not_allowed = []
        already_added = []
        to_add = []
        for role in roles:
            allowed = await is_allowed_by_role_hierarchy(
                self.bot, ctx.me, ctx.author, role
            )
            if not allowed[0]:
                not_allowed.append(role)
            elif role in member.roles:
                already_added.append(role)
            else:
                to_add.append(role)
        reason = get_audit_reason(ctx.author)
        msg = []
        if to_add:
            await member.add_roles(*to_add, reason=reason)
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: Added {humanize_roles(to_add)} to **{member}**.",
                color=0x313338,
            )
        if already_added:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: **{member}** already had {humanize_roles(already_added)}.",
                color=0x313338,
            )
        if not_allowed:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: You do not have permission to assign the roles {humanize_roles(not_allowed)}.",
                color=0x313338,
            )
        await ctx.reply("\n".join(msg), embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @multirole.command("remove", require_var_positional=True)
    async def multirole_remove(
        self, ctx: commands.Context, member: TouchableMember, *roles: StrictRole
    ):
        """Remove multiple roles from a member."""
        not_allowed = []
        not_added = []
        to_rm = []
        for role in roles:
            allowed = await is_allowed_by_role_hierarchy(
                self.bot, ctx.me, ctx.author, role
            )
            if not allowed[0]:
                not_allowed.append(role)
            elif role not in member.roles:
                not_added.append(role)
            else:
                to_rm.append(role)
        reason = get_audit_reason(ctx.author)
        msg = []
        if to_rm:
            await member.remove_roles(*to_rm, reason=reason)
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: Removed {humanize_roles(to_rm)} from **{member}**.",
                color=0x313338,
            )
        if not_added:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: **{member}** didn't have {humanize_roles(not_added)}.",
                color=0x313338,
            )
        if not_allowed:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: You do not have permission to assign the roles {humanize_roles(not_allowed)}.",
                color=0x313338,
            )
        await ctx.reply("\n".join(msg), embed=embed, mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command()
    async def all(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all members of the server."""
        await self.super_massrole(ctx, ctx.guild.members, role)

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command(aliases=["removeall"])
    async def rall(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all members of the server."""
        member_list = self.get_member_list(ctx.guild.members, role, False)
        await self.super_massrole(
            ctx, member_list, role, "No one on the server has this role.", False
        )

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command()
    async def humans(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all humans (non-bots) in the server."""
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if not member.bot],
            role,
            "Every human in the server has this role.",
        )

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command()
    async def rhumans(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all humans (non-bots) in the server."""
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if not member.bot],
            role,
            "None of the humans in the server have this role.",
            False,
        )

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command()
    async def bots(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all bots in the server."""
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if member.bot],
            role,
            "Every bot in the server has this role.",
        )

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command()
    async def rbots(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all bots in the server."""
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if member.bot],
            role,
            "None of the bots in the server have this role.",
            False,
        )

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command("in")
    async def role_in(
        self, ctx: commands.Context, target_role: FuzzyRole, *, add_role: StrictRole
    ):
        """Add a role to all members of a another role."""
        await self.super_massrole(
            ctx,
            [member for member in target_role.members],
            add_role,
            f"Every member of **{target_role}** has this role.",
        )

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.command("rin")
    async def role_rin(
        self, ctx: commands.Context, target_role: FuzzyRole, *, remove_role: StrictRole
    ):
        """Remove a role from all members of a another role."""
        await self.super_massrole(
            ctx,
            [member for member in target_role.members],
            remove_role,
            f"No one in **{target_role}** has this role.",
            False,
        )

    @commands.check(targeter_cog)
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @role.group()
    async def target(self, ctx: commands.Context):
        """
        Modify roles using 'targeting' args.

        An explanation of Targeter and test commands to preview the members affected can be found with `[p]target`.
        """

    @target.command("add")
    async def target_add(
        self, ctx: commands.Context, role: StrictRole, *, args: TargeterArgs
    ):
        """
        Add a role to members using targeting args.

        An explanation of Targeter and test commands to preview the members affected can be found with `[p]target`.
        """
        await self.super_massrole(
            ctx,
            args,
            role,
            f"No one was found with the given args that was eligible to recieve **{role}**.",
        )

    @target.command("remove")
    async def target_remove(
        self, ctx: commands.Context, role: StrictRole, *, args: TargeterArgs
    ):
        """
        Remove a role from members using targeting args.

        An explanation of Targeter and test commands to preview the members affected can be found with `[p]target`.
        """
        await self.super_massrole(
            ctx,
            args,
            role,
            f"No one was found with the given args that was eligible have **{role}** removed from them.",
            False,
        )

    async def super_massrole(
        self,
        ctx: commands.Context,
        members: list,
        role: discord.Role,
        fail_message: str = "Everyone in the server has this role.",
        adding: bool = True,
    ) -> None:
        if guild_roughly_chunked(ctx.guild) is False and self.bot.intents.members:
            await ctx.guild.chunk()
        member_list = self.get_member_list(members, role, adding)
        if not member_list:
            await ctx.send(fail_message)
            return
        verb = "add" if adding else "remove"
        word = "to" if adding else "from"
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: Beginning to {verb} **{role.name}** {word} **{len(member_list)}** members.",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=False)
        await self.massrole(member_list, [role], get_audit_reason(ctx.author), adding)
        await ctx.send(
            embed=discord.Embed(
                description=f"> {ctx.author.mention}: {verb.title()[:5]}ed **{role.name}** {word} **{len(member_list)}** members.",
                color=0x313338,
            )
        )

    def get_member_list(
        self, members: List[discord.Member], role: discord.Role, adding: bool = True
    ) -> List[discord.Member]:
        if adding:
            members = [member for member in members if role not in member.roles]
        else:
            members = [member for member in members if role in member.roles]
        return members

    async def massrole(
        self,
        members: List[discord.Member],
        roles: List[discord.Role],
        reason: str,
        adding: bool = True,
    ) -> Dict[str, List[discord.Member]]:
        completed: List[discord.Member] = []
        skipped: List[discord.Member] = []
        failed: List[discord.Member] = []
        for member in members:
            if adding:
                to_add = [role for role in roles if role not in member.roles]
                if to_add:
                    try:
                        await member.add_roles(*to_add, reason=reason)
                    except Exception as e:
                        failed.append(member)
                        log.exception(f"Failed to add roles to {member}", exc_info=e)
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
            else:
                to_remove = [role for role in roles if role in member.roles]
                if to_remove:
                    try:
                        await member.remove_roles(*to_remove, reason=reason)
                    except Exception as e:
                        failed.append(member)
                        log.exception(
                            f"Failed to remove roles from {member}", exc_info=e
                        )
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
        return {"completed": completed, "skipped": skipped, "failed": failed}

    @staticmethod
    def format_members(members: List[discord.Member]) -> str:
        length = len(members)
        s = "" if length == 1 else "s"
        return f"**{hn(length)}** member{s}"

    @role.command("uniquemembers", aliases=["um"], require_var_positional=True)
    async def role_uniquemembers(self, ctx: commands.Context, *roles: FuzzyRole):
        """
        View the total unique members between multiple roles.
        """
        roles_length = len(roles)
        if roles_length == 1:
            raise commands.UserFeedbackCheckFailure(
                "You must provide at least 2 roles."
            )
        if not ctx.guild.chunked:
            await ctx.guild.chunk()
        color = roles[0].color
        unique_members = set()
        description = []
        for role in roles:
            unique_members.update(role.members)
            description.append(f"{role.mention}: {self.format_members(role.members)}")
        description.insert(
            0, f"**Unique members**: {self.format_members(unique_members)}"
        )
        e = discord.Embed(
            color=color,
            title=f"Unique members between {roles_length} roles",
            description="\n".join(description),
        )
        ref = ctx.message.to_reference(fail_if_not_exists=False)
        await ctx.send(embed=e, reference=ref)
