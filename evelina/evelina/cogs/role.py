import io
import json
import asyncio

from PIL import Image
from typing import Union
from modules.styles import emojis
from humanfriendly import format_timespan

from discord import Embed, Member, PartialEmoji, Colour, Emoji, Forbidden
from discord.errors import NotFound
from discord.ext.commands import Cog, group, has_guild_permissions, bot_has_guild_permissions

from modules.styles import colors
from modules.predicates import boosted_to
from modules.converters import NewRoleConverter, HexColor
from modules.evelinabot import Evelina, EvelinaContext

class Role(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Role commands"
        self.role_lock = {}
        self.locks = {}

    async def get_emoji_image(self, emoji):
        if isinstance(emoji, PartialEmoji) or isinstance(emoji, Emoji):
            url = emoji.url
            image_data = await self.bot.session.get_bytes(url)
            if image_data:
                image = Image.open(io.BytesIO(image_data)).convert("RGBA")
                return image
        return None

    @group(name="role", brief="manage roles", aliases=["r"], invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role(self, ctx: EvelinaContext, member: Member = None, *, roles: str = None):
        """Add/remove roles to/from a member"""
        if member and roles:
            return await ctx.invoke(self.bot.get_command("role manage"), member=member, roles=roles)
        else:
            return await ctx.create_pages()

    @role.group(name="all", brief="manage roles", invoke_without_command=True, case_insensitive=True)
    async def role_all(self, ctx: EvelinaContext):
        """Add or remove roles from all members"""
        return await ctx.create_pages()

    @role_all.command(name="add", brief="manage roles", usage="role all add humans member")
    async def role_all_add(self, ctx: EvelinaContext, type: str, *, role: NewRoleConverter):
        """Add a role to all members of a specified type (Humans, Bots, Members)"""
        await self.modify_role(ctx, type, role, action="add")

    @role_all.command(name="remove", brief="manage roles", usage="role all remove humans member")
    async def role_all_remove(self, ctx: EvelinaContext, type: str, *, role: NewRoleConverter):
        """Remove a role from all members of a specified type (Humans, Bots, Members)"""
        await self.modify_role(ctx, type, role, action="remove")

    async def modify_role(self, ctx: EvelinaContext, type: str, role, action: str):
        if type.lower() not in ["humans", "bots", "members"]:
            return await ctx.send_warning("Invalid type specified. Use `Humans`, `Bots`, or `Members`.")
        members = []
        if type.lower() == "humans":
            members = [m for m in ctx.guild.members if not m.bot]
        elif type.lower() == "bots":
            members = [m for m in ctx.guild.members if m.bot]
        elif type.lower() == "members":
            members = ctx.guild.members
        async with self.role_lock.setdefault(ctx.guild.id, asyncio.Lock()):
            if action == "add":
                tasks = [m.add_roles(role, reason=f"Role all add invoked by {ctx.author}") for m in members if role not in m.roles]
                action_description = "Added"
                preposition = "to"
            elif action == "remove":
                tasks = [m.remove_roles(role, reason=f"Role all remove invoked by {ctx.author}") for m in members if role in m.roles]
                action_description = "Removed"
                preposition = "from"
            else:
                return await ctx.send_warning("Invalid action specified. Use `add` or `remove`.")
            if len(tasks) == 0:
                return await ctx.send_warning(f"No members to {action_description.lower()} the role.")
            mes = await ctx.evelina_send(f"{action_description} {role.mention} {preposition} **{len(tasks)}** members.\n> This operation might take around **{format_timespan(0.3*len(tasks))}**")
            success_count = 0
            batch_size = 5
            delay_between_batches = 5
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i+batch_size]
                results = await asyncio.gather(*batch, return_exceptions=True)
                for result in results:
                    if isinstance(result, NotFound):
                        continue
                    elif isinstance(result, Exception):
                        continue
                    success_count += 1
                if i + batch_size < len(tasks):
                    await asyncio.sleep(delay_between_batches)
            try:
                return await mes.edit(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {ctx.author.mention}: {action_description} {role.mention} {preposition} **{success_count}** members"))
            except NotFound:
                return await ctx.send_success(f"{action_description} {role.mention} {preposition} **{success_count}** members")
        
    @role.group(name="edit", brief="manage roles", invoke_without_command=True, case_insensitive=True)
    async def role_edit(self, ctx: EvelinaContext):
        """Edit a role's name, icon & color"""
        return await ctx.create_pages()

    @role_edit.command(name="name", brief="manage roles", usage="role edit name booster gang")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_edit_name(self, ctx: EvelinaContext, role: NewRoleConverter, *, name: str):
        """Edit a role's name"""
        await role.edit(name=name, reason=f"Role name edited by {ctx.author}")
        return await ctx.send_success(f"Role name edited to **{name}**")

    @role_edit.command(name="icon", brief="manage roles", usage="role edit icon booster :boost:")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    @boosted_to(2)
    async def role_edit_icon(self, ctx: EvelinaContext, role: NewRoleConverter, *, emoji: Union[PartialEmoji, str]):
        """Edit a role's icon"""
        if emoji == 'none':
            await role.edit(display_icon=None, reason=f"Role icon removed by {ctx.author}")
            return await ctx.send_success(f"Role icon successfully removed")
        try:
            if isinstance(emoji, PartialEmoji) or isinstance(emoji, Emoji):
                image = await self.get_emoji_image(emoji)
                if image:
                    with io.BytesIO() as buffer:
                        image.save(buffer, format="PNG")
                        buffer.seek(0)
                        display_icon = buffer.read()
                else:
                    return await ctx.send_warning(f"Unable to retrieve or process the emoji image.")
            else:
                display_icon = emoji
            await role.edit(display_icon=display_icon, reason=f"Role icon edited by {ctx.author}")
            return await ctx.send_success(f"Role icon successfully changed to **{emoji if isinstance(emoji, (PartialEmoji, Emoji)) else emoji}**")
        except Exception as e:
            return await ctx.send_warning(f"Given emoji is invalid or there was an error: {str(e)}")
    
    @role_edit.command(name="hoist", brief="manage roles", usage="role edit hoist booster")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_edit_hoist(self, ctx: EvelinaContext, *, role: NewRoleConverter):
        """Make a role hoisted or not"""
        await role.edit(hoist=not role.hoist, reason=f"Role hoist edited by {ctx.author}")
        return await ctx.send_success(f"Role {'is now hoisted' if not role.hoist else 'is not hoisted anymore'}")

    @role_edit.command(name="color", aliases=["colour"], brief="manage roles", usage="role edit color #ff00ff")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_edit_color(self, ctx: EvelinaContext, role: NewRoleConverter, color: HexColor):
        """Edit a role's color"""
        await role.edit(color=color.value, reason=f"Color changed by {ctx.author}")
        await ctx.send(embed=Embed(color=color.value, description=f"{ctx.author.mention}: Changed the role's color to `{color.hex}`"))

    @role.command(name="create", brief="manage roles", usage="role create boss #00ff00")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_create(self, ctx: EvelinaContext, name: str, colour: Colour = Colour.default()):
        """Create a new role with an optional colour"""
        guild = ctx.guild
        existing_role = next((role for role in guild.roles if role.name == name), None)
        if existing_role:
            return await ctx.send_warning(f"A role with the name `{name}` already exists.")
        new_role = await guild.create_role(name=name, colour=colour, reason=f"Role created by {ctx.author}")
        return await ctx.send_success(f"Role `{name}` created successfully.")

    @role.command(name="delete", brief="manage roles", usage="role delete boss")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_delete(self, ctx: EvelinaContext, *, role: NewRoleConverter):
        """Delete an existing role"""
        if role.position > ctx.guild.me.top_role.position:
            return await ctx.send_warning(f"Role {role.mention} is over my highest role")
        try:
            await role.delete(reason=f"Role deleted by {ctx.author}")
        except Forbidden:
            return await ctx.send_warning(f"I don't have permission to delete the role {role.mention}")
        except NotFound:
            return await ctx.send_warning(f"Role {role.mention} not found")
        return await ctx.send_success(f"Role `{role}` deleted successfully.")

    @role.command(name="manage", brief="manage roles", usage="role manage comminate member")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_manage(self, ctx: EvelinaContext, member: Member, *, roles: str):
        """Add/remove roles to/from a member"""
        roles = [await NewRoleConverter().convert(ctx, r) for r in roles.split(", ")]
        if len(roles) == 0:
            return await ctx.send_help(ctx.command)
        if len(roles) > 7:
            return await ctx.send_warning("You can't give more than 7 roles at once")
        role_lock_data = await self.bot.db.fetchrow("SELECT * FROM antinuke_roles WHERE guild_id = $1", ctx.guild.id)
        locked_roles = json.loads(role_lock_data['roles']) if role_lock_data else []
        role_lock_status = role_lock_data['status'] if role_lock_data else False
        if any(self.bot.misc.is_dangerous(r) for r in roles):
            if await self.bot.an.is_module("role giving", ctx.guild):
                if not await self.bot.an.is_whitelisted(ctx.author):
                    roles = [r for r in roles if not self.bot.misc.is_dangerous(r)]
        if role_lock_status and not await self.bot.an.is_whitelisted(ctx.author):
            roles = [r for r in roles if r.id not in locked_roles]
        if len(roles) > 0:
            async with self.locks.setdefault(ctx.guild.id, asyncio.Lock()):
                role_mentions = []
                for role in roles:
                    if not role in member.roles:
                        await member.add_roles(role, reason=f"{ctx.author} added the role")
                        role_mentions.append(f"**+**{role.mention}")
                    else:
                        await member.remove_roles(role, reason=f"{ctx.author} removed the role")
                        role_mentions.append(f"**-**{role.mention}")
                return await ctx.send_success(f"Edited {member.mention}'s roles: {', '.join(role_mentions)}")
        else:
            return await ctx.send_warning("You can't give any roles with dangerous permissions or locked roles.")
        
    @role.group(name="copy", brief="manage roles", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_copy(self, ctx: EvelinaContext):
        """Copy a role's permissions to another role"""
        return await ctx.create_pages()
    
    @role_copy.command(name="permissions", brief="manage roles", usage="role copy permissions booster gang")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_copy_permissions(self, ctx: EvelinaContext, role: NewRoleConverter, target: NewRoleConverter):
        """Copy a role's permissions to another role"""
        await target.edit(permissions=role.permissions, reason=f"Role permissions copied by {ctx.author}")
        return await ctx.send_success(f"Role permissions copied from {role.mention} to {target.mention}")
    
    @role_copy.command(name="color", brief="manage roles", usage="role copy color booster gang")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_copy_color(self, ctx: EvelinaContext, role: NewRoleConverter, target: NewRoleConverter):
        """Copy a role's color to another role"""
        await target.edit(color=role.color, reason=f"Role color copied by {ctx.author}")
        return await ctx.send_success(f"Role color copied from {role.mention} to {target.mention}")
    
    @role_copy.command(name="name", brief="manage roles", usage="role copy name booster gang")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_copy_name(self, ctx: EvelinaContext, role: NewRoleConverter, target: NewRoleConverter):
        """Copy a role's name to another role"""
        await target.edit(name=role.name, reason=f"Role name copied by {ctx.author}")
        return await ctx.send_success(f"Role name copied from {role.mention} to {target.mention}")
    
    @role_copy.command(name="all", brief="manage roles", usage="role copy all booster gang")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def role_copy_all(self, ctx: EvelinaContext, role: NewRoleConverter, target: NewRoleConverter):
        """Copy a role's name, color, permissions, hoist, icon, and more to another role"""
        await target.edit(
            name=role.name,
            color=role.color,
            permissions=role.permissions,
            hoist=role.hoist,
            mentionable=role.mentionable,
            reason=f"Role copied by {ctx.author}"
        )
        return await ctx.send_success(f"Role {role.mention} copied to {target.mention}")

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Role(bot))