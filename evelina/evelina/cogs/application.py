import json
import random

from typing import Union
from datetime import datetime

from discord import Embed, TextChannel, Interaction, SelectOption, Role
from discord.ui import Select, View, Modal, TextInput
from discord.ext.commands import Cog, group, command, has_guild_permissions

from modules.styles import emojis, colors
from modules.evelinabot import EvelinaContext, Evelina
from modules.persistent.application import ApplicationModerationView

class Application(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(name="application", aliases=["app"], invoke_without_command=True)
    async def application(self, ctx: EvelinaContext) -> None:
        """Manage your applications"""
        return await ctx.create_pages()
    
    @application.command(name="create", aliases=["add"], brief="manage guild", usage="application create Moderator")
    @has_guild_permissions(manage_guild=True)
    async def application_create(self, ctx: EvelinaContext, name: str) -> None:
        """Create a new application"""
        applications = await self.bot.db.fetch("SELECT * FROM applications WHERE guild_id = $1", ctx.guild.id)
        if len(applications) >= 25:
            return await ctx.send_warning("You can only have **25 applications** per server.")
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if check:
            return await ctx.send_warning("Application with that name already exists.")
        await self.bot.db.execute("INSERT INTO applications (guild_id, name, questions, status) VALUES ($1, $2, $3, $4)", ctx.guild.id, name, [], True)
        return await ctx.send_success(f"Application `{name}` has been created.\nYou can now add questions to it using `{ctx.prefix}application question add`.")

    @application.command(name="delete", aliases=["remove"], brief="manage guild", usage="application delete Moderator")
    @has_guild_permissions(manage_guild=True)
    async def application_delete(self, ctx: EvelinaContext, name: str) -> None:
        """Delete an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        await self.bot.db.execute("DELETE FROM applications WHERE name = $1", name)
        return await ctx.send_success(f"Application `{name}` has been deleted.")

    @application.command(name="list", aliases=["all"], brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def application_list(self, ctx: EvelinaContext) -> None:
        """List all applications"""
        applications = await self.bot.db.fetch("SELECT * FROM applications WHERE guild_id = $1", ctx.guild.id)
        if not applications:
            return await ctx.send_warning("No applications found.")
        embeds = []
        for application in applications:
            embed = Embed(color=colors.NEUTRAL, title=application["name"])
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            embed.add_field(name="Status", value="Open" if application["status"] else "Closed", inline=True)
            for index, question in enumerate(application["questions"]):
                embed.add_field(name=f"Question {index + 1}", value=f"```{question}```", inline=False)
            embed.set_footer(text=f"Page: {applications.index(application) + 1}/{len(applications)} ({applications.index(application) + 1} entries)")
            embeds.append(embed)
        return await ctx.paginator(embeds)
    
    @application.group(name="question", aliases=["questions"], brief="manage guild", invoke_without_command=True)
    @has_guild_permissions(manage_guild=True)
    async def application_question(self, ctx: EvelinaContext) -> None:
        """Manage questions"""
        return await ctx.create_pages()
    
    @application_question.command(name="add", brief="manage guild", usage="application question add Moderator What is your age?")
    async def application_question_add(self, ctx: EvelinaContext, name: str, *, question: str) -> None:
        """Add a question to an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        if len(check["questions"]) >= 5:
            return await ctx.send_warning("You can only have **5 questions** per application.")
        if len(question) > 45:
            return await ctx.send_warning("Question can not be longer than **100 characters")
        questions = check["questions"]
        questions.append(question)
        await self.bot.db.execute("UPDATE applications SET questions = $1 WHERE name = $2 AND guild_id = $3", questions, name, ctx.guild.id)
        return await ctx.send_success(f"Question has been added to application `{name}`\n```{question}```")
    
    @application_question.command(name="remove", brief="manage guild", usage="application question remove Moderator 1")
    async def application_question_remove(self, ctx: EvelinaContext, name: str, question: int) -> None:
        """Remove a question from an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        questions = check["questions"]
        if question > len(questions):
            return await ctx.send_warning("Question with that index does not exist.")
        questions.pop(question - 1)
        await self.bot.db.execute("UPDATE applications SET questions = $1 WHERE name = $2 AND guild_id = $3", questions, name, ctx.guild.id)
        return await ctx.send_success(f"Question has been removed from application `{name}`")
    
    @application_question.command(name="edit", brief="manage guild", usage="application question edit Moderator 1 What is your age?")
    async def application_question_edit(self, ctx: EvelinaContext, name: str, question: int, *, new_question: str) -> None:
        """Edit a question in an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        questions = check["questions"]
        if question > len(questions):
            return await ctx.send_warning("Question with that index does not exist.")
        if len(new_question) > 45:
            return await ctx.send_warning("Question can not be longer than **100 characters")
        questions[question - 1] = new_question
        await self.bot.db.execute("UPDATE applications SET questions = $1 WHERE name = $2 AND guild_id = $3", questions, name, ctx.guild.id)
        return await ctx.send_success(f"Question has been edited in application `{name}`\n```{new_question}```")
    
    @application_question.command(name="list", brief="manage guild", usage="application question list Moderator")
    async def application_question_list(self, ctx: EvelinaContext, name: str) -> None:
        """List all questions in an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        questions = check["questions"]
        if not questions:
            return await ctx.send_warning("No questions found.")
        embed = Embed(color=colors.NEUTRAL, title=name)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        for index, question in enumerate(questions):
            embed.add_field(name=f"Question {index + 1}", value=f"```{question}```", inline=False)
        embed.set_footer(text=f"Page: 1/1 ({len(questions)} entries)")
        return await ctx.send(embed=embed)
    
    @application.group(name="role", aliases=["roles"], brief="manage guild", invoke_without_command=True)
    @has_guild_permissions(manage_guild=True)
    async def application_role(self, ctx: EvelinaContext) -> None:
        """Manage application roles"""
        return await ctx.create_pages()

    @application_role.command(name="add", brief="manage guild", usage="application role add Moderator @Moderator")
    @has_guild_permissions(manage_guild=True)
    async def application_role_add(self, ctx: EvelinaContext, name: str, role: Role) -> None:
        """Add a role to an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        roles = json.loads(check.get("roles", "[]"))
        if str(role.id) in roles:
            return await ctx.send_warning("Role is already added to this application.")
        roles.append(str(role.id))
        await self.bot.db.execute("UPDATE applications SET roles = $1 WHERE name = $2 AND guild_id = $3", json.dumps(roles), name, ctx.guild.id)
        return await ctx.send_success(f"Role {role.mention} has been added to application `{name}`")
    
    @application_role.command(name="remove", brief="manage guild", usage="application role remove Moderator @Moderator")
    @has_guild_permissions(manage_guild=True)
    async def application_role_remove(self, ctx: EvelinaContext, name: str, role: Role) -> None:
        """Remove a role from an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        roles = json.loads(check.get("roles", "[]"))
        if str(role.id) not in roles:
            return await ctx.send_warning("Role is not added to this application.")
        roles.remove(str(role.id))
        await self.bot.db.execute("UPDATE applications SET roles = $1 WHERE name = $2 AND guild_id = $3", json.dumps(roles), name, ctx.guild.id)
        return await ctx.send_success(f"Role {role.mention} has been removed from application `{name}`")

    @application_role.command(name="list", brief="manage guild", usage="application role list Moderator")
    @has_guild_permissions(manage_guild=True)
    async def application_role_list(self, ctx: EvelinaContext, name: str) -> None:
        """List all roles in an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        roles = json.loads(check.get("roles", "[]"))
        if not roles:
            return await ctx.send_warning("No roles found.")
        role_mentions = [self.bot.misc.humanize_role(ctx.guild, int(role_id)) for role_id in roles]
        await ctx.paginate(role_mentions, f"Roles for `{name}`", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @application.command(name="status", brief="manage guild", usage="application status Moderator open")
    @has_guild_permissions(manage_guild=True)
    async def application_status(self, ctx: EvelinaContext, name: str, status: str) -> None:
        """Change the status of an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        if status.lower() == "open":
            status = True
        elif status.lower() == "closed":
            status = False
        else:
            return await ctx.send_warning("Invalid status. Use `open` or `closed`.")
        await self.bot.db.execute("UPDATE applications SET status = $1 WHERE name = $2 AND guild_id = $3", status, name, ctx.guild.id)
        return await ctx.send_success(f"Application `{name}` is now {status}")
    
    @application.command(name="channel", brief="manage guild", usage="application channel Moderator #applications")
    @has_guild_permissions(manage_guild=True)
    async def application_channel(self, ctx: EvelinaContext, name: str, channel: TextChannel) -> None:
        """Set the channel for an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        await self.bot.db.execute("UPDATE applications SET channel_id = $1 WHERE name = $2 AND guild_id = $3", channel.id, name, ctx.guild.id)
        return await ctx.send_success(f"Application `{name}` channel has been set to {channel.mention}")
    
    @application.command(name="level", brief="manage guild", usage="application level Moderator 5")
    @has_guild_permissions(manage_guild=True)
    async def application_level(self, ctx: EvelinaContext, name: str, level: int) -> None:
        """Set the level for an application"""
        check = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", name, ctx.guild.id)
        if not check:
            return await ctx.send_warning("Application with that name does not exist.")
        await self.bot.db.execute("UPDATE applications SET level = $1 WHERE name = $2 AND guild_id = $3", level, name, ctx.guild.id)
        return await ctx.send_success(f"Application `{name}` level has been set to {level}")

    @command(name="apply")
    async def apply(self, ctx: EvelinaContext) -> None:
        """Apply for an open application"""
        applications = await self.bot.db.fetch("SELECT name, questions, channel_id, level FROM applications WHERE guild_id = $1 AND status = $2", ctx.guild.id, True)
        if not applications:
            return await ctx.send_warning("No open applications found.")
        options = [
            SelectOption(label=app["name"], value=str(index))
            for index, app in enumerate(applications[:25])
        ]
        select = Select(placeholder="Choose an application", options=options)
        async def select_callback(interaction: Interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            selected_index = int(interaction.data["values"][0])
            application = applications[selected_index]
            class ApplicationModal(Modal):
                def __init__(self):
                    super().__init__(title=f"Application: {application['name']}")
                    for index, question in enumerate(application["questions"]):
                        self.add_item(
                            TextInput(
                                label=question,
                                required=True,
                                max_length=1000
                            )
                        )
                async def on_submit(self, interaction: Interaction):
                    responses = {item.label: item.value for item in self.children}
                    id = random.randint(100000, 999999)
                    await interaction.client.db.execute("INSERT INTO application_responses (guild_id, user_id, application_name, responses, id) VALUES ($1, $2, $3, $4, $5)", ctx.guild.id, ctx.author.id, application["name"], json.dumps(responses), id)
                    channel_id = application.get("channel_id")
                    if not channel_id:
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: No channel set for this application.")
                        return await interaction.response.edit_message(embed=embed, view=None)
                    channel = interaction.client.get_channel(channel_id)
                    if not channel:
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: The designated channel does not exist.")
                        return await interaction.response.edit_message(embed=embed, view=None)
                    user_level = await interaction.client.db.fetchrow("SELECT * FROM level_user WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
                    if not user_level:
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You do not meet the requirements to apply for this application.\n> You need to be level {application.get('level', 0)}.")
                        return await interaction.response.edit_message(embed=embed, view=None)
                    if user_level["level"] < application.get("level", 0):
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You do not meet the requirements to apply for this application.\n> You need to be level {application.get('level', 0)}.")
                        return await interaction.response.edit_message(embed=embed, view=None)
                    embed = Embed(title=f"📩 New Application: {application['name']}", color=colors.NEUTRAL)
                    embed.add_field(name="User", value=ctx.author.mention, inline=True)
                    embed.add_field(name="Created", value=f"<t:{int(datetime.now().timestamp())}:f>")
                    embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url)
                    for question, answer in responses.items():
                        embed.add_field(name=question, value=f"```{answer}```", inline=False)
                    message = await channel.send(embed=embed, view=ApplicationModerationView(interaction.client))
                    await interaction.client.db.execute("UPDATE application_responses SET id = $1 WHERE id = $2", message.id, id)
                    embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Your application for `{application['name']}` has been submitted.")
                    return await interaction.response.edit_message(embed=embed, view=None)
            await interaction.response.send_modal(ApplicationModal())
        select.callback = select_callback
        view = View(timeout=60)
        view.add_item(select)
        embed = Embed(color=colors.NEUTRAL, description=f"📋 {ctx.author.mention}: Select an application to apply for:")
        await ctx.send(embed=embed, view=view, ephemeral=True)

async def setup(bot: Evelina) -> None:
	return await bot.add_cog(Application(bot))