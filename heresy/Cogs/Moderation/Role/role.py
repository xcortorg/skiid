import discord
from discord.ext import commands
import json
import os
import aiohttp

class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = os.path.join(os.path.dirname(__file__), "autorole_data.json")
        self.autorole_data = self.load_autorole_data()
        self.bot.session = aiohttp.ClientSession()

    def load_autorole_data(self):
        if os.path.exists("autorole_data.json"):
            with open("autorole_data.json", "r") as f:
                return json.load(f)
        return {}

    def save_autorole_data(self):
        with open("autorole_data.json", "w") as f:
            json.dump(self.autorole_data, f)

    @commands.group(name="r", invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def role_group(self, ctx, member: discord.Member = None, *, role_input: str = None):
        if member and role_input:
            await self.give_role(ctx, member, role_input)
        else:
            await ctx.send("Please provide a subcommand or a valid user and role (e.g., `,r @user role_name`).")

    async def give_role(self, ctx, member: discord.Member, role_input: str):
        guild = ctx.guild
        role = None

        if role_input.startswith('<@&') and role_input.endswith('>'):
            role_id = int(role_input[3:-1])
            role = guild.get_role(role_id)
        elif role_input.isdigit():
            role = guild.get_role(int(role_input))
        else:
            role = discord.utils.find(lambda r: r.name.lower().startswith(role_input.lower()), guild.roles)

        if role:
            if role in member.roles:
                await member.remove_roles(role)
                await self.send_embed(ctx, f"Removed {role.mention} from {member.mention}.")
            else:
                await member.add_roles(role)
                await self.send_embed(ctx, f"Gave {role.mention} to {member.mention}.")
        else:
            await ctx.send(f"Role '{role_input}' not found.")

    async def send_embed(self, ctx, message: str):
        embed = discord.Embed(description=message, color=0xADD8E6)
        await ctx.send(embed=embed)

    @role_group.command(name="human", aliases= ["humans"])
    @commands.has_permissions(manage_roles=True)
    async def role_human(self, ctx, role: discord.Role):
        count = len([member for member in ctx.guild.members if not member.bot])
        await self.send_embed(ctx, f"Adding {role.mention} to {count} human members, this may take a moment...")

        for member in ctx.guild.members:
            if not member.bot:
                await member.add_roles(role)

        await self.send_embed(ctx, f"Role {role.mention} has been given to {count} human members.")

    @role_group.command(name="bot", aliases= ["bots"])
    @commands.has_permissions(manage_roles=True)
    async def role_bot(self, ctx, role: discord.Role):
        count = len([member for member in ctx.guild.members if member.bot])
        await self.send_embed(ctx, f"Adding {role.mention} to {count} bot members, this may take a moment...")

        for member in ctx.guild.members:
            if member.bot:
                await member.add_roles(role)

        await self.send_embed(ctx, f"Role {role.mention} has been given to {count} bot members.")

    @role_group.command(name="has")
    @commands.has_permissions(manage_roles=True)
    async def role_has(self, ctx, role: discord.Role, action: str, new_role: discord.Role):
        if action.lower() not in ["give", "remove"]:
            await ctx.send("Invalid action. Use `give` or `remove`.")
            return

        count = len([member for member in ctx.guild.members if role in member.roles])
        await self.send_embed(ctx, f"{'Giving' if action == 'give' else 'Removing'} {new_role.mention} to/from {count} members, this may take a moment...")

        for member in ctx.guild.members:
            if role in member.roles:
                if action.lower() == "give":
                    await member.add_roles(new_role)
                elif action.lower() == "remove":
                    await member.remove_roles(new_role)

        await self.send_embed(ctx, f"Role {new_role.mention} has been {'given' if action == 'give' else 'removed'} to/from {count} members.")

    @role_group.command(name="create")
    @commands.has_permissions(manage_roles=True)
    async def role_create(self, ctx, *, role_name: str):
        guild = ctx.guild
        await guild.create_role(name=role_name)
        await self.send_embed(ctx, f"Role {role_name} created successfully.")

    @role_group.command(name="delete")
    @commands.has_permissions(manage_roles=True)
    async def role_delete(self, ctx, role: discord.Role):
        await role.delete()
        await self.send_embed(ctx, f"Role {role.mention} has been deleted.")

    @role_group.command(name="give")
    @commands.has_permissions(manage_roles=True)
    async def role_give(self, ctx, member: discord.Member, *, role_input: str):
        await self.give_role(ctx, member, role_input)

    @role_group.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, member: discord.Member, *, role_input: str):
        guild = ctx.guild
        role = None
        if role_input.startswith('<@&') and role_input.endswith('>'):
            role_id = int(role_input[3:-1])
            role = guild.get_role(role_id)
        elif role_input.isdigit():
            role = guild.get_role(int(role_input))
        else:
            role = discord.utils.find(lambda r: r.name.lower().startswith(role_input.lower()), guild.roles)

        if role:
            await member.remove_roles(role)
            await self.send_embed(ctx, f"Role {role.mention} has been removed from {member.mention}.")
        else:
            await ctx.send(f"Role '{role_input}' not found.")

    @role_group.command(name="rename")
    @commands.has_permissions(manage_roles=True)
    async def role_rename(self, ctx, role: discord.Role, new_name: str):
        await role.edit(name=new_name)
        await self.send_embed(ctx, f"Role {role.mention} has been renamed to '{new_name}'.")

    @role_group.command(name="icon")
    @commands.has_permissions(manage_roles=True)
    async def role_icon(self, ctx, role: discord.Role, emoji: discord.Emoji = None):
        if emoji is None:
            await ctx.send("Please provide a custom emoji.")
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(emoji.url)) as response:
                    if response.status != 200:
                        await ctx.send("Failed to fetch the emoji image. Please check the emoji.")
                        return

                    image_bytes = await response.read()
                    await role.edit(icon=image_bytes)
                    await ctx.send(f"Role {role.mention}'s icon has been updated using the emoji {emoji}.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @role_group.command(name="hoist")
    @commands.has_permissions(manage_roles=True)
    async def role_hoist(self, ctx, role: discord.Role, hoist: str = None):
        """
        Toggles or sets the hoist status of a role.

        Parameters:
        - role: The role to edit.
        - hoist: True/False to set the hoist explicitly, or omit to toggle.
        """
        if hoist is not None:
            if hoist.lower() in ("true", "yes", "on"):
                hoist_value = True
            elif hoist.lower() in ("false", "no", "off"):
                hoist_value = False
            else:
                await ctx.send("Please specify `true` or `false` for the hoist argument.")
                return
        else:
            hoist_value = not role.hoist  # Toggle the current hoist value

        try:
            await role.edit(hoist=hoist_value, reason=f"Hoist changed by {ctx.author}")
            state = "now displayed" if hoist_value else "no longer displayed"
            await ctx.send(f"Role {role.mention} is {state} separately.")
            await ctx.message.add_reaction("👍")
        except discord.Forbidden:
            await ctx.send("I don't have permission to edit this role.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred while updating the role: {str(e)}")

    @role_group.command(name="color")
    @commands.has_permissions(manage_roles=True)
    async def role_color(self, ctx, role: discord.Role, color_hex: str):
        try:
            color = discord.Color(int(color_hex.lstrip("#"), 16))
            await role.edit(color=color)
            await self.send_embed(ctx, f"Role {role.mention}'s color has been changed to {color_hex}.")
        except ValueError:
            await ctx.send("Invalid color hex code. Please provide a valid hex color (e.g., #00ff00).")

    @commands.command(name="autorole")
    @commands.has_permissions(manage_roles=True)
    async def autorole(self, ctx, role: discord.Role):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.autorole_data:
            self.autorole_data[guild_id] = {"humans": None, "bots": None}

        self.autorole_data[guild_id]["humans"] = role.id
        self.save_autorole_data()
        await self.send_embed(ctx, f"Autorole for new human members has been set to {role.mention}.")

    @commands.command(name="autorolebots")
    @commands.has_permissions(manage_roles=True)
    async def autorole_bots(self, ctx, role: discord.Role):
        """Automatically assigns a role to new bot members for this server."""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.autorole_data:
            self.autorole_data[guild_id] = {"humans": None, "bots": None}

        self.autorole_data[guild_id]["bots"] = role.id
        self.save_autorole_data()
        await self.send_embed(ctx, f"Autorole for new bot members set to {role.mention} for this server.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = str(member.guild.id)
        if guild_id in self.autorole_data:
            role_id = self.autorole_data[guild_id]["bots" if member.bot else "humans"]
            if role_id:
                role = member.guild.get_role(role_id)
                if role:
                    await member.add_roles(role)
                    print(f"Assigned role {role.name} to {'bot' if member.bot else 'human'} {member.name}.")

    async def send_embed(self, ctx, message: str):
        embed = discord.Embed(description=message, color=0xADD8E6)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Role(bot))
