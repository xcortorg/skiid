import discord
from discord.ext import commands
import os

class Ad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Replace this with the exact path to your ad.txt file
        self.ad_path = r"C:\\Users\\fnafl\Downloads\\Heresy v2\\Cogs\\P4P\\ad.txt"

    def get_ad_message(self):
        """
        Reads the ad message from ad.txt.
        """
        try:
            with open(self.ad_path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            return f"Ad file not found at {self.ad_path}. Please ensure the file exists."
        except Exception as e:
            return f"Error reading ad file: {e}"

    @commands.command(name="ad")
    async def ad(self, ctx):
        """
        Sends the promotional message read from ad.txt.
        """
        ad_message = self.get_ad_message()
        await ctx.send(ad_message)


class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Replace this with the exact path to your ad.txt file
        self.ad_path = r"C:\\Users\\fnafl\Downloads\\Heresy v2\\Cogs\\P4P\\ad.txt"

    def get_ad_message(self):
        """
        Reads the ad message from ad.txt.
        """
        try:
            with open(self.ad_path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            return f"Ad file not found at {self.ad_path}. Please ensure the file exists."
        except Exception as e:
            return f"Error reading ad file: {e}"

    @commands.command(name="p4p-setup")
    @commands.has_permissions(administrator=True)
    async def p4p_setup(self, ctx):
        """
        Sets up the P4P category, channels, and role.
        """
        guild = ctx.guild

        # Create the category
        category_name = "US VS THEM"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        # Create the "us" channel
        us_channel = discord.utils.get(guild.text_channels, name="us")
        if not us_channel:
            us_channel = await category.create_text_channel("us")

        # Create the "them" channel
        them_channel = discord.utils.get(guild.text_channels, name="them")
        if not them_channel:
            them_channel = await category.create_text_channel("them")

        # Set permissions for the channels
        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = False  # Default for everyone
        overwrite.read_messages = True  # Visible but not writable

        await us_channel.set_permissions(guild.default_role, overwrite=overwrite)
        await them_channel.set_permissions(guild.default_role, overwrite=overwrite)

        # Create or get the "pm" role
        pm_role = discord.utils.get(guild.roles, name="pm")
        if not pm_role:
            pm_role = await guild.create_role(name="pm")

        # Allow "pm" role to send messages in both channels
        pm_overwrite = discord.PermissionOverwrite(send_messages=True, read_messages=True)
        await us_channel.set_permissions(pm_role, overwrite=pm_overwrite)
        await them_channel.set_permissions(pm_role, overwrite=pm_overwrite)

        # Post the ad in "us" channel
        ad_message = self.get_ad_message()
        await us_channel.send(ad_message)

        await ctx.send(f"P4P setup complete! Category `{category_name}` created.")


async def setup(bot):
    await bot.add_cog(Ad(bot))
    await bot.add_cog(Setup(bot))
