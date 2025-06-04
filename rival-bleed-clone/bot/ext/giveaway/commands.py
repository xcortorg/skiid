from discord.ext.commands import (
    Cog,
    command,
    Greedy,
    group,
    CommandError,
    MultipleRoles,
    has_permissions,
    Expiration,
)
from discord import (
    Client,
    Embed,
    File,
    TextChannel,
    Member,
    Message,
    User,
    Guild,
    utils,
)
from lib.patch.context import Context
from typing import Optional, List
from random import sample
from datetime import datetime, timedelta
from lib.classes.database import Record


def shorten(text: str, length: int):
    return text[:length] + "..." if len(text) > length else text


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    def get_requirements(self, record: Record) -> List[str]:
        r = []
        if record.max_level:
            r.append(f"Must have **level {record.max_level}**")
        if record.min_level:
            r.append(f"Must have **level {record.min_level}**")
        if record.required_roles:
            for role_id in record.required_roles:
                r.append(f"Must have **<@&{role_id}>**")
        return r

    @group(
        name="giveaway",
        description="Start a giveaway quickly and easily",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def giveaway(self, ctx: Context):
        return await ctx.send_help()

    @giveaway.command(
        name="reroll",
        description="Reroll a winner for the specified giveaway",
        example=",giveaway reroll discord.com/channels/... 3",
    )
    @has_permissions(manage_channels=True)
    async def reroll(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        winners: Optional[int] = 1,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not (
            giveaway := await self.bot.db.fetchrow(
                """SELECT entries, win_message_id, prize, host FROM giveaways WHERE message_id = $1""",
                message.id,
            )
        ):
            raise CommandError("that is not a giveaway")
        if not giveaway.win_message_id:
            raise CommandError("that giveaway isn't over yet")
        if winners < 1:
            raise CommandError("winner count must be an integer higher than 1")
        entries = [
            ctx.guild.get_member(i) for i in giveaway.entries if ctx.guild.get_member(i)
        ]
        new_winners = sample(entries, winners)
        winners_string = ", ".join(m.mention for m in new_winners)
        embed = Embed(
            title=f"Winners for {shorten(giveaway.prize, 25)}",
            description=f"{winners_string} {'have' if winners > 1 else 'has'} won the giveaway from <@{giveaway.host}>",
        )
        await message.edit(embed=embed)
        return await ctx.message.add_reaction("👍")

    @giveaway.command(
        name="end",
        description="End an active giveaway early",
        example=",giveaway end discord.com/channels/....",
    )
    @has_permissions(manage_channels=True)
    async def end(self, ctx: Context, message: Optional[Message] = None):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not (
            giveaway := await self.bot.db.fetchrow(
                """SELECT * FROM giveaways WHERE message_id = $1""", message.id
            )
        ):
            raise CommandError("that is not a giveaway")
        self.bot.dispatch("giveaway_end", ctx.guild, message.channel, giveaway)
        return await ctx.message.add_reaction("👍")

    @giveaway.group(
        name="edit",
        description="Edit options and limits for a specific giveaway",
        example=",giveaway edit host a_URL jonathan",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit(self, ctx: Context):
        return await ctx.send_help()

    @giveaway_edit.command(
        name="maxlevel",
        description="Set the maximum level requirement for giveaway entry",
        example=",giveaway edit maxlevel discord.com/channels/... 10",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_maxlevel(
        self, ctx: Context, message: Optional[Message] = None, level: Optional[int] = 1
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET max_level = $1 WHERE message_id = $2""",
                level,
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        giveaway = await self.bot.db.fetchrow(
            """SELECT * FROM giveaways WHERE message_id = $1""", message.id
        )
        end_time = giveaway.expiration
        winners = giveaway.winner_count
        hosts = []
        for host in giveaway.hosts:
            hosts.append(
                self.bot.get_user(giveaway.host) or await self.bot.fetch_user(host)
            )
        hosts_string = ", ".join(f"{str(m)}" for m in hosts if m != None)
        requirements = self.get_requirements(giveaway)
        requirements_string = "**Requirements**\n"
        r = "\n".join(f"> {requirement}" for requirement in requirements)
        requirements_string += r
        embed = Embed(
            title=giveaway.prize,
            description=f"React with 🎉 to enter the giveaway.\n**Ends:** {utils.format_dt(end_time, style='R')} ({utils.format_dt(end_time, style='F')})\n**Winners:** {winners}\n**Hosted by:** {hosts_string}\n{requirements_string}",
            timestamp=giveaway.created_at,
        )
        await message.edit(embed=embed)
        return await ctx.message.add_reaction("👍")

    @giveaway_edit.command(
        name="prize",
        description="Change prize for a giveaway",
        example=",giveaway edit prize discord.com/channels/... tickets",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_prize(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        *,
        prize: Optional[str] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")

        if not prize:
            raise CommandError("a **Prize** is required")

        if not (
            giveaway := await self.bot.db.fetchrow(
                """SELECT * FROM giveaways WHERE message_id = $1""", message.id
            )
        ):
            raise CommandError("that is not a giveaway")

        embed = message.embeds[0]

        embed.title = prize
        await message.edit(embed=embed)
        await self.bot.db.execute(
            """UPDATE giveaways SET prize = $1 WHERE message_id = $2""",
            prize,
            message.id,
        )
        return await ctx.message.add_reaction("👍")

    @giveaway_edit.command(
        name="duration",
        description="Change the end date for a giveaway",
        example=",giveaway duration discord.com/channels/... 2d",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_duration(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        duration: Optional[Expiration] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")

        if not duration:
            raise CommandError("a **Duration** is required")
        end_time = datetime.now() + timedelta(seconds=duration)
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET expiration = $1 WHERE message_id = $2""",
                end_time,
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        giveaway = await self.bot.db.fetchrow(
            """SELECT * FROM giveaways WHERE message_id = $1""", message.id
        )
        end_time = giveaway.expiration
        winners = giveaway.winner_count
        hosts = []
        for host in giveaway.hosts:
            hosts.append(
                self.bot.get_user(giveaway.host) or await self.bot.fetch_user(host)
            )
        hosts_string = ", ".join(f"{str(m)}" for m in hosts if m != None)
        requirements = self.get_requirements(giveaway)
        requirements_string = "**Requirements**\n"
        r = "\n".join(f"> {requirement}" for requirement in requirements)
        requirements_string += r
        embed = Embed(
            title=giveaway.prize,
            description=f"React with 🎉 to enter the giveaway.\n**Ends:** {utils.format_dt(end_time, style='R')} ({utils.format_dt(end_time, style='F')})\n**Winners:** {winners}\n**Hosted by:** {hosts_string}\n{requirements_string}",
            timestamp=giveaway.created_at,
        )
        await message.edit(embed=embed)
        return await ctx.success(
            f"set the **expiration** of the giveaway to {utils.format_dt(end_time, style='R')}"
        )

    @giveaway_edit.command(
        name="image",
        description="Change image for a giveaway embed",
        example=",giveaway edit image discord.com/channels/... https://rival.rocks/image.png",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_image(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        url_or_attachment: Optional[str] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not url_or_attachment:
            if len(ctx.message.attachments) == 0:
                raise CommandError("either a **URL** or **Attachment** is required")
            url_or_attachment = ctx.message.attachments[0].url
        embed = message.embeds[0]
        embed.set_image(url=url_or_attachment)
        await message.edit(embed=embed)
        return await ctx.message.add_reaction("👍")

    @giveaway_edit.command(
        name="thumbnail",
        description="Change thumbnail for a giveaway embed",
        example=",giveaway edit image discord.com/channels/... https://rival.rocks/image.png",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_thumbnail(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        url_or_attachment: Optional[str] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not url_or_attachment:
            if len(ctx.message.attachments) == 0:
                raise CommandError("either a **URL** or **Attachment** is required")
            url_or_attachment = ctx.message.attachments[0].url
        embed = message.embeds[0]
        embed.set_thumbnail(url=url_or_attachment)
        await message.edit(embed=embed)
        return await ctx.message.add_reaction("👍")

    @giveaway_edit.command(
        name="age",
        description="Set minimum account age for new entries",
        example=",giveaway edit age discord.com/channels/...",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_age(
        self, ctx: Context, message: Optional[Message] = None, age: Optional[int] = None
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not age:
            raise CommandError("**Age** is a required parameter")
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET age = $1 WHERE message_id = $2""",
                age,
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        return await ctx.success(f"set the **minimum age** to {age} days")

    @giveaway_edit.command(
        name="host",
        description="Set new hosts for a giveaway",
        example=",giveaway edit host discord.com/channels/... @jonathan",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_host(
        self, ctx: Context, message: Message, members: Greedy[Member]
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not members:
            raise CommandError("at least one host is required")
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET hosts = $1 WHERE message_id = $2""",
                [m.id for m in members],
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        giveaway = await self.bot.db.fetchrow(
            """SELECT * FROM giveaways WHERE message_id = $1""", message.id
        )
        hosts = []
        for host in giveaway.hosts:
            hosts.append(
                self.bot.get_user(giveaway.host) or await self.bot.fetch_user(host)
            )
        hosts_string = ", ".join(f"{str(m)}" for m in hosts if m is not None)
        requirements = self.get_requirements(giveaway)
        requirements_string = "**Requirements**\n"
        r = "\n".join(f"> {requirement}" for requirement in requirements)
        requirements_string += r
        end_time = giveaway.expiration
        winners = giveaway.winner_count
        embed = Embed(
            title=giveaway.prize,
            description=f"React with 🎉 to enter the giveaway.\n**Ends:** {utils.format_dt(end_time, style='R')} ({utils.format_dt(end_time, style='F')})\n**Winners:** {winners}\n**Hosted by:** {hosts_string}\n{requirements_string}",
            timestamp=giveaway.created_at,
        )
        await message.edit(embed=embed)
        return await ctx.success(f"set the **hosts** to {hosts_string}")

    @giveaway_edit.command(
        name="requiredroles",
        description="Set required roles for giveaway entry",
        example=",giveaway edit requiredroles discord.com/channels/... @members, @boosters",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_requiredroles(
        self, ctx: Context, message: Optional[Message] = None, *, roles: MultipleRoles
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not roles:
            raise CommandError("at least one role is required")
        role_ids = [r.id for r in roles]
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET required_roles = $1 WHERE message_id = $2""",
                role_ids,
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        giveaway = await self.bot.db.fetchrow(
            """SELECT * FROM giveaways WHERE message_id = $1""", message.id
        )
        hosts = []
        for host in giveaway.hosts:
            hosts.append(
                self.bot.get_user(giveaway.host) or await self.bot.fetch_user(host)
            )
        hosts_string = ", ".join(f"{str(m)}" for m in hosts if m is not None)
        requirements = self.get_requirements(giveaway)
        requirements_string = "**Requirements**\n"
        r = "\n".join(f"> {requirement}" for requirement in requirements)
        requirements_string += r
        end_time = giveaway.expiration
        winners = giveaway.winner_count
        embed = Embed(
            title=giveaway.prize,
            description=f"React with 🎉 to enter the giveaway.\n**Ends:** {utils.format_dt(end_time, style='R')} ({utils.format_dt(end_time, style='F')})\n**Winners:** {winners}\n**Hosted by:** {hosts_string}\n{requirements_string}",
            timestamp=giveaway.created_at,
        )
        await message.edit(embed=embed)
        roles_string = ", ".join(r.mention for r in roles)
        return await ctx.success(f"set the **required roles** to {roles_string}")

    @giveaway_edit.command(
        name="minlevel",
        description="Set the minimum level requirement for giveaway entry",
        example=",giveaway minlevel discord.com/channels/... 5",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_minlevel(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        level: Optional[int] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not level:
            raise CommandError("a level is required")
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET min_level = $1 WHERE message_id = $2""",
                level,
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        giveaway = await self.bot.db.fetchrow(
            """SELECT * FROM giveaways WHERE message_id = $1""", message.id
        )
        hosts = []
        for host in giveaway.hosts:
            hosts.append(
                self.bot.get_user(giveaway.host) or await self.bot.fetch_user(host)
            )
        hosts_string = ", ".join(f"{str(m)}" for m in hosts if m is not None)
        requirements = self.get_requirements(giveaway)
        requirements_string = "**Requirements**\n"
        r = "\n".join(f"> {requirement}" for requirement in requirements)
        requirements_string += r
        end_time = giveaway.expiration
        winners = giveaway.winner_count
        embed = Embed(
            title=giveaway.prize,
            description=f"React with 🎉 to enter the giveaway.\n**Ends:** {utils.format_dt(end_time, style='R')} ({utils.format_dt(end_time, style='F')})\n**Winners:** {winners}\n**Hosted by:** {hosts_string}\n{requirements_string}",
            timestamp=giveaway.created_at,
        )
        await message.edit(embed=embed)
        return await ctx.success(f"set the **minimum level requirement** to {level}")

    @giveaway_edit.command(
        name="description",
        description="Change description for a giveaway",
        example=",giveaway edit description discord.com/channels/... sup",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_description(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        *,
        text: Optional[str] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not text:
            raise CommandError("a description is required")
        embed = message.embeds[0]
        description = f"{text}\n{embed.description}"
        embed.description = description
        await message.edit(embed=embed)
        return await ctx.message.add_reaction("👍")

    @giveaway_edit.command(
        name="winners",
        description="Change the amount of winners for a giveaway",
        example=",giveaway edit winners discord.com/channels/... 5",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_winners(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        count: Optional[int] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not count:
            raise CommandError("a count is required")
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET winner_count = $1 WHERE message_id = $2""",
                count,
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        giveaway = await self.bot.db.fetchrow(
            """SELECT * FROM giveaways WHERE message_id = $1""", message.id
        )
        hosts = []
        for host in giveaway.hosts:
            hosts.append(
                self.bot.get_user(giveaway.host) or await self.bot.fetch_user(host)
            )
        hosts_string = ", ".join(f"{str(m)}" for m in hosts if m is not None)
        requirements = self.get_requirements(giveaway)
        requirements_string = "**Requirements**\n"
        r = "\n".join(f"> {requirement}" for requirement in requirements)
        requirements_string += r
        end_time = giveaway.expiration
        winners = giveaway.winner_count
        embed = Embed(
            title=giveaway.prize,
            description=f"React with 🎉 to enter the giveaway.\n**Ends:** {utils.format_dt(end_time, style='R')} ({utils.format_dt(end_time, style='F')})\n**Winners:** {winners}\n**Hosted by:** {hosts_string}\n{requirements_string}",
            timestamp=giveaway.created_at,
        )
        await message.edit(embed=embed)
        return await ctx.success(f"set the **winner count** to {count}")

    @giveaway_edit.command(
        name="stay",
        description="Set minimum server stay for new entries",
        example=",giveaway edit stay discord.com/channels/... 5",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_stay(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        days: Optional[int] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not days:
            raise CommandError("a number of days is required")
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET min_stay = $1 WHERE message_id = $2""",
                days,
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        giveaway = await self.bot.db.fetchrow(
            """SELECT * FROM giveaways WHERE message_id = $1""", message.id
        )
        hosts = []
        for host in giveaway.hosts:
            hosts.append(
                self.bot.get_user(giveaway.host) or await self.bot.fetch_user(host)
            )
        hosts_string = ", ".join(f"{str(m)}" for m in hosts if m is not None)
        requirements = self.get_requirements(giveaway)
        requirements_string = "**Requirements**\n"
        r = "\n".join(f"> {requirement}" for requirement in requirements)
        requirements_string += r
        end_time = giveaway.expiration
        winners = giveaway.winner_count
        embed = Embed(
            title=giveaway.prize,
            description=f"React with 🎉 to enter the giveaway.\n**Ends:** {utils.format_dt(end_time, style='R')} ({utils.format_dt(end_time, style='F')})\n**Winners:** {winners}\n**Hosted by:** {hosts_string}\n{requirements_string}",
            timestamp=giveaway.created_at,
        )
        await message.edit(embed=embed)
        return await ctx.success(f"set the **minimum server stay** to {days} days")

    @giveaway_edit.command(
        name="roles",
        description="Award winners specific roles for a giveaway",
        example=",giveaway edit roles discord.com/channels/... @winners @giveaways",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_edit_roles(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        *,
        roles: Optional[MultipleRoles] = None,
    ):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        if not roles:
            raise CommandError("roles are required")
        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET rewarded_roles = $1 WHERE message_id = $2""",
                [r.id for r in roles],
                message.id,
            )
        except Exception:
            raise CommandError("that is not a giveaway")
        return await ctx.success(
            f"set the **rewarded roles** to {', '.join(r.mention for r in roles)}"
        )

    @giveaway.command(
        name="list", description="List every active giveaway in the server"
    )
    @has_permissions(manage_channels=True)
    async def giveaway_list(self, ctx: Context):
        giveaways = await self.bot.db.fetch(
            "SELECT * FROM giveaways WHERE guild_id = $1" "", ctx.guild.id
        )

        if not giveaways:
            raise CommandError("there are no active giveaways in this server")
        embed = Embed(title="Giveaways").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = []

        def get_message_link(record: Record) -> str:
            return f"https://discord.com/channels/{record.guild_id}/{record.channel_id}/{record.message_id}"

        for giveaway in giveaways:
            if giveaway.win_message_id:
                continue
            else:
                rows.append(f"[**{giveaway.prize}**]({get_message_link(giveaway)})")
        if len(rows) == 0:
            raise CommandError("there are no active giveaways in this server")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        return await ctx.paginate(embed, rows)

    @giveaway.command(
        name="cancel",
        description="Delete a giveaway without picking any winners",
        example=",giveaway cancel discord.com/channels/...",
    )
    @has_permissions(manage_channels=True)
    async def giveaway_cancel(self, ctx: Context, message: Optional[Message] = None):
        if not message:
            message = await self.bot.get_reference(ctx.message)
            if not message:
                raise CommandError("A message link is required")
        await self.bot.db.execute(
            """DELETE FROM giveaways WHERE message_id = $1""", message.id
        )
        await message.delete()
        return await ctx.success("successfully cancelled that giveaway")

    @giveaway.command(
        name="start",
        description="Start a giveaway with your provided duration, winners and prize description",
        example=",giveaways start #gw 24h 2 Concert Tickets",
    )
    @has_permissions(manage_channels=True)
    async def start(
        self,
        ctx: Context,
        channel: TextChannel,
        duration: Expiration,
        winners: int,
        *,
        prize: str,
    ):
        end_time = datetime.now() + timedelta(seconds=duration)
        embed = Embed(
            title=prize,
            description=f"React with 🎉 to enter the giveaway.\n**Ends:** {utils.format_dt(end_time, style='R')} ({utils.format_dt(end_time, style='F')})\n**Winners:** {winners}\n**Hosted by:** {str(ctx.author)}",
            timestamp=datetime.now(),
        )
        message = await channel.send(embed=embed)
        await message.add_reaction("🎉")
        await self.bot.db.execute(
            """INSERT INTO giveaways (guild_id, channel_id, message_id, winner_count, prize, expiration, entries, hosts) VALUES($1, $2, $3, $4, $5, $6, $7, $8)""",
            ctx.guild.id,
            channel.id,
            message.id,
            winners,
            prize,
            end_time,
            [],
            [ctx.author.id],
        )
        return await ctx.message.add_reaction("👍")
