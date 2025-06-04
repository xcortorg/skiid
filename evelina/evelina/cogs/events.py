from discord import Embed, TextChannel, Message, Interaction, ButtonStyle
from discord.ui import View, button
from discord.ext.commands import Cog, group, has_guild_permissions, BadArgument

from typing import Union

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import query_limit
from modules.validators import ValidTime

class ServerView(View):
    def __init__(self, guild_name: str):
        super().__init__()
        self.guild_name = guild_name
        self.children[0].label = f"Sent from server: {self.guild_name}"

    @button(label="Sent from server:", style=ButtonStyle.gray, disabled=True)
    async def server_button(self, interaction, button):
        await interaction.response.send_message(f"Button pressed in server: {self.guild_name}")

class Events(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Event commands"

    async def test_message(self, ctx: EvelinaContext, channel: TextChannel) -> Message:
        table = ctx.command.qualified_name.split(" ")[0]
        check = await self.bot.db.fetchrow(f"SELECT * FROM {table} WHERE channel_id = $1", channel.id)
        if not check:
            raise BadArgument(f"There is no {table} message in this channel")
        perms = channel.permissions_for(channel.guild.me)
        if not perms.send_messages or not perms.embed_links:
            raise BadArgument(f"I don't have permissions to send the {table} message in {channel.mention}")
        x = await self.bot.embed_build.convert(ctx, check["message"])
        try:
            mes = await channel.send(**x)
            return await ctx.send_success(f"Sent the message {mes.jump_url}")
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while sending the message\n```{e}```")

    @group(invoke_without_command=True, aliases=["greet", "wlc", "welc"], case_insensitive=True)
    async def welcome(self, ctx: EvelinaContext):
        """Set up a welcome message in one or multiple channels"""
        return await ctx.create_pages()

    @welcome.command(name="add", brief="manage guild", usage="welcome add #general Hi, {user.mention}")
    @has_guild_permissions(manage_guild=True)
    @query_limit("welcome")
    async def welcome_add(self, ctx: EvelinaContext, channel: TextChannel, *, code: str):
        """Add a welcome message for a channel"""
        template = await self.bot.db.fetchval("SELECT embed FROM embeds_templates WHERE code = $1", code)
        if template:
            code = template
        check = await self.bot.db.fetchrow("SELECT * FROM welcome WHERE channel_id = $1", channel.id)
        if check:
            args = ["UPDATE welcome SET message = $1 WHERE channel_id = $2", code, channel.id]
        else:
            args = ["INSERT INTO welcome VALUES ($1,$2,$3)", ctx.guild.id, channel.id, code]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Added welcome message to {channel.mention}\n```{code}```")

    @welcome.command(name="joinping", brief="manage guild", usage="welcome joinping #general")
    @has_guild_permissions(manage_guild=True)
    @query_limit("welcome")
    async def welcome_joinping(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Add a join ping in a specific channel"""
        code = "{embed}$v{content: {user.mention}}$v{delete: 1}"
        check = await self.bot.db.fetchrow("SELECT * FROM welcome WHERE channel_id = $1", channel.id)
        if check:
            args = ["UPDATE welcome SET message = $1 WHERE channel_id = $2", code, channel.id]
        else:
            args = ["INSERT INTO welcome VALUES ($1,$2,$3)", ctx.guild.id, channel.id, code]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Added join ping message to {channel.mention}")

    @welcome.command(name="remove", brief="manage guild", usage="welcome remove #general")
    @has_guild_permissions(manage_guild=True)
    async def welcome_remove(self, ctx: EvelinaContext, *, channel: Union[TextChannel, int]):
        """Remove a welcome message from a channel"""
        channel_id = self.bot.misc.convert_channel(channel)
        check = await self.bot.db.fetchrow("SELECT * FROM welcome WHERE channel_id = $1", channel_id)
        if not check:
            return await ctx.send_warning("There is no welcome message configured in this channel")
        await self.bot.db.execute("DELETE FROM welcome WHERE channel_id = $1", channel_id)
        return await ctx.send_success(f"Deleted the welcome message from {self.bot.misc.humanize_channel(channel_id)}")

    @welcome.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def welcome_list(self, ctx: EvelinaContext):
        """View all welcome messages"""
        results = await self.bot.db.fetch("SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There is no welcome message configured in this server")
        embeds = [
            Embed(color=colors.NEUTRAL, title=f"Welcome Configuration")
            .set_footer(text=f"Page: {results.index(result)+1}/{len(results)} ({len(results)} entries)")
            .add_field(name=f"Channel", value=f"{self.bot.misc.humanize_channel(result['channel_id'])}", inline=True)
            .add_field(name=f"Message", value=f"```{result['message']}```", inline=False)
            for result in results
        ]
        await ctx.paginator(embeds)

    @welcome.group(name="delete", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def welcome_delete(self, ctx: EvelinaContext):
        """Delete a welcome message"""
        return await ctx.create_pages()
    
    @welcome_delete.command(name="enable", brief="manage guild", usage="welcome delete enable #welcome 5m")
    @has_guild_permissions(manage_guild=True)
    async def welcome_delete_enable(self, ctx: EvelinaContext, channel: TextChannel, time: ValidTime):
        """Enable the welcome message deletion"""
        check = await self.bot.db.fetchrow("SELECT * FROM welcome WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if not check:
            return await ctx.send_warning("There is no welcome message configured in this channel")
        await self.bot.db.execute("UPDATE welcome SET delete = $1, duration = $2 WHERE channel_id = $3", True, time, channel.id)
        return await ctx.send_success(f"Enabled the welcome message deletion in {channel.mention} after {time} when a user left")
    
    @welcome_delete.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def welcome_delete_disable(self, ctx: EvelinaContext, channel: TextChannel):
        """Disable the welcome message deletion"""
        check = await self.bot.db.fetchrow("SELECT * FROM welcome WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if not check:
            return await ctx.send_warning("There is no welcome message configured in this channel")
        await self.bot.db.execute("UPDATE welcome SET delete = $1, duration = $2 WHERE channel_id = $3", False, None, channel.id)
        return await ctx.send_success(f"Disabled the welcome message deletion in {channel.mention}")

    @welcome.command(name="test", brief="manage guild", usage="welcome test #general")
    @has_guild_permissions(manage_guild=True)
    async def welcome_test(self, ctx: EvelinaContext, *, channel: TextChannel):
        """View welcome message for a channel"""
        await self.test_message(ctx, channel)

    @welcome.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def welcome_reset(self, ctx: EvelinaContext):
        """Remove all the welcome messages"""
        check = await self.bot.db.fetch("SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id)
        if len(check) == 0:
            return await ctx.send_warning("You have **no** welcome messages in this server")
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM welcome WHERE guild_id = $1", interaction.guild.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Deleted all welcome messages in this server")
            await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.APPROVE} {interaction.user.mention}: Welcome messages deletion got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **RESET** all welcome messages in this server?", yes_callback, no_callback)

    @group(invoke_without_command=True, case_insensitive=True)
    async def leave(self, ctx: EvelinaContext):
        """Set up a goodbye message in one or multiple channels"""
        return await ctx.create_pages()

    @leave.command(name="add", brief="manage guild", usage="leave add #general Bye, {user.mention}")
    @has_guild_permissions(manage_guild=True)
    @query_limit("leave")
    async def leave_add(self, ctx: EvelinaContext, channel: TextChannel, *, code: str):
        """Add a goodbye message for a channel"""
        template = await self.bot.db.fetchval("SELECT embed FROM embeds_templates WHERE code = $1", code)
        if template:
            code = template
        check = await self.bot.db.fetchrow("SELECT * FROM leave WHERE channel_id = $1", channel.id)
        if check:
            args = ["UPDATE leave SET message = $1 WHERE channel_id = $2", code, channel.id]
        else:
            args = ["INSERT INTO leave VALUES ($1,$2,$3)", ctx.guild.id, channel.id, code]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Added leave message to {channel.mention}\n```{code}```")

    @leave.command(name="remove", brief="manage guild", usage="leave remove #general")
    @has_guild_permissions(manage_guild=True)
    async def leave_remove(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Remove a goodbye message from a channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM leave WHERE channel_id = $1", channel.id)
        if not check:
            return await ctx.send_warning("There is no leave message configured in this channel")
        await self.bot.db.execute("DELETE FROM leave WHERE channel_id = $1", channel.id)
        return await ctx.send_success(f"Deleted the leave message from {channel.mention}")

    @leave.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def leave_list(self, ctx: EvelinaContext):
        """View goodbye message for a channel"""
        results = await self.bot.db.fetch("SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There is no leave message configured in this server")
        embeds = [
            Embed(color=colors.NEUTRAL, title=f"Leave Configuration")
            .set_footer(text=f"Page: {results.index(result)+1}/{len(results)} ({len(results)} entries)")
            .add_field(name=f"Channel", value=f"{ctx.guild.get_channel(result['channel_id']).mention if ctx.guild.get_channel(result['channel_id']) else 'None'}", inline=True)
            .add_field(name=f"Message", value=f"```{result['message']}```", inline=False)
            for result in results
        ]
        await ctx.paginator(embeds)

    @leave.command(name="test", brief="manage guild", usage="leave test #general")
    @has_guild_permissions(manage_guild=True)
    async def leave_test(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Test the leave message in a channel"""
        await self.test_message(ctx, channel)

    @leave.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def leave_reset(self, ctx: EvelinaContext):
        """Remove all the leave messages"""
        check = await self.bot.db.fetch("SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id)
        if len(check) == 0:
            return await ctx.send_warning("You have **no** leave messages in this server")
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM leave WHERE guild_id = $1", interaction.guild.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Deleted all leave messages in this server")
            await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.APPROVE} {interaction.user.mention}: Leave messages deletion got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **RESET** all leave messages in this server?", yes_callback, no_callback)

    @group(invoke_without_command=True, case_insensitive=True)
    async def boost(self, ctx: EvelinaContext):
        """Set up a boost message in one or multiple channels"""
        return await ctx.create_pages()

    @boost.command(name="add", brief="manage guild", usage="boost add #general Thanks, {user.mention}")
    @has_guild_permissions(manage_guild=True)
    @query_limit("boost")
    async def boost_add(self, ctx: EvelinaContext, channel: TextChannel, *, code: str):
        """Add a boost message for a channel"""
        template = await self.bot.db.fetchval("SELECT embed FROM embeds_templates WHERE code = $1", code)
        if template:
            code = template
        check = await self.bot.db.fetchrow("SELECT * FROM boost WHERE channel_id = $1", channel.id)
        if check:
            args = ["UPDATE boost SET message = $1 WHERE channel_id = $2", code, channel.id]
        else:
            args = ["INSERT INTO boost VALUES ($1,$2,$3)", ctx.guild.id, channel.id, code]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Added boost message to {channel.mention}\n```{code}```")

    @boost.command(name="remove", brief="manage guild", usage="boost remove #general")
    @has_guild_permissions(manage_guild=True)
    async def boost_remove(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Remove a boost message from a channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM boost WHERE channel_id = $1", channel.id)
        if not check:
            return await ctx.send_warning("There is no boost message configured in this channel")
        await self.bot.db.execute("DELETE FROM boost WHERE channel_id = $1", channel.id)
        return await ctx.send_success(f"Deleted the boost message from {channel.mention}")

    @boost.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def boost_list(self, ctx: EvelinaContext):
        """View boost message for a channel"""
        results = await self.bot.db.fetch("SELECT * FROM boost WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There is no boost message configured in this server")
        embeds = [
            Embed(color=colors.NEUTRAL, title=f"Boost Configuration")
            .set_footer(text=f"Page: {results.index(result)+1}/{len(results)} ({len(results)} entries)")
            .add_field(name=f"Channel", value=f"{ctx.guild.get_channel(result['channel_id']).mention if ctx.guild.get_channel(result['channel_id']) else 'None'}", inline=True)
            .add_field(name=f"Message", value=f"{result['message']}", inline=False)
            for result in results
        ]
        await ctx.paginator(embeds)

    @boost.command(name="test", brief="manage guild", usage="boost test #general")
    @has_guild_permissions(manage_guild=True)
    async def boost_test(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Test the boost message in a channel"""
        await self.test_message(ctx, channel)

    @boost.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def boost_reset(self, ctx: EvelinaContext):
        """Remove all the boost messages"""
        check = await self.bot.db.fetch("SELECT * FROM boost WHERE guild_id = $1", ctx.guild.id)
        if len(check) == 0:
            return await ctx.send_warning("You have **no** boost messages in this server")
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM boost WHERE guild_id = $1", interaction.guild.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Deleted all boost messages in this server")
            await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.APPROVE} {interaction.user.mention}: Boost messages deletion got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **RESET** all boost messages in this server?", yes_callback, no_callback)
    
    @group(name="joindm", invoke_without_command=True, case_insensitive=True)
    async def joindm(self, ctx: EvelinaContext):
        """Set up a join DM message"""
        return await ctx.create_pages()
    
    @joindm.command(name="add", brief="manage guild", usage="joindm add Hi, {user.mention}")
    @has_guild_permissions(manage_guild=True)
    async def joindm_add(self, ctx: EvelinaContext, *, code: str):
        """Add a join DM message"""
        template = await self.bot.db.fetchval("SELECT embed FROM embeds_templates WHERE code = $1", code)
        if template:
            code = template
        check = await self.bot.db.fetchrow("SELECT * FROM joindm WHERE guild_id = $1", ctx.guild.id)
        if check:
            args = ["UPDATE joindm SET message = $1 WHERE guild_id = $2", code, ctx.guild.id]
        else:
            args = ["INSERT INTO joindm VALUES ($1,$2)", ctx.guild.id, code]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Added join DM message\n```{code}```")
    
    @joindm.command(name="remove", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def joindm_remove(self, ctx: EvelinaContext):
        """Remove the join DM message"""
        check = await self.bot.db.fetchrow("SELECT * FROM joindm WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There is no join DM message configured in this server")
        await self.bot.db.execute("DELETE FROM joindm WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Deleted the join DM message")
    
    @joindm.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def joindm_list(self, ctx: EvelinaContext):
        """View the join DM message"""
        check = await self.bot.db.fetchrow("SELECT * FROM joindm WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There is no join DM message configured in this server")
        embed = Embed(color=colors.NEUTRAL, title=f"Join DM Configuration")
        embed.description=f"```{check['message']}```"
        await ctx.send(embed=embed)
    
    @joindm.command(name="test", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def joindm_test(self, ctx: EvelinaContext):
        """Test the join DM message"""
        check = await self.bot.db.fetchrow("SELECT * FROM joindm WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There is no join DM message configured in this server")
        try:
            x = await self.bot.embed_build.convert(ctx, check["message"])
            view = ServerView(guild_name=ctx.guild.name)
            await ctx.author.send(**x)
            await ctx.author.send(view=view)
            return await ctx.send_success("Sent the message in your DMs")
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while sending the message\n```{e}```")
        
    @joindm.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def joindm_reset(self, ctx: EvelinaContext):
        """Remove the join DM message"""
        check = await self.bot.db.fetchrow("SELECT * FROM joindm WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There is no join DM message configured in this server")
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM joindm WHERE guild_id = $1", interaction.guild.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Deleted the join DM message in this server")
            await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.APPROVE} {interaction.user.mention}: Join DM message deletion got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **RESET** the join DM message in this server?", yes_callback, no_callback)
    
async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Events(bot))