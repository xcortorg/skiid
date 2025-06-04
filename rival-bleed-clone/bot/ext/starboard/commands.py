import discord
from discord.ext import commands
from discord.ui import Button, View
from discord.ext.commands import Context, CommandError, check, Boolean, Cog
from lib.classes.color import ColorConverter
from discord import Embed, Member, Role, TextChannel, Thread, Client
import orjson
from typing import Union, Optional


def boolean_to_emoji(ctx: Context, boolean: bool):
    if boolean:
        return ctx.bot.config["emojis"]["success"]
    return ctx.bot.config["emojis"]["fail"]


def starboard_check():
    async def predicate(ctx: Context):
        query = "SELECT EXISTS(SELECT 1 FROM starboard WHERE guild_id = $1)"
        if await ctx.bot.db.fetchval(query, ctx.guild.id):
            return True
        else:
            raise CommandError(
                f"**Starboard** hasn't been setup using `{ctx.prefix}starboard set`"
            )

    return check(predicate)


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    @commands.group(
        name="starboard",
        usage="(subcommand) <args>",
        aliases=["board", "star"],
        description="Showcase the best messages in your server",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard(self: "Commands", ctx: Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @starboard.command(
        name="threshold",
        aliases=["amount"],
        description="Sets the default amount stars needed to post",
        example=",starboard threshold 5",
    )
    @starboard_check()
    @commands.has_permissions(manage_guild=True)
    async def starboard_threshold(self: "Commands", ctx: Context, *, number: int):
        query = "UPDATE starboard SET threshold = $1 WHERE guild_id = $2"
        await ctx.bot.db.execute(query, number, ctx.guild.id)
        return await ctx.success(f"**Starboard** threshold has been set to `{number}`")

    @starboard.command(
        name="selfstar", description="Allow an author to star their own message"
    )
    @starboard_check()
    @commands.has_permissions(manage_guild=True)
    async def starboard_selfstar(self: "Commands", ctx: Context, *, option: Boolean):
        query = "UPDATE starboard SET self_star = $1 WHERE guild_id = $2"
        await ctx.bot.db.execute(query, option, ctx.guild.id)
        return await ctx.success(f"**Starboard** selfstar has been set to `{option}`")

    @starboard.command(
        name="set",
        usage="(channel) (emoji) (amount)",
        example=",starboard set #highlights ⭐",
        description="Set the channel for the starboard.",
        parameters={
            "threshold": {
                "converter": int,
                "description": "The number of reactions required to be saved",
                "default": 1,
                "minimum": 1,
                "maximum": 120,
                "aliases": ["amount", "count"],
            }
        },
        aliases=["create"],
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard_set(
        self: "Commands",
        ctx: Context,
        channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
        emoji: Optional[str] = "⭐",
    ):
        channel = channel or ctx.channel
        if await self.bot.db.fetchrow(
            """SELECT * FROM starboard WHERE guild_id = $1""", ctx.guild.id
        ):
            raise CommandError(
                f"**Starboard** has already been setup. -to reset use `{ctx.prefix}starboard reset`"
            )
        try:
            await ctx.message.add_reaction(emoji)
        except discord.HTTPException:
            return await ctx.fail(f"**{emoji}** is not a valid emoji")
        threshold = ctx.parameters.get("threshold")
        if threshold == 1:
            m = ""
        else:
            m = f"with a threshold of `{threshold}`"
        try:
            await self.bot.db.execute(
                "INSERT INTO starboard (guild_id, channel_id, emoji, threshold) VALUES ($1, $2, $3, $4)",
                ctx.guild.id,
                channel.id,
                emoji,
                ctx.parameters.get("threshold"),
            )
        except Exception as e:
            raise e
            await ctx.fail(f"There is already a **starboard** using **{emoji}**")
        else:
            await ctx.success(
                f"**Starboard** channel has been set to {channel.mention} using **{emoji}** {m}"
            )

    @starboard.command(
        name="lock", description="Disables/locks clownboard from operating"
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_lock(self: "Commands", ctx: Context):
        prefix = (
            await self.bot.db.fetchval(
                """SELECT prefix FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or ","
        )
        current_state = await self.bot.db.fetchval(
            """SELECT lock FROM starboard WHERE guild_id = $1""", ctx.guild.id
        )
        if current_state:
            return await ctx.fail(
                f"**Starboard** is **already locked**, use `{prefix}starboard unlock` to unlock."
            )
        await self.bot.db.execute(
            """UPDATE starboard SET lock = $1 WHERE guild_id = $2""", True, ctx.guild.id
        )
        return await ctx.success(
            f"**Starboard** has been **locked**. Use `{prefix}starboard unlock` to revert."
        )

    @starboard.command(
        name="unlock", description="Enables/unlocks clownboard from operating"
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_unlock(self: "Commands", ctx: Context):
        prefix = (
            await self.bot.db.fetchval(
                """SELECT prefix FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or ","
        )
        current_state = await self.bot.db.fetchval(
            """SELECT lock FROM starboard WHERE guild_id = $1""", ctx.guild.id
        )
        if not current_state:
            return await ctx.fail(
                f"**Starboard** is **already unlocked**, use `{prefix}starboard lock` to lock"
            )
        await self.bot.db.execute(
            """UPDATE starboard SET lock = $1 WHERE guild_id = $2""",
            False,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**Starboard** has been **unlocked**, use `{prefix}starboard lock` to revert."
        )

    @starboard.command(
        name="color",
        aliases=["hexit"],
        description="set the starboard embed color",
        example=",starboard color #151515",
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_color(self: "Commands", ctx: Context, *, color: ColorConverter):
        await self.bot.db.execute(
            """UPDATE starboard SET color = $1 WHERE guild_id = $2""",
            str(color),
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully set the starboard color to `#{str(color)}`"
        )

    @starboard.command(
        name="timestamp",
        aliases=["ts", "time"],
        description="Allow a timestamp to appear on a Starboard post",
        example=",starboard timestamp true",
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_timestamp(self: "Commands", ctx: Context, *, option: Boolean):
        await self.bot.db.execute(
            """INSERT INTO starboard (guild_id, ts) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET ts = excluded.ts""",
            ctx.guild.id,
            option,
        )
        return await ctx.success(
            f"successfully **{'ENABLED' if option else 'DISABLED'}** starboard timestamps"
        )

    @starboard.command(
        name="attachments",
        aliases=["files", "a", "images", "img", "imgs"],
        description="Allow attachments to appear on Starboard posts",
        example=",starboard attachments true",
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_attachments(self: "Commands", ctx: Context, *, option: Boolean):
        await self.bot.db.execute(
            """INSERT INTO starboard (guild_id, attachments) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET attachments = excluded.attachments""",
            ctx.guild.id,
            option,
        )
        return await ctx.success(
            f"successfully **{'ENABLED' if option else 'DISABLED'}** starboard attachments"
        )

    @starboard.command(
        name="jumpurl",
        aliases=["jump", "url"],
        description="Allow the jump URL to appear on a Starboard post",
        example=",starboard jumpurl true",
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_jumpurl(self: "Commands", ctx: Context, *, option: Boolean):
        await self.bot.db.execute(
            """INSERT INTO starboard (guild_id, jump) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET jump = excluded.jump""",
            ctx.guild.id,
            option,
        )
        await ctx.success(
            f"successfully **{'ENABLED' if option else 'DISABLED'}** starboard jump urls on embeds"
        )

    @starboard.command(
        name="emoji",
        aliases=["emote"],
        description="Sets the emoji that triggers the starboard messages",
        example=",starboard emoji 💀",
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_emoji(self: "Commands", ctx: Context, *, emoji: str):
        await self.bot.db.execute(
            """INSERT INTO starboard (guild_id, emoji) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET emoji = excluded.emoji""",
            ctx.guild.id,
            str(emoji),
        )
        return await ctx.success(
            f"successfully set the starboard emoji as {str(emoji)}"
        )

    @starboard.command(
        name="reset",
        description="Reset the guild's starboard configuration",
        aliases=[
            "delete",
        ],
    )
    @starboard_check()
    @commands.has_permissions(manage_guild=True)
    async def starboard_reset(self: "Commands", ctx: Context):
        class ConfirmReset(View):
            def __init__(self, bot):
                super().__init__(timeout=15)
                self.bot = bot
                self.value = None

            @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
            async def approve(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if interaction.user != ctx.author:
                    embed = discord.Embed(
                        description=f"<:warning:1286583936113311755> {interaction.user.mention}: Your interaction is not allowed on this embed",
                        color=0xE69705,
                    )
                    return await interaction.response.send_message(
                        embed=embed, ephemeral=True
                    )

                await interaction.response.defer()
                await self.bot.db.execute(
                    """DELETE FROM starboard WHERE guild_id = $1""", ctx.guild.id
                )
                prefix = (
                    await self.bot.db.fetchval(
                        """SELECT prefix FROM config WHERE guild_id = $1""",
                        ctx.guild.id,
                    )
                    or ","
                )
                embed = discord.Embed(
                    description=f"<:check:1286583241905803356> {ctx.author.mention}: Starboard has been **reset**. Run `{prefix}help starboard` to see a list of options.",
                    color=0x90DA68,
                )
                await message.edit(embed=embed, view=None)
                self.value = True
                self.stop()

            @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
            async def decline(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if interaction.user != ctx.author:
                    embed = discord.Embed(
                        description=f"<:warning:1286583936113311755> {interaction.user.mention}: Your interaction is not allowed on this embed",
                        color=0xE69705,
                    )
                    return await interaction.response.send_message(
                        embed=embed, ephemeral=True
                    )
                await message.delete()
                self.value = False
                self.stop()

        embed = discord.Embed(
            description=f"<:settings:1287327423746146334> {ctx.author.mention}: Are you sure that you want to **reset** your Starboard settings?",
            color=0x6E879C,
        )
        view = ConfirmReset(self.bot)
        message = await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is None:
            await message.delete()

    @starboard.command(
        name="settings",
        aliases=["config"],
        description="Display your current starboard settings",
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard_settings(self: "Commands", ctx: Context):
        starboard = await self.bot.db.fetchrow(
            """SELECT * FROM starboard WHERE guild_id = $1""", ctx.guild.id
        )
        if not starboard:
            return await ctx.warning(
                "**Starboard** hasn't been setup using `{ctx.prefix}starboard set"
            )

        description = f"**Locked:** {boolean_to_emoji(ctx, starboard.lock)}"

        general_value = f"**Channel:** {f'<#{starboard.channel_id}>' if starboard.channel_id else 'No channel set'}\n**Color:** {f'`#{starboard.color}' if starboard.color else 'Author color'}\n**Threshold:** {starboard.threshold}\n**Emoji:** {starboard.emoji}"

        options_value = f"**Show Attachments:** {boolean_to_emoji(ctx, starboard.attachments)}\n**Show Timestamps:** {boolean_to_emoji(ctx, starboard.ts)}\n**Show Jump URL:** {boolean_to_emoji(ctx, starboard.jump)}\n**Self Star:** {boolean_to_emoji(ctx, starboard.self_star)}"
        roles = 0
        channels = 0
        members = 0
        if starboard.ignore_entries:
            data = orjson.loads(starboard.ignore_entries)
            for d in data:
                if ctx.guild.get_channel(d):
                    channels += 1
                elif ctx.guild.get_member(d):
                    members += 1
                elif ctx.guild.get_role(d):
                    roles += 1
                else:
                    continue

        count_value = f"**Blacklisted Channels:** {channels}\n**Blacklisted Users:** {members}\n**Blacklisted Roles:** {roles}"
        embed = Embed(
            color=0x6E879C, title="Starboard configuration", description=description
        )

        embed.add_field(name="General", value=general_value, inline=True)
        embed.add_field(name="Options", value=options_value, inline=True)
        embed.add_field(name="Count", value=count_value, inline=True)
        return await ctx.send(embed=embed)

    @starboard.group(
        name="ignore",
        description="Ignore a channel, member, or role, for reactions",
        example=",starboard ignore @kuzay",
        usage="channel or member or role",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_ignore(
        self: "Commands",
        ctx: Context,
        *,
        member_channel_role: Union[Member, Role, TextChannel, Thread],
    ):
        if member_channel_role is None:
            return await ctx.fail(
                "You must mention a valid **channel**, **role**, or **user**"
            )
        data = orjson.loads(
            await self.bot.db.fetchval(
                """SELECT ignore_entries FROM starboard WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "[]"
        )
        if member_channel_role.id not in data:
            data.append(member_channel_role.id)
            option = f"**Starboard** will now **ignore** {member_channel_role.mention}"
        else:
            data.remove(member_channel_role.id)
            option = (
                f"**Starboard** will no longer ignore {member_channel_role.mention}"
            )

        await self.bot.db.execute(
            """UPDATE starboard SET ignore_entries = $1 WHERE guild_id = $2""",
            orjson.dumps(data),
            ctx.guild.id,
        )
        return await ctx.success(f"{option}")

    @starboard_ignore.command(
        name="list",
        aliases=["show", "all"],
        description="View ignored roles, members and channels for Starboard",
    )
    @commands.has_permissions(manage_guild=True)
    @starboard_check()
    async def starboard_ignore_list(self: "Commands", ctx: Context):
        data = orjson.loads(
            await self.bot.db.fetchval(
                """SELECT ignore_entries FROM starboard WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "[]"
        )
        if not data:
            return await ctx.fail(
                "**Starboard** has no ignored **roles**, **members**, or **channels**"
            )
        rows = []
        diff = 0
        for i, entry in enumerate(data, start=1):
            if ctx.guild.get_role(entry):
                rows.append(
                    f"`{i - diff}` {ctx.guild.get_role(entry).mention} --**role**"
                )
            elif ctx.guild.get_member(entry):
                rows.append(
                    f"`{i - diff}` {ctx.guild.get_member(entry).mention} --**member**"
                )
            elif ctx.guild.get_channel(entry):
                rows.append(
                    f"`{i - diff}` {ctx.guild.get_channel(entry).mention} --**channel**"
                )
            else:
                diff += 1
                continue
        return await ctx.paginate(
            Embed(color=self.bot.color, title="Starboard Blacklists"), rows
        )
