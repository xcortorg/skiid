from discord import Member, User, Forbidden, Interaction, Embed
from discord.ext.commands import Cog, group, has_permissions

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import whitelist_enabled

class Whitelist(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Whitelst commands"

    @group(name="whitelist", aliases=["wl"], invoke_without_command=True, brief="administrator", case_insensitive=True)
    @has_permissions(administrator=True)
    async def whitelist(self, ctx: EvelinaContext):
        """Manage the whitelist module"""
        return await ctx.create_pages()

    @whitelist.command(name="enable", brief="administrator", usage="whitelist enable")
    @has_permissions(administrator=True)
    async def whitelist_enable(self, ctx: EvelinaContext):
        """Turn on the whitelist system"""
        if await self.bot.db.fetchrow("SELECT * FROM whitelist_module WHERE guild_id = $1", ctx.guild.id):
            return await ctx.send_warning(f"The whitelist is **already** enabled")
        async def yes_callback(interaction: Interaction):
            await self.bot.db.execute("INSERT INTO whitelist_module VALUES ($1, $2)", ctx.guild.id, "default")
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Enabled the **whitelist**")
            return await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Whitelist activation got canceled")
            return await interaction.response.edit_message(embed=embed, view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **enable** the whitelist system?\n This will kick every user that joins your server if you don't whitelist them!", yes_callback, no_callback)

    @whitelist.command(name="disable", brief="administrator", usage="whitelist disable")
    @has_permissions(administrator=True)
    @whitelist_enabled()
    async def whitelist_disable(self, ctx: EvelinaContext):
        """Turn off the whitelist system"""
        await self.bot.db.execute("DELETE FROM whitelist_module WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success(f"Disabled the **whitelist**")

    @whitelist.command(name="message", aliases=["msg", "dm"], brief="administrator", usage="whitelist message {user.mention}, this server has a whitelist.")
    @has_permissions(administrator=True)
    @whitelist_enabled()
    async def whitelist_message(self, ctx: EvelinaContext, *, code: str):
        """Change the message sent to users when not in the whitelist"""
        if code.lower().strip() == "none":
            await self.bot.db.execute("UPDATE whitelist_module SET embed = $1 WHERE guild_id = $2", "none", ctx.guild.id)
            return await ctx.send_success(f"Removed your **whitelist** message users will no longer be notified")
        elif code.lower().strip() == "default":
            await self.bot.db.execute("UPDATE whitelist_module SET embed = $1 WHERE guild_id = $2", "default", ctx.guild.id)
            return await ctx.send_success(f"Set your **whitelist** message to the default")
        else:
            await self.bot.db.execute("UPDATE whitelist_module SET embed = $1 WHERE guild_id = $2", code, ctx.guild.id)
            return await ctx.send_success(f"Set your **custom** whitelist message")

    @whitelist.command(name="punishment", aliases=["punish"], brief="administrator", usage="whitelist punishment kick")
    @has_permissions(administrator=True)
    @whitelist_enabled()
    async def whitelist_punishment(self, ctx: EvelinaContext, punishment: str):
        """Change the punishment for not being whitelisted"""
        if punishment.lower() not in ["kick", "ban"]:
            return await ctx.send_warning(f"Punishment must be either `kick` or `ban`")
        await self.bot.db.execute("UPDATE whitelist_module SET punishment = $1 WHERE guild_id = $2", punishment.lower(), ctx.guild.id)
        return await ctx.send_success(f"Set your **whitelist** punishment to `{punishment}`")

    @whitelist.command(name="add", brief="administrator", usage="whitelist add comminate")
    @has_permissions(administrator=True)
    @whitelist_enabled()
    async def whitelist_add(self, ctx: EvelinaContext, user: User):
        """Add someone to the server whitelist"""
        if await self.bot.db.fetchrow("SELECT * FROM whitelist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id):
            return await ctx.send_warning(f"{user.mention} is already **whitelisted**")
        await self.bot.db.execute("INSERT INTO whitelist VALUES ($1, $2)", ctx.guild.id, user.id)
        await ctx.send_success(f"Added {user.mention} to the **whitelist**")

    @whitelist.command(name="remove", brief="administrator", usage="whitelist remove comminate")
    @has_permissions(administrator=True)
    @whitelist_enabled()
    async def whitelist_remove(self, ctx: EvelinaContext, user: Member | User):
        """Remove someone from the server whitelist"""
        if not await self.bot.db.fetchrow("SELECT * FROM whitelist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id):
            return await ctx.send_warning(f"{user.mention} is not **whitelisted**")
        await self.bot.db.execute("DELETE FROM whitelist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
        i = None
        if isinstance(user, Member):
            try:
                await ctx.guild.kick(user, reason=f"Removed from the whitelist by {ctx.author} ({ctx.author.id})")
                i = True
            except Forbidden:
                i = False
        return await ctx.send_success(f"Removed {user.mention} from the **whitelist**" if i is True else f"Removed {user.mention} from the **whitelist** - failed to kick the member")

    @whitelist.command(name="list", brief="administrator", usage="whitelist list")
    @has_permissions(administrator=True)
    @whitelist_enabled()
    async def whitelist_list(self, ctx: EvelinaContext):
        """View all whitelisted members"""
        results = await self.bot.db.fetch("SELECT * FROM whitelist WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"No users are **whitelisted**")
        content = []
        for result in results:
            user = self.bot.get_user(result['user_id'])
            if user:
                content.append(f"{user.mention} (`{user.id}`)")
            else:
                user = await self.bot.fetch_user(result['user_id'])
                if user:
                    content.append(f"{user.mention} (`{user.id}`)")
                else:
                    content.append(f"Unknown User (`{result['user_id']}`)")
        return await ctx.paginate(content, title=f"Whitelist Users", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina):
    await bot.add_cog(Whitelist(bot))