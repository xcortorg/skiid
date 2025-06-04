import discord

from logging import getLogger
from typing import Annotated

from discord import Message, Role
from discord.ext.commands import group, has_permissions

from tools import CompositeMetaClass, MixinMeta
from core.client.context import Context
from tools.conversion import StrictRole
from .dynamicrolebutton import DynamicRoleButton

log = getLogger("evict/buttonroles")


class Buttons(MixinMeta, metaclass=CompositeMetaClass):
    """
    Allow members to assign roles to themselves using buttons.
    """

    @group(
        name="rolebuttons",
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def rolebutton(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @has_permissions(manage_messages=True)
    @rolebutton.command(
        name="add",
        example="(message) (emoji) (role)",
    )
    async def rolebutton_add(
        self,
        ctx: Context,
        message: Message,
        emoji: str,
        role: Annotated[
            Role,
            StrictRole(check_dangerous=True),
        ],
    ):
        """
        Add a reaction button to a message.
        """

        prefix = await self.bot.get_prefix(ctx.message)
        if message.author.id != self.bot.user.id:
            return await ctx.warn(
                f"I can only add role **buttons** to my own **messages**. You can create an **embed** using `{prefix}createembed (code)` and add the **button** there."
            )

        if role.is_premium_subscriber():
            return await ctx.warn("I cant assign integrated roles to users.")

        view = discord.ui.View()

        for component in message.components:
            if isinstance(component, discord.components.ActionRow):
                for button in component.children:
                    if button.custom_id == f"RB:{message.id}:{role.id}":
                        return await ctx.warn(
                            f"**role** {role.mention} is already **assigned** to this **message**."
                        )

                    if button.custom_id.startswith("RB"):
                        view.add_item(
                            DynamicRoleButton(
                                message_id=button.custom_id.split(":")[1],
                                role_id=button.custom_id.split(":")[2],
                                emoji=button.emoji,
                            )
                        )

                    else:
                        view.add_item(
                            discord.ui.Button(
                                style=button.style,
                                label=button.label,
                                emoji=button.emoji,
                                url=button.url,
                                disabled=button.disabled,
                            )
                        )
        view.add_item(
            DynamicRoleButton(message_id=message.id, role_id=role.id, emoji=emoji)
        )
        await message.edit(view=view)
        return await ctx.approve(
            f"added **role** {role.mention} to [**message**]({message.jump_url})"
        )

    @rolebutton.command(
        name="remove",
        example="(message) (role)",
    )
    @has_permissions(manage_messages=True)
    async def rolebutton_remove(
        self, ctx: Context, message: discord.Message, role: discord.Role
    ):
        """
        Remove a reaction button from a message.
        """
        prefix = await self.bot.get_prefix(ctx.message)
        if message.author.id != self.bot.user.id:
            return await ctx.warn(
                f"I can only remove role **buttons** to my own **messages**. You can create an **embed** using `{prefix}createembed (code)` and add the **button** there."
            )
        view = discord.ui.View()
        for component in message.components:
            if isinstance(component, discord.components.ActionRow):
                for button in component.children:
                    if button.custom_id == f"RB:{message.id}:{role.id}":
                        continue
                    if button.custom_id.startswith("RB"):
                        view.add_item(
                            DynamicRoleButton(
                                message_id=message.id,
                                role_id=role.id,
                                emoji=button.emoji,
                            )
                        )
                    else:
                        view.add_item(
                            discord.ui.Button(
                                style=button.style,
                                label=button.label,
                                emoji=button.emoji,
                                url=button.url,
                                disabled=button.disabled,
                            )
                        )
        await message.edit(view=view)
        return await ctx.approve(
            f"removed **role** {role.mention} from [**message**]({message.jump_url})"
        )
