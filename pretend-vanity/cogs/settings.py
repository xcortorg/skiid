import os

import discord
import psycopg2
from discord import Embed
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB"),
            user=os.getenv("DBUSER"),
            password=os.getenv("PASSW"),
            host=os.getenv("HOST"),
            port=os.getenv("PORT"),
        )

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Hello!")

    @commands.group()
    @commands.has_permissions(manage_guild=True)
    async def set(self, ctx):
        """
        Group command for setting guild options.
        """
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                description="```vanity, channel, role, vanitylock, notifications```",
                color=0x729BB0,
            )
            await ctx.reply(embed=embed)

    @set.command()
    @commands.has_permissions(manage_guild=True)
    async def keeprole(self, ctx, bool_value: bool):
        """
        Sets the keep role option for the guild.
        """
        guild = ctx.guild
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM servers WHERE guild_id = %s", (guild.id,))
            result = cursor.fetchone()

            if result:
                cursor.execute(
                    "UPDATE servers SET keeprole = %s WHERE guild_id = %s",
                    (bool_value, guild.id),
                )
                self.conn.commit()
                message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Keep role **option updated*** to `{bool_value}`."
            else:
                cursor.execute(
                    "INSERT INTO servers (guild_id, keeprole) VALUES (%s, %s)",
                    (guild.id, bool_value),
                )
                self.conn.commit()
                message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Keep **role option** set to `{bool_value}`."

            embed = discord.Embed(description=message, color=0xA5EB78)
            await ctx.reply(embed=embed)
        finally:
            cursor.close()

    @set.command()
    @commands.has_permissions(manage_guild=True)
    async def vanity(self, ctx, vanity: str):
        """
        Sets the vanity for the guild.
        """
        guild = ctx.guild
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM servers WHERE guild_id = %s", (guild.id,))
            result = cursor.fetchone()

            if result:
                cursor.execute(
                    "UPDATE servers SET vanity = %s WHERE guild_id = %s",
                    (vanity, guild.id),
                )
                self.conn.commit()
                message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Vanity **updated** to `{vanity}`."
            else:
                cursor.execute(
                    "INSERT INTO servers (guild_id, vanity) VALUES (%s, %s)",
                    (guild.id, vanity),
                )
                self.conn.commit()
                message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Set **vanity substring** to  `{vanity}`."

            embed = discord.Embed(description=message, color=0xA5EB78)
            await ctx.reply(embed=embed)
        finally:
            cursor.close()

    @set.command()
    @commands.has_permissions(manage_guild=True)
    async def notifications(self, ctx, bool_value: bool):
        """
        Toggles the notifications for the guild.
        """
        guild = ctx.guild
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM servers WHERE guild_id = %s", (guild.id,))
            result = cursor.fetchone()

            if result:
                cursor.execute(
                    "UPDATE servers SET notif = %s WHERE guild_id = %s",
                    (bool_value, guild.id),
                )
                self.conn.commit()
                message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Notifications **updated** to `{bool_value}`."
            else:
                cursor.execute(
                    "INSERT INTO servers (guild_id, notif) VALUES (%s, %s)",
                    (guild.id, bool_value),
                )
                self.conn.commit()
                message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Notifications **set** to `{bool_value}`."

            embed = discord.Embed(description=message, color=0xA5EB78)
            await ctx.reply(embed=embed)
        finally:
            cursor.close()

    @set.command()
    @commands.has_permissions(manage_guild=True)
    async def vanitylock(self, ctx, bool_value: bool):
        """
        Sets the vanity lock for the guild.
        """
        guild = ctx.guild
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM servers WHERE guild_id = %s", (guild.id,))
            result = cursor.fetchone()

            if result:
                cursor.execute(
                    "UPDATE servers SET vanitylock = %s WHERE guild_id = %s",
                    (bool_value, guild.id),
                )
                self.conn.commit()
                message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Vanity lock **updated** to `{bool_value}`."
            else:
                cursor.execute(
                    "INSERT INTO servers (guild_id, vanitylock) VALUES (%s, %s)",
                    (guild.id, bool_value),
                )
                self.conn.commit()
                message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Vanity lock **set** to `{bool_value}`."

            embed = discord.Embed(description=message, color=0xA5EB78)
            await ctx.reply(embed=embed)
        finally:
            cursor.close()

    @set.command()
    @commands.has_permissions(manage_guild=True)
    async def channel(self, ctx, notif_channel: discord.TextChannel):
        """
        Sets the notification channel for the guild.
        """
        guild = ctx.guild

        if notif_channel:
            if (
                ctx.guild.me.guild_permissions.manage_roles
                and notif_channel.permissions_for(guild.me).send_messages
                and notif_channel.permissions_for(guild.me).embed_links
            ):
                cursor = self.conn.cursor()
                try:
                    cursor.execute(
                        "SELECT * FROM servers WHERE guild_id = %s", (guild.id,)
                    )
                    result = cursor.fetchone()

                    if result:
                        cursor.execute(
                            "UPDATE servers SET notif_channel = %s WHERE guild_id = %s",
                            (notif_channel.id, guild.id),
                        )
                        self.conn.commit()
                        message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Notification **channel set** to {notif_channel.mention}."
                    else:
                        cursor.execute(
                            "INSERT INTO servers (guild_id, notif_channel) VALUES (%s, %s)",
                            (guild.id, notif_channel.id),
                        )
                        self.conn.commit()
                        message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Notification **channel set** to {notif_channel.mention}."

                    embed = discord.Embed(description=message, color=0xA5EB78)
                    await ctx.reply(embed=embed)
                finally:
                    cursor.close()
            else:
                embed = discord.Embed(
                    description="<:deny:1251929424777969797> <@{ctx.author.id}>: I don't have permission to **manage roles** or **send messages** in the notification **channel**.",
                    color=0xEB3434,
                )
                await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                description="<:deny:1251929424777969797> <@{ctx.author.id}>:The specified notification channel does not exist.",
                color=0xEB3434,
            )
            await ctx.reply(embed=embed)

    @set.command()
    @commands.has_permissions(manage_guild=True)
    async def role(self, ctx, role: discord.Role):
        """
        Sets the role to be assigned for the guild.
        """
        guild = ctx.guild

        if role:
            if ctx.guild.me.guild_permissions.manage_roles:
                cursor = self.conn.cursor()
                try:
                    cursor.execute(
                        "SELECT * FROM servers WHERE guild_id = %s", (guild.id,)
                    )
                    result = cursor.fetchone()

                    if result:
                        cursor.execute(
                            "UPDATE servers SET role_id = %s WHERE guild_id = %s",
                            (role.id, guild.id),
                        )
                        self.conn.commit()
                        message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Role **updated** to {role.mention}."
                    else:
                        cursor.execute(
                            "INSERT INTO servers (guild_id, role_id) VALUES (%s, %s)",
                            (guild.id, role.id),
                        )
                        self.conn.commit()
                        message = f"<:approve:1266758547128062005> <@{ctx.author.id}>: Set {role.mention} as an **award role**."

                    cursor.execute(
                        "SELECT vanity FROM servers WHERE guild_id = %s", (guild.id,)
                    )
                    result = cursor.fetchone()

                    if result:
                        vanity = (
                            result[0] or ""
                        )  # Default to empty string if vanity is None

                        for member in guild.members:
                            current_status = (
                                member.activity.name if member.activity else "None"
                            )
                            has_vanity = (
                                vanity.lower() in current_status.lower()
                                if current_status
                                else False
                            )

                            if has_vanity and role not in member.roles:
                                await member.add_roles(
                                    role, reason=f"{member.name} has vanity in status"
                                )
                            elif not has_vanity and role in member.roles:
                                await member.remove_roles(
                                    role,
                                    reason=f"{member.name} no longer has vanity in status",
                                )

                    embed = discord.Embed(description=message, color=0xA5EB78)
                    await ctx.reply(embed=embed)
                finally:
                    cursor.close()
            else:
                embed = discord.Embed(
                    description="<:deny:1251929424777969797> <@{ctx.author.id}>: I don't have permission to manage roles.",
                    color=0xEB3434,
                )
                await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                description="<:deny:1251929424777969797> <@{ctx.author.id}>: The specified role does not exist.",
                color=0xEB3434,
            )
            await ctx.reply(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def settings(self, ctx):
        """
        Displays the current settings for the guild.
        """
        guild = ctx.guild
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE guild_id = %s", (guild.id,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            vanity, role_id, notif_channel_id, keeprole = (
                result[1],
                result[2],
                result[3],
                result[4],
            )
            role = guild.get_role(role_id)
            notif_channel = guild.get_channel(notif_channel_id)
            embed = Embed(title="Settings", color=0x729BB0)
            embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar)
            embed.set_thumbnail(url=guild.icon)
            embed.set_footer(text=f"{guild.name}", icon_url=guild.icon)
            embed.add_field(name="Vanity", value=f"```{vanity}```", inline=False)
            embed.add_field(
                name="Role", value=f"<@&{role.id}>" if role else "None", inline=True
            )
            embed.add_field(
                name="Notification Channel",
                value=f"<#{notif_channel.id}>" if notif_channel else "None",
                inline=True,
            )
            embed.add_field(name="Keep role", value=keeprole, inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No settings found for this guild.")


async def setup(bot):
    await bot.add_cog(settings(bot))
