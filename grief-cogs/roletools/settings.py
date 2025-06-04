from typing import Optional, Union

from red_commons.logging import getLogger

from grief.core import commands
from grief.core.commands import Context
from grief.core.i18n import Translator

from .abc import RoleToolsMixin
from .converter import RoleHierarchyConverter

roletools = RoleToolsMixin.roletools

log = getLogger("grief.roletools")
_ = Translator("RoleTools", __file__)


class RoleToolsSettings(RoleToolsMixin):
    """This class handles setting the roletools role settings."""

    # @roletools.command()
    # @commands.has_permissions(manage_roles=True)
    # async def selfadd(
    #  self,
    # ctx: Context,
    #     true_or_false: Optional[bool] = None,
    #      #    *,
    #     role: RoleHierarchyConverter,
    #  ) -> None:
    #   """
    #   Set whether or not a user can apply the role to themselves.
    #
    #  `[true_or_false]` optional boolean of what to set the setting to.
    #    If not provided the current setting will be shown instead.
    #    `<role>` The role you want to set.
    #        """
    #     await ctx.typing()

    #     cur_setting = await self.config.role(role).selfassignable()
    #         if true_or_false is None:
    #          if cur_setting:
    #              msg = _("The {role} role is self assignable.").format(role=role.mention)
    #              await ctx.send(msg)
    #          else:
    #              command = f"`{ctx.clean_prefix}roletools selfadd yes {role.name}`"
    #              msg = _(
    #                 "The {role} role is not self assignable. Run the command "
    #              "{command} to make it self assignable."
    #           ).format(role=role.mention, command=command)
    #           await ctx.send(msg)
    #        return
    #     if true_or_false is True:
    #              await self.config.role(role).selfassignable.set(True)
    #           msg = _("The {role} role is now self assignable.").format(role=role.mention)
    #          await ctx.send(msg)
    #       if true_or_false is False:
    #           await self.config.role(role).selfassignable.set(False)
    #           msg = _("The {role} role is no longer self assignable.").format(role=role.mention)
    #           await ctx.send(msg)

    #   @roletools.command()
    #  @commands.has_permissions(manage_roles=True)
    #   async def selfrem(
    #       self,    #     #       ctx: Context,
    #       true_or_false: Optional[bool] = None,
    #       *,
    #        role: RoleHierarchyConverter,
    #    ) -> None:
    #        """
    #        Set whether or not a user can remove the role from themselves.
    #
    #        `[true_or_false]` optional boolean of what to set the setting to.
    #        If not provided the current setting will be shown instead.
    #        `<role>` The role you want to set.
    #        """
    #        await ctx.typing()
    #
    #        cur_setting = await self.config.role(role).selfremovable()
    #        if true_or_false is None:
    #            if cur_setting:
    #                msg = _("The {role} role is self removeable.").format(role=role.mention)
    #                await ctx.send(msg)
    #            else:
    #               command = f"`{ctx.clean_prefix}roletools selfrem yes {role.name}`"
    #            msg = _(
    #                   "The {role} role is not self removable. Run the command "
    #                   "{command} to make it self removeable."
    #               ).format(role=role.mention, command=command)
    #               await ctx.send(msg)
    #           return
    #       if true_or_false is True:
    #        await self.config.role(role).selfremovable.set(True)
    #           msg = _("The {role} role is now self removeable.").format(role=role.mention)
    #           await ctx.send(msg)
    #    if true_or_false is False:
    #         await self.config.role(role).selfremovable.set(False)
    #             msg = _("The {role} role is no longer self removeable.").format(role=role.mention)
    #      await ctx.send(msg)

    # @roletools.command(with_app_command=False)
    # @commands.admin_or_permissions(manage_roles=True)
    # async def atomic(self, ctx: Context, true_or_false: Optional[Union[bool, str]] = None) -> None:
    # """
    # Set the atomicity of role assignment.
    # What this means is that when this is `True` roles will be
    # applied inidvidually and not cause any errors. When this
    # is set to `False` roles will be grouped together into one call.

    # This can cause race conditions if you have other methods of applying
    # roles setup when set to `False`.

    # [true_or_false ]` optional boolean of what to set the setting to.
    # To reset back to the default global rules use `clear`.
    # If not provided the current setting will be shown instead.
    #  """
    # cur_setting = await self.config.guild(ctx.guild).atomic()
    # if true_or_false is None or true_or_false not in ["clear", True, False]:
    #    if cur_setting is True:
    #       msg = _("This server is currently using atomic role assignment")
    #  elif cur_setting is False:
    #     msg = _("This server is not currently using atomic role assignment.")
    # else:
    #    msg = _(
    #       "This server currently using the global atomic "
    #      "role assignment setting `{current_global}`."
    # ).format(current_global=await self.config.atomic())
    # command = f"`{ctx.clean_prefix}roletools atomic yes`"
    # cmd_msg = _("Do {command} to atomically assign roles.").format(command=command)
    # await ctx.send(f"{msg} {cmd_msg}")
    # return
    # elif true_or_false is True:
    # await self.config.guild(ctx.guild).atomic.set(True)
    # msg = _("RoleTools will now atomically assign roles.")
    # elif true_or_false is False:
    # await self.config.guild(ctx.guild).atomic.set(False)
    # msg = _("RoleTools will no longer atomically assign roles.")
    # else:
    # await self.config.guild(ctx.guild).atomic.clear()
    # msg = _("RoleTools will now default to the global atomic setting.")
    # await ctx.send(msg)

    # @roletools.command(with_app_command=False)
    # @commands.is_owner()
    # @commands.command(hidden=True)
    # async def globalatomic(self, ctx: Context, true_or_false: Optional[bool] = None) -> None:
    # """
    # Set the atomicity of role assignment.
    # What this means is that when this is `True` roles will be
    # applied inidvidually and not cause any errors. When this
    # is set to `False` roles will be grouped together into one call.

    # This can cause race conditions if you have other methods of applying
    # roles setup when set to `False`.

    # [true_or_false]` optional boolean of what to set the setting to.
    # If not provided the current setting will be shown instead.
    # """
    # cur_setting = await self.config.atomic()
    # if true_or_false is None:
    # if cur_setting:
    #  await ctx.send(_("I am currently using atomic role assignment"))
    #  else:
    #  command = f"`{ctx.clean_prefix}roletools globalatomic yes`"
    #  await ctx.send(
    #      _(
    #              "I am not currently using atomic role assignment. Do "
    #        "{command} to atomically assign roles."
    #    ).format(command=command)
    #   )
    #   return
    #     if true_or_false is True:
    #    await self.config.atomic.clear()
    #    await ctx.send(_("RoleTools will now atomically assign roles."))
    # if true_or_false is False:
    #    await self.config.atomic.set(False)
    #     await ctx.send(_("RoleTools will no longer atomically assign roles."))

    @roletools.command()
    @commands.has_permissions(manage_roles=True)
    async def sticky(
        self,
        ctx: Context,
        true_or_false: Optional[bool] = None,
        *,
        role: RoleHierarchyConverter,
    ) -> None:
        """
        Set whether or not a role will be re-applied when a user leaves and rejoins the server.

        `[true_or_false]` optional boolean of what to set the setting to.
        If not provided the current setting will be shown instead.
        `<role>` The role you want to set.
        """
        await ctx.typing()

        cur_setting = await self.config.role(role).sticky()
        if true_or_false is None:
            if cur_setting:
                msg = _("The {role} role is sticky.").format(role=role.mention)
                await ctx.send(msg)
            else:
                command = f"{ctx.clean_prefix}roletools sticky yes {role.name}"
                msg = _(
                    "The {role} role is not sticky. Run the command "
                    "{command} to make it sticky."
                ).format(role=role.mention, command=command)
                await ctx.send(msg)
            return
        if true_or_false is True:
            await self.config.role(role).sticky.set(True)
            msg = _("The {role} role is now sticky.").format(role=role.mention)
        if true_or_false is False:
            await self.config.role(role).sticky.set(False)
            msg = _("The {role} role is no longer sticky.").format(role=role.mention)
        await ctx.send(msg)

    @roletools.command(aliases=["auto"])
    @commands.has_permissions(manage_roles=True)
    async def autorole(
        self,
        ctx: Context,
        true_or_false: Optional[bool] = None,
        *,
        role: RoleHierarchyConverter,
    ) -> None:
        """
        Set a role to be automatically applied when a user joins the server.

        `[true_or_false]` optional boolean of what to set the setting to.
        If not provided the current setting will be shown instead.
        `<role>` The role you want to set.
        """
        await ctx.typing()

        cur_setting = await self.config.role(role).auto()
        if true_or_false is None:
            if cur_setting:
                msg = _("The role {role} is automatically applied on joining.").format(
                    role=role
                )
                await ctx.send(msg)
            else:
                command = f"`{ctx.clean_prefix}roletools auto yes {role.name}`"
                msg = _(
                    "The {role} role is not automatically applied "
                    "when a member joins  this server. Run the command "
                    "{command} to make it automatically apply when a user joins."
                ).format(role=role.mention, command=command)
                await ctx.send(msg)
            return
        if true_or_false is True:
            async with self.config.guild(ctx.guild).auto_roles() as current_roles:
                if role.id not in current_roles:
                    current_roles.append(role.id)
                if ctx.guild.id not in self.settings:
                    self.settings[ctx.guild.id] = await self.config.guild(
                        ctx.guild
                    ).all()
                if role.id not in self.settings[ctx.guild.id]["auto_roles"]:
                    self.settings[ctx.guild.id]["auto_roles"].append(role.id)
            await self.config.role(role).auto.set(True)
            msg = _(
                "The {role} role will now automatically be applied when a user joins."
            ).format(role=role.mention)
            await ctx.send(msg)
        if true_or_false is False:
            async with self.config.guild(ctx.guild).auto_roles() as current_roles:
                if role.id in current_roles:
                    current_roles.remove(role.id)
                if (
                    ctx.guild.id in self.settings
                    and role.id in self.settings[ctx.guild.id]["auto_roles"]
                ):
                    self.settings[ctx.guild.id]["auto_roles"].remove(role.id)
            await self.config.role(role).auto.set(False)
            msg = _(
                "The {role} role will not automatically be applied when a user joins."
            ).format(role=role.mention)
            await ctx.send(msg)
