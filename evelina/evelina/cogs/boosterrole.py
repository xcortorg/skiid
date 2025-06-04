import io
import json
import aiohttp
import asyncio

from io import BytesIO
from PIL import Image
from typing import Union

from discord import Interaction, Embed, Role, PartialEmoji, Member, User, Emoji
from discord.ext.commands import Cog, group, has_guild_permissions
from discord.errors import NotFound, Forbidden, HTTPException

from modules.styles import emojis, colors
from modules.misc.views import ShareRoleView
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.converters import HexColor, NewRoleConverter
from modules.predicates import br_is_configured, has_br_role, boosted_to, boosterrole_blacklisted

from modules.misc.session import Session

async def get_emoji_image(emoji):
    if isinstance(emoji, PartialEmoji) or isinstance(emoji, Emoji):
        url = emoji.url
        response = await Session().get_bytes(url)
        if response:
            image = Image.open(BytesIO(response)).convert("RGBA")
            return image
    return None

class Boosterrole(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Boosterole commands"

    async def get_banned_words(self, guild_id):
        banned_words_json = await self.bot.db.fetchval("SELECT banned_words FROM booster_module WHERE guild_id = $1", guild_id)
        if banned_words_json:
            return json.loads(banned_words_json)
        return []

    async def save_banned_words(self, guild_id, banned_words):
        banned_words_json = json.dumps(banned_words)
        await self.bot.db.execute("UPDATE booster_module SET banned_words = $1 WHERE guild_id = $2", banned_words_json, guild_id)

    def contains_banned_words(self, banned_words, text):
        text_lower = text.lower()
        return any(banned_word in text_lower for banned_word in banned_words)

    @group(invoke_without_command=True, aliases=["br"], case_insensitive=True)
    async def boosterrole(self, ctx: EvelinaContext):
        """Boosterrole Commands"""
        return await ctx.create_pages()

    @boosterrole.group(name="blacklist", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def br_blacklist(self, ctx: EvelinaContext):
        """Manage the blacklist for boosterrole names/users"""
        return await ctx.create_pages()

    @boosterrole.group(name="unblacklist", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def br_unblacklist(self, ctx: EvelinaContext):
        """Manage the unblacklist for boosterrole names/users"""
        return await ctx.create_pages()

    @boosterrole.group(name="blacklisted", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def br_blacklisted(self, ctx: EvelinaContext):
        """List all blacklisted words for boosterrole names/users"""
        return await ctx.create_pages()

    @br_blacklist.command(name="word", brief="manage guild", usage="boosterrole blacklist word nig*a")
    @has_guild_permissions(manage_guild=True)
    async def br_blacklist_word(self, ctx: EvelinaContext, *, words: str):
        """Blacklist a word that can no longer be used as a Boosterrole name"""
        word_list = [word.strip().lower() for word in words.split(',')]
        banned_words = await self.get_banned_words(ctx.guild.id)
        new_banned_words = []
        for word in word_list:
            if word in banned_words:
                await ctx.send_warning(f"Word `{word}` is already banned.")
            else:
                banned_words.append(word)
                new_banned_words.append(word)
        if new_banned_words:
            await self.save_banned_words(ctx.guild.id, banned_words)
            new_banned_words_str = ', '.join(new_banned_words)
            await ctx.send_success(f"Following words have been added:\n> **{new_banned_words_str}**")
        else:
            await ctx.send_warning("No new words were added to the banned words list.")

    @br_unblacklist.command(name="word", brief="manage guild", usage="boosterrole unblacklist word nig*a")
    @has_guild_permissions(manage_guild=True)
    async def br_unblacklist_word(self, ctx: EvelinaContext, *, words: str):
        """Unblacklist a word to allow it as a boosterrole name again"""
        word_list = [word.strip().lower() for word in words.split(',')]
        banned_words = await self.get_banned_words(ctx.guild.id)
        removed_words = []
        for word in word_list:
            if word in banned_words:
                banned_words.remove(word)
                removed_words.append(word)
            else:
                await ctx.send_warning(f"Word `{word}` is not banned.")
        if removed_words:
            await self.save_banned_words(ctx.guild.id, banned_words)
            removed_words_str = ', '.join(removed_words)
            await ctx.send_success(f"Following words have been removed:\n> **{removed_words_str}**")
        else:
            await ctx.send_warning("No words were removed from the banned words list.")

    @br_blacklisted.command(name="word", brief="manage guild")
    @has_guild_permissions(administrator=True)
    async def br_blacklisted_word(self, ctx: EvelinaContext):
        """Shows all blacklisted words for boosterrole names"""
        banned_words = await self.get_banned_words(ctx.guild.id)
        if not banned_words:
            return await ctx.send("There are no banned words.")
        banned_words_list = [f"**{word}**" for index, word in enumerate(banned_words)]
        await ctx.paginate(banned_words_list, f"Blacklisted words", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @br_blacklist.command(name="user", brief="Manage guild", usage="boosterrole blacklist user comminate Spamming")
    @has_guild_permissions(manage_guild=True)
    async def br_blacklist_user(self, ctx: EvelinaContext, user: User, *, reason: str):
        """Blacklist a member from using boosterroles"""
        if user.id in self.bot.owner_ids:
            return await ctx.send_warning("Don't blacklist a bot owner, are you sure?")
        try:
            await self.bot.db.execute("INSERT INTO booster_blacklist (guild_id, user_id, reason) VALUES ($1, $2, $3)", ctx.guild.id, user.id, reason)
            await ctx.send_success(f"Blacklisted {user.mention} from using boosterroles for reason: **{reason}**")
        except Exception:
            await ctx.send_warning(f"User {user.mention} is **already** blacklisted from using boosterroles")
        
    @br_unblacklist.command(name="user", brief="Manage guild", usage="boosterrole unblacklist user comminate")
    @has_guild_permissions(manage_guild=True)
    async def br_unblacklist_user(self, ctx: EvelinaContext, user: User):
        """Unblacklist a member from using boosterroles"""
        if user.id in self.bot.owner_ids:
            return await ctx.send_warning("Don't unblacklist a bot owner, are you sure?")
        try:
            result = await self.bot.db.fetchval("SELECT COUNT(*) FROM booster_blacklist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
            if result == 0:
                return await ctx.send_warning(f"{user.mention} isn't blacklisted from using boosterroles")
            await self.bot.db.execute("DELETE FROM booster_blacklist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
            await ctx.send_success(f"Unblacklisted {user.mention} from using boosterroles")
        except Exception:
            await ctx.send_warning(f"User {user.mention} is **not** blacklisted from using boosterroles")
        
    @br_blacklisted.command(name="user", brief="Manage guild")
    @has_guild_permissions(manage_guild=True)
    async def br_blacklisted_user(self, ctx: EvelinaContext):
        """List all blacklisted users from using boosterroles"""
        results = await self.bot.db.fetch("SELECT user_id, reason FROM booster_blacklist WHERE guild_id = $1", ctx.guild.id)
        to_show = [f"**{self.bot.get_user(check['user_id'])}** (`{check['user_id']}`)\n{emojis.REPLY} **Reason:** {check['reason']}" for check in results]
        if to_show:
            await ctx.paginate(to_show, f"Boosterrole Blacklisted", {"name": ctx.author, "icon_url": ctx.author.avatar.url})
        else:
            await ctx.send_warning("No boosterrole blacklisted user found")

    @boosterrole.command(name="setup", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def br_setup(self, ctx: EvelinaContext):
        """Enable Boosterrole system in your server"""
        if await self.bot.db.fetchrow("SELECT * FROM booster_module WHERE guild_id = $1", ctx.guild.id):
            return await ctx.send_warning("Booster role is **already** configured")
        await self.bot.db.execute("INSERT INTO booster_module (guild_id) VALUES ($1)", ctx.guild.id)
        return await ctx.send_success("Configured booster role module")

    @boosterrole.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @br_is_configured()
    async def br_reset(self, ctx: EvelinaContext):
        """Disable Boosterrole system in your server"""
        async def yes_callback(interaction: Interaction):
            await self.bot.db.execute("DELETE FROM booster_module WHERE guild_id = $1", ctx.guild.id)
            await self.bot.db.execute("DELETE FROM booster_roles WHERE guild_id = $1", ctx.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {ctx.author.mention}: Booster role module cleared"), view=None)
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {ctx.author.mention}: Booster role deactivation got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to unset the boosterrole module? This action is **IRREVERSIBLE**", yes_callback, no_callback)

    @boosterrole.command(name="wipe", brief="manage guild", usage="boosterrole wipe comminate")
    @has_guild_permissions(manage_guild=True)
    @br_is_configured()
    async def br_wipe(self, ctx: EvelinaContext, user: Member):
        """Wipe a member's booster role"""
        role = ctx.guild.get_role(await self.bot.db.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id))
        if role:
            await role.delete(reason="Booster role wiped")
        await self.bot.db.execute("DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
        return await ctx.send_success(f"Wiped {user.mention}'s booster role")

    @boosterrole.group(name="award", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def br_award(self, ctx: EvelinaContext):
        """Give additional roles to members when they boost the server"""
        return await ctx.create_pages()

    @br_award.command(name="add", brief="manage guild", usage="boosterrole award add gang")
    @has_guild_permissions(manage_guild=True)
    async def br_award_add(self, ctx: EvelinaContext, *, role: NewRoleConverter):
        """Reward a member a specific role upon boost"""
        if await self.bot.db.fetchrow("SELECT * FROM booster_award WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id):
            return await ctx.send_warning("This role is **already** a booster role award")
        await self.bot.db.execute("INSERT INTO booster_award VALUES ($1,$2)", ctx.guild.id, role.id)
        return await ctx.send_success(f"Added {role.mention} as a booster role award")

    @br_award.command(name="remove", brief="manage guild", usage="boosterrole award remove gang")
    @has_guild_permissions(manage_guild=True)
    async def br_award_remove(self, ctx: EvelinaContext, *, role: Union[Role, int]):
        """Remove the reward role"""
        role_id = self.bot.misc.convert_role(role)
        if not await self.bot.db.fetchrow("SELECT * FROM booster_award WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id):
            return await ctx.send_warning("This role is **not** a booster role award")
        await self.bot.db.execute("DELETE FROM booster_award WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        return await ctx.send_success(f"Removed {self.bot.misc.humanize_role(ctx.guild, role_id)} from the booster role awards")

    @br_award.command(name="list")
    async def br_award_list(self, ctx: EvelinaContext):
        """Returns all the booster role awards in this server"""
        if results := await self.bot.db.fetch("SELECT role_id FROM booster_award WHERE guild_id = $1", ctx.guild.id):
            return await ctx.paginate(list(map(lambda result: f"{self.bot.misc.humanize_role(ctx.guild, result['role_id'])}", results)), f"Booster awards", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        return await ctx.send_warning("No booster role awards in this server")
    
    @boosterrole.group(name="allow", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def br_allow(self, ctx: EvelinaContext):
        """Allow roles to create booster roles"""
        return await ctx.create_pages()
    
    @br_allow.command(name="add", brief="manage guild", usage="boosterrole allow add gang")
    @has_guild_permissions(manage_guild=True)
    async def br_allow_add(self, ctx: EvelinaContext, *, role: NewRoleConverter):
        """Allow a role to create booster roles"""
        check = await self.bot.db.fetchrow("SELECT * FROM booster_allow WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if check:
            return await ctx.send_warning("This role is **already** allowed to create booster roles")
        await self.bot.db.execute("INSERT INTO booster_allow VALUES ($1,$2)", ctx.guild.id, role.id)
        return await ctx.send_success(f"Added {role.mention} as a role that can create booster roles")
    
    @br_allow.command(name="remove", brief="manage guild", usage="boosterrole allow remove gang")
    @has_guild_permissions(manage_guild=True)
    async def br_allow_remove(self, ctx: EvelinaContext, *, role: Union[Role, int]):
        """Remove a role from creating booster roles"""
        role_id = self.bot.misc.convert_role(role)
        check = await self.bot.db.fetchrow("SELECT * FROM booster_allow WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        if not check:
            return await ctx.send_warning("This role is **not** allowed to create booster roles")
        await self.bot.db.execute("DELETE FROM booster_allow WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        return await ctx.send_success(f"Removed {self.bot.misc.humanize_role(ctx.guild, role_id)} from the roles that can create booster roles")
    
    @br_allow.command(name="list")
    async def br_allow_list(self, ctx: EvelinaContext):
        """List all roles that can create booster roles"""
        if results := await self.bot.db.fetch("SELECT role_id FROM booster_allow WHERE guild_id = $1", ctx.guild.id):
            return await ctx.paginate(list(map(lambda result: f"{self.bot.misc.humanize_role(ctx.guild, result['role_id'])}", results)), f"Roles that can create booster roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        return await ctx.send_warning("No roles are allowed to create booster roles in this server")

    @boosterrole.group(name="share", invoke_without_command=True, case_insensitive=True)
    async def br_share(self, ctx: EvelinaContext):
        """Share your booster role with others"""
        return await ctx.create_pages()
    
    @br_share.command(name="enable", brief="manage guild")
    @br_is_configured()
    @has_guild_permissions(manage_guild=True)
    async def br_share_enable(self, ctx: EvelinaContext):
        """Enable sharing your booster role"""
        check = await self.bot.db.fetchrow("SELECT share_enabled FROM booster_module WHERE guild_id = $1", ctx.guild.id)
        if check and check['share_enabled']:
            return await ctx.send_warning("Booster role sharing is **already** enabled")
        await self.bot.db.execute("UPDATE booster_module SET share_enabled = $1 WHERE guild_id = $2", True, ctx.guild.id)
        return await ctx.send_success(f"Booster role sharing is now enabled\n> Use `{ctx.clean_prefix}boosterrole share limit` to set a limit")

    @br_share.command(name="disable", brief="manage guild")
    @br_is_configured()
    @has_guild_permissions(manage_guild=True)
    async def br_share_disable(self, ctx: EvelinaContext):
        """Disable sharing your booster role"""
        check = await self.bot.db.fetchrow("SELECT share_enabled FROM booster_module WHERE guild_id = $1", ctx.guild.id)
        if check and not check['share_enabled']:
            return await ctx.send_warning("Booster role sharing is **already** disabled")
        await self.bot.db.execute("UPDATE booster_module SET share_enabled = $1 WHERE guild_id = $2", False, ctx.guild.id)
        return await ctx.send_success("Booster role sharing is now disabled")
    
    @br_share.command(name="limit", brief="manage guild", usage="boosterrole share limit 5")
    @br_is_configured()
    @has_guild_permissions(manage_guild=True)
    async def br_share_limit(self, ctx: EvelinaContext, limit: int):
        """Limit the amount of people who can share your booster role"""
        check = await self.bot.db.fetchrow("SELECT share_enabled FROM booster_module WHERE guild_id = $1", ctx.guild.id)
        if check and not check['share_enabled']:
            return await ctx.send_warning(f"Booster role sharing is **disabled**\n> Use `{ctx.clean_prefix}boosterrole share enable` to enable it")
        await self.bot.db.execute("UPDATE booster_module SET share_limit = $1 WHERE guild_id = $2", limit, ctx.guild.id)
        return await ctx.send_success(f"Booster role sharing limit set to **{limit}**")
    
    @br_share.command(name="add", brief="server booster", usage="boosterrole share add comminate")
    @br_is_configured()
    @has_br_role()
    @boosterrole_blacklisted()
    async def br_share_add(self, ctx: EvelinaContext, user: Member):
        """Add a member to share your booster role"""
        if user.id == ctx.author.id:
            return await ctx.send_warning("You can't share your booster role with yourself")
        if user.bot:
            return await ctx.send_warning("You can't share your booster role with a bot")
        data = await self.bot.db.fetchrow(
            "SELECT share_enabled, share_limit FROM booster_module WHERE guild_id = $1",
            ctx.guild.id
        )
        if not data or not data['share_enabled']:
            return await ctx.send_warning(f"Booster role sharing is **disabled**\n> Use `{ctx.clean_prefix}boosterrole share enable` to enable it.")
        role_data = await self.bot.db.fetchrow(
            "SELECT role_id, shared_users FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id, ctx.author.id
        )
        shared_users = role_data['shared_users']
        if isinstance(shared_users, str):
            shared_users = json.loads(shared_users)
        limit = data['share_limit']
        role_id = role_data['role_id']
        if user.id in shared_users:
            return await ctx.send_warning(f"You are already sharing your booster role with {user.mention}")
        if len(shared_users) >= limit:
            return await ctx.send_warning(f"You can only share your role with **{limit}** users")
        embed = Embed(color=0xf47fff, description=f"🚀 {ctx.author.mention} wants to share their booster role with you. Do you accept?")
        view = ShareRoleView(ctx, user)
        view.message = await ctx.reply(content=user.mention, embed=embed, view=view)

    @br_share.command(name="remove", brief="server booster", usage="boosterrole share remove comminate")
    @br_is_configured()
    @has_br_role()
    @boosterrole_blacklisted()
    async def br_share_remove(self, ctx: EvelinaContext, user: Member):
        """Remove a member from sharing your booster role"""
        if user.id == ctx.author.id:
            return await ctx.send_warning("You can't share your booster role with yourself")
        if user.bot:
            return await ctx.send_warning("You can't share your booster role with a bot")
        role_data = await self.bot.db.fetchrow(
            "SELECT role_id, shared_users FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id, ctx.author.id
        )
        shared_users = role_data['shared_users']
        if isinstance(shared_users, str):
            shared_users = json.loads(shared_users)
        role_id = role_data['role_id']
        if user.id not in shared_users:
            return await ctx.send_warning(f"You are not sharing your booster role with {user.mention}")
        shared_users.remove(user.id)
        await self.bot.db.execute(
            "UPDATE booster_roles SET shared_users = $1 WHERE guild_id = $2 AND user_id = $3",
            json.dumps(shared_users), ctx.guild.id, ctx.author.id
        )
        booster_role = ctx.guild.get_role(role_id)
        try:
            await user.remove_roles(booster_role)
        except Forbidden:
            return await ctx.send_warning("I don't have permission to remove the booster role from this user")
        except NotFound:
            return await ctx.send_warning("I couldn't find the booster role")
        return await ctx.send_success(f"You are no longer sharing your booster role with {user.mention}")
    
    @br_share.command(name="list", brief="server booster")
    @br_is_configured()
    @has_br_role()
    @boosterrole_blacklisted()
    async def br_share_list(self, ctx: EvelinaContext):
        """List all members you are sharing your booster role with"""
        role_data = await self.bot.db.fetchrow(
            "SELECT role_id, shared_users FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id, ctx.author.id
        )
        shared_users = role_data['shared_users']
        if not shared_users:
            return await ctx.send_warning("You are not sharing your booster role with anyone")
        if isinstance(shared_users, str):
            shared_users = json.loads(shared_users)
        shared_users_list = []
        for user_id in shared_users:
            user = ctx.guild.get_member(user_id)
            if user:
                shared_users_list.append(f"{user.mention} (`{user.id}`)")
            else:
                shared_users_list.append(f"<@{user_id}> (`{user_id}`)")
        if shared_users_list:
            return await ctx.paginate(shared_users_list, "Shared users", {"name": ctx.author.display_name, "icon_url": ctx.author.avatar.url})
        else:
            return await ctx.send_warning("You are not sharing your booster role with anyone")

    @boosterrole.command(name="base", brief="manage guild", usage="boosterrole base ---------")
    @has_guild_permissions(manage_guild=True)
    @br_is_configured()
    async def br_base(self, ctx: EvelinaContext, *, role: Role = None):
        """Set the base role for where boost roles will go under"""
        check = await self.bot.db.fetchrow("SELECT base FROM booster_module WHERE guild_id = $1", ctx.guild.id)
        if role is None:
            if check is None:
                return await ctx.send_warning("Booster role module **base role** isn't set")
            await self.bot.db.execute("UPDATE booster_module SET base = $1 WHERE guild_id = $2", None, ctx.guild.id)
            return await ctx.send_success("Removed base role")

        await self.bot.db.execute("UPDATE booster_module SET base = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        return await ctx.send_success(f"Set {role.mention} as base role")
    
    @boosterrole.command(name="limit", brief="manage guild", usage="boosterrole limit 5")
    @has_guild_permissions(manage_guild=True)
    @br_is_configured()
    async def br_limit(self, ctx: EvelinaContext, limit: int):
        """Set the limit of booster roles that can be created"""
        check = await self.bot.db.fetchrow('SELECT "limit" FROM booster_module WHERE guild_id = $1', ctx.guild.id)
        if check and check['limit'] == limit:
            return await ctx.send_warning(f"Booster role limit is **already** set to **{limit}**")
        await self.bot.db.execute('UPDATE booster_module SET "limit" = $1 WHERE guild_id = $2', limit, ctx.guild.id)
        return await ctx.send_success(f"Set booster role limit to **{limit}**")

    @boosterrole.command(name="create", brief="server booster", usage="boosterrole create #3498DB boss")
    @br_is_configured()
    @boosterrole_blacklisted()
    async def br_create(self, ctx: EvelinaContext, color: HexColor, *, name: str = None):
        """Create a booster role"""
        if not ctx.author.premium_since:
            results = await self.bot.db.fetch("SELECT * FROM booster_allow WHERE guild_id = $1", ctx.guild.id)
            if not any(result['role_id'] in [role.id for role in ctx.author.roles] for result in results):
                if results:
                    return await ctx.send_warning("You need to **boost** or have any of these roles: " + ', '.join([f"<@&{result['role_id']}>" for result in results]))
                return await ctx.send_warning("You need to **boost** the server to create a booster role")
        limit = await self.bot.db.fetchval('SELECT "limit" FROM booster_module WHERE guild_id = $1', ctx.guild.id)
        if limit and limit > 0:
            results = await self.bot.db.fetch("SELECT * FROM booster_roles WHERE guild_id = $1", ctx.guild.id)
            if len(results) >= limit:
                return await ctx.send_warning(f"Booster role limit reached, you can only have **{limit}** booster roles")
        if name:
            if len(name) > 100:
                return await("Boosterrole name has to be fewer then 100 characters")
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send_warning("I don't have permission to manage roles.")
        if len(ctx.guild.roles) >= 250:
            return await ctx.send_warning("You can't create more roles in this server, please delete some roles")
        async with ctx.typing():
            check = await self.bot.db.fetchval("SELECT base FROM booster_module WHERE guild_id = $1", ctx.guild.id)
            if not name:
                name = f"{ctx.author.name}'s role"
            existing_role = await self.bot.db.fetchrow("SELECT * FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
            if existing_role:
                return await ctx.send_warning(f"You already have <@&{existing_role['role_id']}> as booster role")
            base = ctx.guild.get_role(check)
            role = await ctx.guild.create_role(name=name, color=color.value, reason="Booster role created")
            await asyncio.sleep(1)
            if base:
                try:
                    await role.move(below=base)
                except (Forbidden, NotFound, HTTPException):
                    return await ctx.send_warning("I don't have permission to edit the role position.")
            else:
                user_highest_role = max(ctx.author.roles, key=lambda r: r.position)
                bot_highest_role = max(ctx.guild.me.roles, key=lambda r: r.position)
                try:
                    await role.move(above=user_highest_role)
                except (Forbidden, NotFound, HTTPException):
                    try:
                        await role.move(above=bot_highest_role)
                    except (Forbidden, NotFound, HTTPException):
                        return await ctx.send_warning("I don't have permission to edit the role position.")
            try:
                await ctx.author.add_roles(role)
            except (Forbidden, NotFound, HTTPException):
                return await ctx.send_warning("I don't have permission to give you the role.")
            await self.bot.db.execute("INSERT INTO booster_roles (guild_id, user_id, role_id) VALUES ($1, $2, $3)", ctx.guild.id, ctx.author.id, role.id)
            return await ctx.send_success(f"Booster role {role.mention} created successfully!")

    @boosterrole.command(name="name", brief="server booster", usage="boosterrole name boss")
    @has_br_role()
    @boosterrole_blacklisted()
    async def br_name(self, ctx: EvelinaContext, *, name: str):
        """Edit your booster roles name"""
        try:
            if len(name) > 32:
                return await ctx.send_warning("The booster role name can't have more than **32** characters")
            banned_words = await self.get_banned_words(ctx.guild.id)
            if self.contains_banned_words(banned_words, name):
                return await ctx.send_warning("This role name contains a prohibited word. Please choose a different name.")
            role = ctx.guild.get_role(await self.bot.db.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id))
            if not role:
                return await ctx.send_warning(f"Your booster role was deleted\n> Please use `{ctx.clean_prefix}br delete` then `{ctx.clean_prefix}br create`")
            await role.edit(name=name, reason="Edited booster role name")
            await ctx.send_success(f"Edited the booster role name to **{name}**")
        except NotFound:
            return await ctx.send_warning("I couldn't find your booster role")
        except Forbidden:
            return await ctx.send_warning("I don't have permission to edit your booster role")

    @boosterrole.command(name="color", brief="server booster", usage="boosterrole color #3498DB")
    @has_br_role()
    @boosterrole_blacklisted()
    async def br_color(self, ctx: EvelinaContext, *, color: HexColor):
        """Edit your booster roles color"""
        try:
            role = ctx.guild.get_role(await self.bot.db.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id))
            if not role:
                return await ctx.send_warning(f"Your booster role was deleted\n> Please use `{ctx.clean_prefix}br delete` then `{ctx.clean_prefix}br create`")
            await role.edit(color=color.value, reason="Edited booster role color")
            await ctx.send(embed=Embed(color=color.value, description=f"{ctx.author.mention}: Edited the role's color to `{color.hex}`"))
        except NotFound:
            return await ctx.send_warning("I couldn't find your booster role")
        except Forbidden:
            return await ctx.send_warning("I don't have permission to edit your booster role")

    @boosterrole.command(name="icon", brief="server booster", usage="boosterrole icon :love:")
    @has_br_role()
    @boosted_to(2)
    @boosterrole_blacklisted()
    async def br_icon(self, ctx: EvelinaContext, *, icon: Union[PartialEmoji, str]):
        """Edit your booster roles icon"""
        try:
            role = ctx.guild.get_role(await self.bot.db.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id))
            if not role:
                return await ctx.send_warning(f"Your booster role was deleted\n> Please use `{ctx.clean_prefix}br delete` then `{ctx.clean_prefix}br create`")
            if icon == 'none':
                await role.edit(display_icon=None, reason="Edited the booster role icon")
                return await ctx.send_success("Booster role icon successfully removed")
            image = None
            if isinstance(icon, (PartialEmoji, Emoji)):
                image = await get_emoji_image(icon)
            elif icon.startswith('http'):
                async with aiohttp.ClientSession() as session:
                    async with session.get(icon) as response:
                        if response.status == 200:
                            image = Image.open(BytesIO(await response.read())).convert("RGBA")
            elif isinstance(icon, str) and icon.startswith('http'):
                async with aiohttp.ClientSession() as session:
                    async with session.get(icon) as response:
                        if response.status == 200:
                            image = Image.open(BytesIO(await response.read())).convert("RGBA")
            elif isinstance(icon, str):
                try:
                    image = Image.open(BytesIO(await ctx.bot.get_emoji_image(icon))).convert("RGBA")
                except:
                    return await ctx.send_warning("Invalid emoji or URL provided.")
            elif ctx.message.attachments:
                attachment = ctx.message.attachments[0]
                if attachment.content_type.startswith('image'):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as response:
                            if response.status == 200:
                                image = Image.open(BytesIO(await response.read())).convert("RGBA")
            if image:
                with io.BytesIO() as buffer:
                    image.save(buffer, format="PNG")
                    buffer.seek(0)
                    display_icon = buffer.read()
                await role.edit(display_icon=display_icon, reason="Edited the booster role icon")
                return await ctx.send_success(f"Booster role icon successfully changed to **{icon}**")
            else:
                return await ctx.send_warning("Unable to retrieve or process the image.")
        except NotFound:
            return await ctx.send_warning("I couldn't find your booster role")
        except Forbidden:
            return await ctx.send_warning("I don't have permission to edit your booster role")

    @boosterrole.command(name="delete", brief="server booster")
    @has_br_role()
    @boosterrole_blacklisted()
    async def br_delete(self, ctx: EvelinaContext):
        """Delete your booster role"""
        role = ctx.guild.get_role(await self.bot.db.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id))
        if role:
            try:
                await role.delete(reason="Booster role deleted")
            except NotFound:
                pass
            except Forbidden:
                return await ctx.send_warning("I don't have permission to delete the booster role")
        await self.bot.db.execute("DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
        return await ctx.send_success("Booster role deleted")

    @boosterrole.command(name="list")
    async def br_list(self, ctx: EvelinaContext):
        """View all booster roles"""
        results = await self.bot.db.fetch("SELECT * FROM booster_roles WHERE guild_id = $1", ctx.guild.id)
        if len(results) == 0:
            return await ctx.send_warning("No **booster roles** found in this server")
        return await ctx.paginate([f"<@&{result['role_id']}> owned by <@!{result['user_id']}>" for result in results], f"Booster Roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Boosterrole(bot))