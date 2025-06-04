import datetime

from typing import Union

from discord import User, Invite
from discord.ext.commands import Cog, group, command

from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import is_manager
from modules.validators import ValidCommand

class Manager(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(name="beta", brief="bot manager", invoke_without_command=True, case_insensitive=True)
    @is_manager()
    async def beta(self, ctx: EvelinaContext):
        """Beta commands"""
        return await ctx.create_pages()
    
    @beta.command(name="add", brief="bot manager", usage="beta add comminate")
    @is_manager()
    async def beta_add(self, ctx: EvelinaContext, user: User):
        """Add a user to the beta program"""
        check = await self.bot.db.fetchrow("SELECT * FROM beta_testers WHERE user_id = $1", user.id)
        if check:
            return await ctx.send_warning(f"User {user.mention} is already in the beta program")
        else:
            await self.bot.manage.add_role(user, 1338968077957730356)
            await self.bot.db.execute("INSERT INTO beta_testers VALUES ($1)", user.id)
            return await ctx.send_success(f"Added {user.mention} to the beta program")
        
    @beta.command(name="remove", brief="bot manager", usage="beta remove comminate")
    @is_manager()
    async def beta_remove(self, ctx: EvelinaContext, user: User):
        """Remove a user from the beta program"""
        check = await self.bot.db.fetchrow("SELECT * FROM beta_testers WHERE user_id = $1", user.id)
        if not check:
            return await ctx.send_warning(f"User {user.mention} isn't in the beta program")
        else:
            await self.bot.manage.remove_role(user, 1338968077957730356)
            await self.bot.db.execute("DELETE FROM beta_testers WHERE user_id = $1", user.id)
            return await ctx.send_success(f"Removed {user.mention} from the beta program")
        
    @beta.command(name="list", brief="bot manager")
    @is_manager()
    async def beta_list(self, ctx: EvelinaContext):
        """List all users in the beta program"""
        results = await self.bot.db.fetch("SELECT * FROM beta_testers")
        if not results:
            return await ctx.send_warning(f"There are no beta users")
        return await ctx.paginate([f"<@{result['user_id']}>" for result in results], f"Beta users")
    
    @beta.group(name="command", brief="bot manager", invoke_without_command=True, case_insensitive=True)
    @is_manager()
    async def beta_command(self, ctx: EvelinaContext):
        """Beta command commands"""
        return await ctx.create_pages()
    
    @beta_command.command(name="add", brief="bot manager", usage="beta command add play")
    @is_manager()
    async def beta_command_add(self, ctx: EvelinaContext, command: ValidCommand):
        """Add a command to the beta program"""
        check = await self.bot.db.fetchrow("SELECT * FROM global_beta_commands WHERE command = $1", command)
        if check:
            return await ctx.send_warning(f"Command **{command}** is already in the beta program")
        else:
            await self.bot.db.execute("INSERT INTO global_beta_commands VALUES ($1, $2, $3, $4)", command, True, ctx.author.id, datetime.datetime.now().timestamp())
            return await ctx.send_success(f"Added **{command}** to the beta program")
        
    @beta_command.command(name="remove", brief="bot manager", usage="beta command remove play")
    @is_manager()
    async def beta_command_remove(self, ctx: EvelinaContext, command: ValidCommand):
        """Remove a command from the beta program"""
        check = await self.bot.db.fetchrow("SELECT * FROM global_beta_commands WHERE command = $1", command)
        if not check:
            return await ctx.send_warning(f"Command **{command}** isn't in the beta program")
        else:
            await self.bot.db.execute("DELETE FROM global_beta_commands WHERE command = $1", command)
            return await ctx.send_success(f"Removed **{command}** from the beta program")
        
    @beta_command.command(name="list", brief="bot manager")
    @is_manager()
    async def beta_command_list(self, ctx: EvelinaContext):
        """List all commands in the beta program"""
        results = await self.bot.db.fetch("SELECT * FROM global_beta_commands")
        if not results:
            return await ctx.send_warning(f"There are no beta commands")
        beta_list = [f"{result['command']} added by <@{result['user']}>" for result in results]
        return await ctx.smallpaginate(beta_list, f"Beta commands", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @group(name="creator", brief="bot manager", invoke_without_command=True, case_insensitive=True)
    @is_manager()
    async def creator(self, ctx: EvelinaContext):
        """Manage users permissions to post embeds on evelina's page"""
        return await ctx.create_pages()

    @creator.command(name="add", brief="bot manager", usage="creator add comminate")
    @is_manager()
    async def creator_add(self, ctx: EvelinaContext, user: User):
        """Add a user premissions to post embeds"""
        check = await self.bot.db.fetchrow("SELECT * FROM embeds_creator where user_id = $1", user.id)
        if check:
            return await ctx.send_warning(f"User {user.mention} is already permited to post embeds")
        else:
            await self.bot.db.execute("INSERT INTO embeds_creator VALUES ($1)", user.id)
            return await ctx.send_success(f"Permitted {user.mention} to post embeds")
        
    @creator.command(name="remove", brief="bot manager", usage="creator remove comminate")
    @is_manager()
    async def creator_remove(self, ctx: EvelinaContext, user: User):
        """Remove a user premissions to post embeds"""
        check = await self.bot.db.fetchrow("SELECT * FROM embeds_creator where user_id = $1", user.id)
        if not check:
            return await ctx.send_warning(f"User {user.mention} isn't permited to post embeds")
        else:
            await self.bot.db.execute("INSERT INTO embeds_creator VALUES ($1)", user.id)
            return await ctx.send_success(f"Prohibited {user.mention} to post embeds")
        
    @creator.command(name="list", brief="bot manager")
    @is_manager()
    async def donators(self, ctx: EvelinaContext):
        """List all premitted users that can post embeds"""
        results = await self.bot.db.fetch("SELECT * FROM embeds_creator")
        if not results:
            return await ctx.send_warning(f"There are no embed creators")
        return await ctx.paginate([f"<@!{result['user_id']}>" for result in results], f"Embed creators")
    
    @command(name="delvouch", brief="bot manager", usage="delvouch 65")
    @is_manager()
    async def delvouch(self, ctx: EvelinaContext, vouch_id: int):
        """Delete a vouch"""
        check = await self.bot.db.fetchval("SELECT * FROM vouches WHERE id = $1", vouch_id)
        if not check:
            return await ctx.send_warning(f"Vouch with ID **{vouch_id}** not found")
        await self.bot.db.execute("DELETE FROM vouches WHERE id = $1", vouch_id)
        await ctx.send_success(f"Vouch with ID **{vouch_id}** deleted successfully")

    @command(name="delavatar", brief="bot manager", usage="delavatar e864474905ce41826da62dc2e853183b.png")
    @is_manager()
    async def delavatar(self, ctx: EvelinaContext, avatar: str):
        """Deletes a specific avatar from R2 bucket and the database"""
        delete_res = await self.bot.r2.delete_file("evelina", avatar, "avatars")
        if delete_res:
            delete_result = await self.bot.db.execute("DELETE FROM avatar_history WHERE avatar = $1 AND user_id = $2", avatar, ctx.author.id)
            if delete_result == "DELETE 1":
                await ctx.send_success(f"Successfully deleted avatar from both R2 and your avatar history\n> **Avatar:** `{avatar}`")
            else:
                await ctx.send_warning(f"Avatar `{avatar}` not found in your avatar history")
        else:
            return await ctx.send_warning("An error occurred while deleting avatar")
    
    @group(name="instances", brief="bot manager", invoke_without_command=True, case_insensitive=True)
    @is_manager()
    async def instances(self, ctx: EvelinaContext):
        """Manage the bot's instances"""
        return await ctx.create_pages()

    @instances.command(name="setup", brief="bot manager", usage="instances setup evelina comminate /evelina")
    @is_manager()
    async def instances_setup(self, ctx: EvelinaContext, instance: User, owner: User, server: Union[Invite, int]):
        """Setup a new instance"""
        if not instance.bot:
            return await ctx.send_warning("Instance user must be a bot")
        if isinstance(server, Invite):
            server = server.guild.id
        await self.bot.db.execute("INSERT INTO instance VALUES ($1, $2, $3, $4, $5, $6)", instance.id, instance.name, int(datetime.datetime.now().timestamp()), owner.id, server, 3)
        await self.bot.manage.add_role(owner, 1284159368262324285)
        return await ctx.send_success(f"Instance **{instance.mention}** has been successfully created for {await self.bot.manage.guild_name(server, True)}\n> **Setuped:** <t:{int(datetime.datetime.now().timestamp())}:R> **Owned by:** {owner.mention}")

    @instances.command(name="add", brief="bot manager", usage="instances add evelina /evelina")
    @is_manager()
    async def instances_add(self, ctx: EvelinaContext, instance: User, server: Union[Invite, int]):
        """Add a new instance server"""
        if not instance.bot:
            return await ctx.send_warning("Instance user must be a bot")
        if isinstance(server, Invite):
            server = server.guild.id
        instance_data = await self.bot.db.fetchrow("SELECT * FROM instance WHERE user_id = $1", instance.id)
        if not instance_data:
            return await ctx.send_warning(f"Instance **{instance.mention}** not found")
        instance_check = await self.bot.db.fetchrow("SELECT * FROM instance WHERE user_id = $1 AND guild_id = $2", instance.id, server)
        if instance_check:
            return await ctx.send_warning(f"Instance **{instance.mention}** is already in {await self.bot.manage.guild_name(server, True)}")
        instance_check_addon = await self.bot.db.fetchrow("SELECT * FROM instance_addon WHERE user_id = $1 AND guild_id = $2", instance.id, server)
        if instance_check_addon:
            return await ctx.send_warning(f"Instance **{instance.mention}** is already in {await self.bot.manage.guild_name(server, True)}")
        await self.bot.db.execute("INSERT INTO instance_addon VALUES ($1, $2, $3, $4)", instance.id, datetime.datetime.now().timestamp(), instance_data['owner_id'], server)
        return await ctx.send_success(f"Instance **{instance.mention}** has been successfully added to {await self.bot.manage.guild_name(server, True)}")
    
    @instances.command(name="remove", brief="bot manager", usage="instances remove evelina /evelina")
    @is_manager()
    async def instances_remove(self, ctx: EvelinaContext, instance: User, server: Union[Invite, int]):
        """Remove an instance server"""
        if not instance.bot:
            return await ctx.send_warning("Instance user must be a bot")
        if isinstance(server, Invite):
            server = server.guild.id
        instance_data = await self.bot.db.fetchrow("SELECT * FROM instance WHERE user_id = $1", instance.id)
        if not instance_data:
            return await ctx.send_warning(f"Instance **{instance.mention}** not found")
        instance_check = await self.bot.db.fetchrow("SELECT * FROM instance_addon WHERE user_id = $1 AND guild_id = $2", instance.id, server)
        if not instance_check:
            return await ctx.send_warning(f"Instance **{instance.mention}** is not in {await self.bot.manage.guild_name(server, True)}")
        await self.bot.db.execute("DELETE FROM instance_addon WHERE user_id = $1 AND guild_id = $2", instance.id, server)
        return await ctx.send_success(f"Instance **{instance.mention}** has been successfully removed from {await self.bot.manage.guild_name(server, True)}")

    @instances.group(name="transfer", brief="bot manager", invoke_without_command=True, case_insensitive=True)
    @is_manager()
    async def instances_transfer(self, ctx: EvelinaContext):
        """Transfer an instance"""
        return await ctx.create_pages()
    
    @instances_transfer.command(name="owner", brief="bot manager", usage="instances transfer owner comminate curet")
    @is_manager()
    async def instances_transfer_owner(self, ctx: EvelinaContext, old_owner: User, new_owner: User):
        """Transfer an instance owner"""
        instance = await self.bot.db.fetchrow("SELECT * FROM instance WHERE owner_id = $1", old_owner.id)
        if not instance:
            return await ctx.send_warning(f"Instance owner **{old_owner.mention}** not found")
        await self.bot.db.execute("UPDATE instance SET owner_id = $1 WHERE owner_id = $2", new_owner.id, old_owner.id)
        await self.bot.db.execute("UPDATE instance_addon SET owner_id = $1 WHERE owner_id = $2", new_owner.id, old_owner.id)
        return await ctx.send_success(f"Instance owner **{old_owner.mention}** has been successfully transferred to **{new_owner.mention}**")

    @instances_transfer.command(name="server", brief="bot manager", usage="instances transfer server evelina /evelina /death")
    @is_manager()
    async def instances_transfer_server(self, ctx: EvelinaContext, instance: User, old_server: Union[Invite, int], new_server: Union[Invite, int]):
        """Transfer an instance server"""
        if not instance.bot:
            return await ctx.send_warning("Instance user must be a bot")
        if isinstance(old_server, Invite):
            old_server = old_server.guild.id
        if isinstance(new_server, Invite):
            new_server = new_server.guild.id
        instance_data = await self.bot.db.fetchrow("SELECT * FROM instance WHERE user_id = $1", instance.id)
        if not instance_data:
            return await ctx.send_warning(f"Instance **{instance.mention}** not found")
        instance_check = await self.bot.db.fetchrow("SELECT * FROM instance WHERE user_id = $1 AND guild_id = $2", instance.id, old_server)
        if not instance_check:
            return await ctx.send_warning(f"Instance **{instance.mention}** is not in {await self.bot.manage.guild_name(old_server, True)}")
        if instance_data['transfers'] <= 0:
            return await ctx.send_warning(f"Instance **{instance.mention}** has no transfers left")
        current_transfers = instance_data['transfers']
        if current_transfers <= 0:
            return await ctx.send_warning(f"Instance **{instance.mention}** has no transfers left")
        new_transfers = current_transfers - 1
        await self.bot.db.execute("UPDATE instance SET guild_id = $1, transfers = $2 WHERE user_id = $3 AND guild_id = $4", new_server, new_transfers, instance.id, old_server)
        return await ctx.send_success(f"Instance **{instance.mention}** has been successfully transferred from {await self.bot.manage.guild_name(old_server, True)} to {await self.bot.manage.guild_name(new_server, True)}")

    @instances.command(name="inspect", brief="bot manager")
    @is_manager()
    async def instances_inspect(self, ctx: EvelinaContext, user: User):
        """Inspect all instances from a user"""
        instances = await self.bot.db.fetch("SELECT * FROM instance WHERE owner_id = $1 ORDER BY paid DESC", user.id)
        if not instances:
            return await ctx.send_warning(f"{user.mention} doesn't have any instances")
        content = []
        for instance in instances:
            content.append(f"<@{instance['user_id']}> - {await self.bot.manage.guild_name(instance['guild_id'])} (<t:{instance['paid']}:R>)")
        return await ctx.paginate(content, f"Instances of {user.name}", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url})

    @instances.command(name="list", brief="bot manager")
    @is_manager()
    async def instances_list(self, ctx: EvelinaContext):
        """List all instances"""
        instances = await self.bot.db.fetch("SELECT * FROM instance ORDER BY paid DESC")
        if not instances:
            return await ctx.send_warning("No instances found")
        content = []
        for instance in instances:
            content.append(f"<@{instance['user_id']}> - <@{instance['owner_id']}> (<t:{instance['paid']}:R>)")
        return await ctx.paginate(content, f"Instances", {"name":  ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @group(name="authorized", aliases=["auth"], brief="bot manager", invoke_without_command=True, case_insensitive=True)
    @is_manager()
    async def authorized(self, ctx: EvelinaContext):
        """Manage authorized users"""
        return await ctx.create_pages()
    
    @authorized.command(name="add", brief="bot manager", usage="authorized add comminate /evelina")
    @is_manager()
    async def authorized_add(self, ctx: EvelinaContext, user: User, server: Union[Invite, int]):
        """Add a user to the authorized list"""
        if isinstance(server, Invite):
            server = server.guild.id
        await self.bot.db.execute("INSERT INTO authorized VALUES ($1, $2, $3)", user.id, server, int(datetime.datetime.now().timestamp()))
        return await ctx.send_success(f"User **{user.mention}** has been successfully added to the authorized list for {await self.bot.manage.guild_name(server, True)}")
    
    @authorized.command(name="remove", brief="bot manager", usage="authorized remove comminate /evelina")
    @is_manager()
    async def authorized_remove(self, ctx: EvelinaContext, user: User, server: Union[Invite, int]):
        """Remove a user from the authorized list"""
        if isinstance(server, Invite):
            server = server.guild.id
        await self.bot.db.execute("DELETE FROM authorized WHERE owner_id = $1 AND guild_id = $2", user.id, server)
        return await ctx.send_success(f"User **{user.mention}** has been successfully removed from the authorized list for {await self.bot.manage.guild_name(server, True)}")
    
    @authorized.command(name="list", brief="bot manager")
    @is_manager()
    async def authorized_list(self, ctx: EvelinaContext):
        """List all authorized servers"""
        results = await self.bot.db.fetch("SELECT * FROM authorized")
        if not results:
            return await ctx.send_warning("There are no authorized servers")
        return await ctx.paginate([f"{await self.bot.manage.guild_name(result['guild_id'], True)} - <@{result['owner_id']}>" for result in results], f"Authorized servers")

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Manager(bot))