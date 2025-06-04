import re
import json
import random
import datetime
import humanfriendly

from modules.styles import colors
from modules.evelinabot import Evelina as AB
from modules.predicates import max_gws
from modules.misc.functions import giveaway_end
from modules.helpers import EvelinaContext
from modules.validators import ValidMessage, ValidTime
from modules.persistent.giveaway import GiveawayView
from modules.converters import RoleConverter

from discord import Embed, Forbidden, NotFound, TextChannel, User
from discord.ext.commands import Cog, command, has_guild_permissions, group

class Giveaway(Cog):
    def __init__(self, bot: AB):
        self.bot = bot
        self.emoji = "🎉"
        self.description = "Giveaway commands"

    @command(brief="manage guild", usage="gcreate #giveaway 12h 1 Nitro")
    @has_guild_permissions(manage_guild=True)
    async def gcreate(self, ctx: EvelinaContext, channel: TextChannel, time: ValidTime, winners: int, *, prize: str):
        """Start a giveaway with your provided duration, winners and prize description"""
        return await ctx.invoke(self.bot.get_command("giveaway create"), channel=channel, time=time, winners=winners, prize=prize)

    @command()
    async def glist(self, ctx: EvelinaContext):
        """List every active giveaway in the server"""
        return await ctx.invoke(self.bot.get_command("giveaway list"))

    @command(brief="manage_server", usage="gend 1256932539411468380")
    @has_guild_permissions(manage_guild=True)
    async def gend(self, ctx: EvelinaContext, message: ValidMessage):
        """End an active giveaway early"""
        await ctx.invoke(self.bot.get_command("giveaway end"), message=message)

    @command(brief="manage guild", usage="greroll 1256932539411468380 1")
    @has_guild_permissions(manage_guild=True)
    async def greroll(self, ctx: EvelinaContext, message: ValidMessage, winners: int = 1):
        """Reroll a winner for the specified giveaway"""
        await ctx.invoke(self.bot.get_command("giveaway reroll"), message=message, winners=winners)

    @group(invoke_without_command=True, aliases=["gw"], case_insensitive=True)
    async def giveaway(self, ctx: EvelinaContext):
        """Manage giveaways in your server"""
        return await ctx.create_pages()

    @giveaway.command(name="end", brief="manage_server", usage="giveaway end 1256932539411468380")
    @has_guild_permissions(manage_guild=True)
    async def giveaway_end(self, ctx: EvelinaContext, message: ValidMessage):
        """End an active giveaway early"""
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("This message is not a giveaway or it ended if it was one")
        await giveaway_end(self.bot, check)
        return await ctx.send_success(f"Ended giveaway in {message.channel.mention}")
    
    @giveaway.command(name="delete", brief="manage server", usage="giveaway delete 1256932539411468380")
    @has_guild_permissions(manage_guild=True)
    async def giveaway_delete(self, ctx: EvelinaContext, message_id: int):
        """Delete a giveaway"""
        res = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE message_id = $1 AND guild_id = $2", message_id, ctx.guild.id)
        if not res:
            return await ctx.send_warning("This message is not a valid giveaway or doesn't exist")
        await self.bot.db.execute("DELETE FROM giveaway WHERE message_id = $1 AND guild_id = $2", message_id, ctx.guild.id)
        try:
            msg = await ctx.channel.fetch_message(message_id)
            await msg.delete()
        except (NotFound, Forbidden):
            pass
        await ctx.send_success("The giveaway has been deleted")


    @giveaway.command(name="reroll", brief="manage guild", usage="giveaway reroll 1256932539411468380 1")
    @has_guild_permissions(manage_guild=True)
    async def giveaway_reroll(self, ctx: EvelinaContext, message: ValidMessage, winners: int = 1):
        """Reroll a specified number of winners for the giveaway"""
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway_ended WHERE channel_id = $1 AND message_id = $2", message.channel.id, message.id)
        if not check:
            return await ctx.send_warning(f"This message is not a giveaway or it didn't end if it is one. Use `{ctx.clean_prefix}gend` to end the giveaway")
        members = json.loads(check["members"])
        if len(members) < winners:
            return await ctx.send_warning(f"Not enough participants to reroll {winners} winners. There are only {len(members)} participants.")
        new_winners = random.sample(members, winners)
        await ctx.reply(f"**New winners:** {', '.join([f'<@!{winner}>' for winner in new_winners])}")

    @giveaway.command(name="list")
    async def giveaway_list(self, ctx: EvelinaContext):
        """List every active giveaway in the server"""
        results = await self.bot.db.fetch("SELECT * FROM giveaway WHERE guild_id = $1", ctx.guild.id)
        if len(results) == 0:
            return await ctx.send_warning("There are no giveaways")
        return await ctx.paginate([f"[**{result['title']}**](https://discord.com/channels/{ctx.guild.id}/{result['channel_id']}/{result['message_id']}) ends <t:{int(result['finish'].timestamp())}:R>" for result in results], f"Giveaways in {ctx.guild.name}")

    @giveaway.command(name="create", brief="manage guild", usage="giveaway create #giveaway 12h 1 Nitro --bonus @booster", extras={"role": "Set a required role", "bonus": "Set a bonus entrie role", "messages": "Set a required messages count", "level": "Set a required level", "invites": "Set a required invites count", "ignore": "Set a required ignore role"})
    @has_guild_permissions(manage_guild=True)
    @max_gws()
    async def giveaway_create(self, ctx: EvelinaContext, channel: TextChannel, time: ValidTime, winners: int, *, prize: str):
        """Start a giveaway with your provided duration, winners and prize description"""
        flags = {
            "--role": None,
            "--bonus": None,
            "--messages": None,
            "--level": None,
            "--invites": None,
            "--ignore": None
        }

        for flag in flags.keys():
            match = re.search(rf"{re.escape(flag)}\s+(\S+)", prize)
            if match:
                flags[flag] = match.group(1)
                prize = re.sub(rf"{re.escape(flag)}\s+\S+", "", prize).strip()

        role = None
        bonus = None
        messages = None
        level = None
        invites = None
        ignore = None

        if flags["--role"]:
            try:
                role_obj = await RoleConverter().convert(ctx, flags["--role"])
                role = role_obj.id
            except Exception:
                return await ctx.send_warning("Invalid role provided.")

        if flags["--bonus"]:
            try:
                bonus_obj = await RoleConverter().convert(ctx, flags["--bonus"])
                bonus = bonus_obj.id
            except Exception:
                return await ctx.send_warning("Invalid bonus role provided.")

        if flags["--messages"]:
            try:
                messages = int(flags["--messages"])
            except ValueError:
                return await ctx.send_warning("Invalid messages value provided.")

        if flags["--level"]:
            try:
                level = int(flags["--level"])
            except ValueError:
                return await ctx.send_warning("Invalid level value provided.")
            
        if flags["--invites"]:
            try:
                invites = int(flags["--invites"])
            except ValueError:
                return await ctx.send_warning("Invalid invites value provided.")
            
        if flags["--ignore"]:
            try:
                ignore_obj = await RoleConverter().convert(ctx, flags["--ignore"])
                ignore = ignore_obj.id
            except Exception:
                return await ctx.send_warning("Invalid ignore role provided.")

        embed = Embed(color=colors.NEUTRAL, title=prize, description=f"**Ends:** <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=time)).timestamp())}> (<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=time)).timestamp())}:R>)\n**Hosted by:** {ctx.author.mention}\n**Winners:** {winners}")
        embed.add_field(name="Entries", value="0")

        if bonus:
            embed.add_field(name="Bonus", value=bonus_obj.mention)
        if role:
            embed.add_field(name="Role", value=role_obj.mention)
        if messages:
            embed.add_field(name="Messages", value=messages)
        if level:
            if await self.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", ctx.guild.id):
                embed.add_field(name="Level", value=level)
            else:
                return await ctx.send_warning(f"Leveling is not enabled in this server\n> Use `{ctx.clean_prefix}level enable` to enable it")
        if invites:
            if await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id):
                embed.add_field(name="Invites", value=invites)
            else:
                return await ctx.send_warning(f"Invites are not enabled in this server\n> Use `{ctx.clean_prefix}invites enable` to enable it")
        if ignore:
            embed.add_field(name="Ignore", value=ignore_obj.mention)

        view = GiveawayView(self.bot)
        await ctx.send_success(f"Giveaway setup completed! Check {channel.mention}")
        mes = await channel.send(embed=embed, view=view)

        await self.bot.db.execute(
            "INSERT INTO giveaway (guild_id, channel_id, message_id, winners, members, finish, host, title, required_role, required_bonus, required_messages, required_level, required_invites, required_ignore) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)",
            ctx.guild.id,
            channel.id,
            mes.id,
            winners,
            json.dumps([]),
            (datetime.datetime.now() + datetime.timedelta(seconds=time)),
            ctx.author.id,
            prize,
            role,
            bonus,
            messages,
            level,
            invites,
            ignore
        )

    @giveaway.group(name="edit", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def giveaway_edit(self, ctx: EvelinaContext):
        """Edit a giveaway's settings"""
        return await ctx.create_pages()
    
    @giveaway_edit.command(name="price", brief="manage guild", usage="giveaway edit price 1256932539411468380 Nitro Yearly")
    @has_guild_permissions(manage_guild=True)
    async def giveaway_edit_price(self, ctx: EvelinaContext, message: ValidMessage, *, price: str):
        """Edit the prize of a giveaway"""
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("This message is not a giveaway or it ended if it was one")
        embed = message.embeds[0]
        embed.title = price
        await message.edit(embed=embed)
        await self.bot.db.execute("UPDATE giveaway SET title = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4", price, ctx.guild.id, message.channel.id, message.id)
        return await ctx.send_success(f"Updated [`giveaway`]({message.jump_url}) prize to **{price}**")
    
    @giveaway_edit.command(name="duration", brief="manage guild", usage="giveaway edit duration 1256932539411468380 1d")
    @has_guild_permissions(manage_guild=True)
    async def giveaway_edit_duration(self, ctx: EvelinaContext, message: ValidMessage, *, duration: str):
        """Edit the duration of a giveaway"""
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("This message is not a giveaway or it ended if it was one")
        embed = message.embeds[0]
        try:
            seconds = humanfriendly.parse_timespan(duration)
        except humanfriendly.InvalidTimespan:
            return await ctx.send_warning("Invalid time parsed, please use 3d, 2h, 1m, 30s, etc.")
        embed.description = f"**Ends:** <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=seconds)).timestamp())}> (<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=seconds)).timestamp())}:R>)\n**Hosted by:** <@{check['host']}>\n**Winners:** {check['winners']}"
        await message.edit(embed=embed)
        await self.bot.db.execute("UPDATE giveaway SET finish = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4", (datetime.datetime.now() + datetime.timedelta(seconds=seconds)), ctx.guild.id, message.channel.id, message.id)
        return await ctx.send_success(f"Updated [`giveaway`]({message.jump_url}) duration to **{duration}**")
    
    @giveaway_edit.command(name="host", brief="manage guild", usage="giveaway edit host 1256932539411468380 comminate")
    @has_guild_permissions(manage_guild=True)
    async def giveaway_edit_host(self, ctx: EvelinaContext, message: ValidMessage, *, host: User):
        """Edit the host of a giveaway"""
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("This message is not a giveaway or it ended if it was one")
        embed = message.embeds[0]
        embed.description = f"**Ends:** <t:{int(check['finish'].timestamp())}> (<t:{int(check['finish'].timestamp())}:R>)\n**Hosted by:** {host.mention}\n**Winners:** {check['winners']}"
        await message.edit(embed=embed)
        await self.bot.db.execute("UPDATE giveaway SET host = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4", host.id, ctx.guild.id, message.channel.id, message.id)
        return await ctx.send_success(f"Updated [`giveaway`]({message.jump_url}) host to **{host}**")
    
    @giveaway_edit.command(name="winners", brief="manage guild", usage="giveaway edit winners 1256932539411468380 2")
    @has_guild_permissions(manage_guild=True)
    async def giveaway_edit_winners(self, ctx: EvelinaContext, message: ValidMessage, winners: int):
        """Edit the number of winners of a giveaway"""
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("This message is not a giveaway or it ended if it was one")
        embed = message.embeds[0]
        embed.description = f"**Ends:** <t:{int(check['finish'].timestamp())}> (<t:{int(check['finish'].timestamp())}:R>)\n**Hosted by:** <@{check['host']}>\n**Winners:** {winners}"
        await message.edit(embed=embed)
        await self.bot.db.execute("UPDATE giveaway SET winners = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4", winners, ctx.guild.id, message.channel.id, message.id)
        return await ctx.send_success(f"Updated [`giveaway`]({message.jump_url}) winners to **{winners}**")

    @giveaway.group(name="requirements", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def giveaway_requirements(self, ctx: EvelinaContext):
        """Manage a giveaway's requirements"""
        return await ctx.create_pages()
    
    @giveaway_requirements.command(name="add", brief="manage guild", usage="giveaway requirements add 1256932539411468380 role Admin")
    async def giveaway_requirements_add(self, ctx: EvelinaContext, message: ValidMessage, flag: str, *, input: str):
        """Add a new requirement to the giveaway"""
        valid_flags = ["role", "bonus", "messages", "level", "invites", "ignore"]
        if flag not in valid_flags:
            formatted_flags = ", ".join(f"`{f}`" for f in valid_flags[:-1]) + f" & `{valid_flags[-1]}`"
            return await ctx.send_warning(f"Invalid flag. Use one of: {formatted_flags}")
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("This message is not a giveaway or it ended if it was one")
        column = f"required_{flag}" if flag != "bonus" else "required_bonus"
        if check[column] is not None:
            return await ctx.send_warning(f"The {flag} requirement is already set")
        embed = message.embeds[0]
        if flag in ["role", "bonus", "ignore"]:
            try:
                role_obj = await RoleConverter().convert(ctx, input)
                role_id = role_obj.id
                await self.bot.db.execute(f"UPDATE giveaway SET {column} = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4", role_id, ctx.guild.id, message.channel.id, message.id)
                embed.add_field(name=flag.capitalize(), value=role_obj.mention, inline=True)
            except Exception:
                return await ctx.send_warning("Invalid role provided.")
        elif flag in ["messages", "level", "invites"]:
            try:
                value = int(input)
                await self.bot.db.execute(f"UPDATE giveaway SET {column} = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4", value, ctx.guild.id, message.channel.id, message.id)
                embed.add_field(name=flag.capitalize(), value=value, inline=True)
            except ValueError:
                return await ctx.send_warning("Invalid number provided.")
        await message.edit(embed=embed)
        await ctx.send_success(f"Added {flag} requirement to the [`giveaway`]({message.jump_url})")

    @giveaway_requirements.command(name="remove", brief="manage guild", usage="giveaway requirements remove 1256932539411468380 role")
    async def giveaway_requirements_remove(self, ctx: EvelinaContext, message: ValidMessage, flag: str):
        """Remove a requirement from the giveaway"""
        valid_flags = ["role", "bonus", "messages", "level", "invites", "ignore"]
        if flag not in valid_flags:
            formatted_flags = ", ".join(f"`{f}`" for f in valid_flags[:-1]) + f" & `{valid_flags[-1]}`"
            return await ctx.send_warning(f"Invalid flag. Use one of: {formatted_flags}")
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("This message is not a giveaway or it ended if it was one")
        column = f"required_{flag}" if flag != "bonus" else "required_bonus"
        if check[column] is None:
            return await ctx.send_warning(f"The {flag} requirement is not set and cannot be removed")
        embed = message.embeds[0]
        await self.bot.db.execute(f"UPDATE giveaway SET {column} = NULL WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        for field in embed.fields:
            if field.name.lower() == flag:
                embed.remove_field(embed.fields.index(field))
                break
        await message.edit(embed=embed)
        await ctx.send_success(f"Removed {flag} requirement from the [`giveaway`]({message.jump_url})")

    @giveaway_requirements.command(name="edit", brief="manage guild", usage="giveaway requirements edit role 1256932539411468380 Moderator")
    async def giveaway_requirements_edit(self, ctx: EvelinaContext, message: ValidMessage, flag: str, *, input: str):
        """Edit an existing requirement in the giveaway"""
        valid_flags = ["role", "bonus", "messages", "level", "invites", "ignore"]
        if flag not in valid_flags:
            formatted_flags = ", ".join(f"`{f}`" for f in valid_flags[:-1]) + f" & `{valid_flags[-1]}`"
            return await ctx.send_warning(f"Invalid flag. Use one of: {formatted_flags}")
        check = await self.bot.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("This message is not a giveaway or it ended if it was one")
        column = f"required_{flag}" if flag != "bonus" else "required_bonus"
        if check[column] is None:
            await self.giveaway_requirements_add(ctx, message, flag, input=input)
        elif check[column] is not None:
            await self.giveaway_requirements_remove(ctx, message, flag)

async def setup(bot: AB) -> None:
    await bot.add_cog(Giveaway(bot))