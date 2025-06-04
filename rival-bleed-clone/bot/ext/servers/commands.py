from typing import Optional, Union, List
from discord.ext.commands import (
    Cog,
    group,
    CommandError,
    check,
    has_permissions,
    EmbedConverter,
    ColourConverter as ColorConverter,
    command,
    Converter,
    MultipleRoles,
    FakePermissionConverter,
    param,
    MessageLinkConverter,
    CommandConverter,
    Boolean,
    ModuleConverter,
    EventConverter,
)
from lib.classes.embed import embed_to_code
from discord import (
    Client,
    Embed,
    TextChannel,
    Message,
    Role,
    Emoji,
    Thread,
    PartialEmoji,
    Color,
    Member,
    AutoModTrigger,
    AutoModRuleTriggerType,
    AutoModRuleEventType,
    AutoModRuleAction,
    Webhook,
)
from discord.utils import utcnow
from lib.classes.embed import Script
from lib.classes.flags.servers import Parameters
from asyncpg import UniqueViolationError
from lib.classes.database import Record
from lib.classes.color import get_dominant_color
from lib.patch.context import Context
from lib.classes.flags.automod import FilterFlags, SpamFilterFlags
from lib.classes.builtins import human_join
import aiohttp
import random
import re
import string
import asyncio
import humanize
from lib.classes.converters import EVENT_MAPPING
from lib.classes.checks import is_booster
from ext.information.views import confirm

from ext.information.commands import CommandorGroup as CommandOrGroup

LINK_REGEX = r"(http|ftp|https):\/\/(?!open\.spotify\.com|tenor\.com)([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])"


def generate_id(length: int = 8) -> str:
    characters = string.ascii_lowercase + string.digits
    random_code = "".join(random.choice(characters) for _ in range(length))
    return random_code


class MultipleLinks(Converter):
    async def convert(self, ctx: Context, argument: str):
        if " , " in argument:
            arguments = argument.split(" , ")
        elif "," in argument:
            arguments = argument.split(",")
        else:
            arguments = [argument]
        return [match.group(2).lower() for match in re.iter(LINK_REGEX, argument)]


class RegexConverter(Converter):
    async def convert(self, ctx: Context, argument: str):
        try:
            re.compile(argument)
            return argument
        except re.error as e:
            raise CommandError(f"Invalid regex: {e}")


class MultipleInvites(Converter):
    async def convert(self, ctx: Context, argument: str) -> List[str]:
        arg = argument.lower()
        if " , " in arg:
            arguments = arg.split(" , ")
        elif "," in arg:
            arguments = arg.split(",")
        else:
            arguments = [arg]

        def resolve(invite: str) -> str:
            if "/" in invite:
                return invite.split("/")[-1]
            else:
                return invite

        return [resolve(a) for a in arguments]


class MultipleWords(Converter):
    async def convert(self, ctx: Context, argument: str) -> List[str]:
        arg = argument.lower()
        if " , " in arg:
            arguments = arg.split(" , ")
        elif "," in arg:
            arguments = arg.split(",")
        else:
            arguments = [arg]

        return arguments


ACTION_MAPPING = {"deny": ["d", "n", "no"], "allow": ["a", "y", "yes"]}


class AutoResponderAction(Converter):
    async def convert(self, ctx: Context, argument: str):
        argument = argument.lower()
        if ACTION_MAPPING.get(argument):
            return argument
        for key, value in ACTION_MAPPING.items():
            if argument in value:
                return key
        raise CommandError("valid inputs are `allow` and `deny`")


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    @group(
        name="webhook",
        aliases=["webhooks", "wh"],
        description="Set up webhooks in your server",
        invoke_without_command=True,
    )
    async def webhook(self, ctx: Context):
        return await ctx.send_help()

    @webhook.command(
        name="create",
        aliases=["c", "add", "setup", "a"],
        description="Create webhook to forward messages to",
        example=",webhook create purp",
    )
    @has_permissions(manage_webhooks=True)
    async def webhook_create(self, ctx: Context, *, name: str):
        webhook = await ctx.channel.create_webhook(
            name=name, reason=f"Created by {str(ctx.author)}"
        )
        serial = generate_id()
        await self.bot.db.execute(
            """INSERT INTO webhooks (guild_id, channel_id, id, name, url, created_by) VALUES($1, $2, $3, $4, $5, $6)""",
            ctx.guild.id,
            ctx.channel.id,
            serial,
            name,
            webhook.url,
            ctx.author.id,
        )
        return await ctx.success(
            f"Created webhook `{serial}` for {ctx.channel.mention}. Note that to edit any messages sent from the webhook, you **must** have the webhook identifer!"
        )

    @webhook.command(
        name="edit",
        aliases=["editmsg", "e"],
        description="Send message to existing channel webhook",
        example=",webhook edit https://discord.com/channels/... {embed}{description: sup}",
    )
    @has_permissions(manage_webhooks=True)
    async def webhook_edit(
        self,
        ctx: Context,
        message: Message = param(
            converter=MessageLinkConverter, default=MessageLinkConverter.fallback
        ),
        embed_code: Optional[EmbedConverter] = None,
    ):
        if not embed_code:
            raise CommandError("Please provide an embed's code")
        if not (
            row := await self.bot.db.fetchrow(
                """SELECT * FROM webhooks WHERE guild_id = $1 AND message_ids @> ARRAY[$1];""",
                ctx.guild.id,
                message.id,
            )
        ):
            raise CommandError(
                f"No valid webhook found under [this message]({message.jump_url})"
            )
        s = Script(embed_code, ctx.author)
        await s.compile()
        await s.send(message)
        return await ctx.success(
            f"Editted **webhook message**: [`{message.id}`]({message.jump_url}) for `{row.id}`"
        )

    @webhook.command(
        name="delete",
        aliases=["del", "rem", "remove", "d", "r"],
        description="Delete webhook for a channel",
        example=",webhook delete tx53151",
    )
    @has_permissions(manage_webhooks=True)
    async def webhook_delete(self, ctx: Context, identifier: str):
        if not (
            row := await self.bot.db.fetchrow(
                """DELETE FROM webhooks WHERE guild_id = $1 AND id = $2 RETURNING *""",
                ctx.guild.id,
                identifier,
            )
        ):
            raise CommandError(f"No valid webhook found with id `{identifier}`")
        message = await ctx.warning(
            f"Are you sure that you would like to delete the **webhook** `{identifier}`?"
        )
        confirmed: bool = await confirm(self, ctx, message)
        if confirmed:
            channel = ctx.guild.get_channel(row.channel_id)
            webhook = Webhook.from_url(
                row.url, client=self.bot, bot_token=self.bot.config["token"]
            )
            await webhook.delete()
            return await ctx.success(
                f"Deleted **webhook** for {channel.mention} Matching ID `{identifier}`"
            )
        else:
            await message.delete()

    @webhook.command(
        name="send",
        description="Send message to existing channel webhook",
        example=",webhook send txru114 {embed}{description: sup}",
    )
    @has_permissions(manage_webhooks=True)
    async def webhook_send(
        self, ctx: Context, identifier: str, embed_code: EmbedConverter
    ):
        if not (
            row := await self.bot.db.fetchrow(
                """SELECT * FROM webhooks WHERE guild_id = $1 AND id = $2""",
                ctx.guild.id,
                identifier,
            )
        ):
            raise CommandError(f"No valid webhook found with id `{identifier}`")
        s = Script(embed_code, ctx.author)
        await s.compile()
        data = await s.data(True)
        webhook = Webhook.from_url(
            row.url, client=self.bot, bot_token=self.bot.config["token"]
        )
        await webhook.send(**data)

    @webhook.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="List all available webhooks in the server",
    )
    @has_permissions(manage_webhooks=True)
    async def webhook_list(self, ctx: Context):
        rows = []
        if not (
            data := await self.bot.db.fetch(
                """SELECT id, created_by FROM webhooks WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No webhooks found in this server")
        for row in data:
            if user := self.bot.get_user(row.created_by):
                rows.append(f"`{row.id}` {user.mention} belongs to **{str(user)}**")
        return await ctx.paginate(
            Embed(title="Webhooks").set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            ),
            rows,
        )

    @group(name="prefix", description="View guild prefix", invoke_without_command=True)
    async def prefix(self: "Commands", ctx: Context):
        prefix = await self.bot.db.fetchval(
            """SELECT prefixes FROM config WHERE guild_id = $1""", ctx.guild.id
        ) or [","]
        await ctx.pin(
            f"Prefix for **{ctx.guild.name}** is {', '.join(f'`{p}`' for p in prefix)}"
        )

    @prefix.command(
        name="set",
        aliases=["setup"],
        description="Set a custom command guild prefix",
        example=",prefix !",
    )
    @has_permissions(manage_guild=True)
    async def set_prefix(self: "Commands", ctx: Context, prefix: str):
        if len(prefix) > 3:
            raise CommandError("Prefix cannot exceed **3** characters")
        await self.bot.db.execute(
            """INSERT INTO config (guild_id, prefixes) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET prefixes = excluded.prefixes""",
            ctx.guild.id,
            [prefix],
        )
        return await ctx.success(f"**Server prefix** updated to `{prefix}`")

    @prefix.command(
        name="add",
        description="add a custom command guild prefix",
        aliases=["a"],
        example=",prefix add !",
    )
    @has_permissions(manage_guild=True)
    async def add_prefix(self: "Commands", ctx: Context, prefix: str):
        if len(prefix) > 3:
            raise CommandError("Prefix cannot exceed **3** characters")
        await self.bot.db.execute(
            """INSERT INTO config (guild_id, prefixes) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET prefixes = ARRAY(SELECT 'prefix_' || unnest(EXCLUDED.prefixes));""",
            ctx.guild.id,
            prefix,
        )
        return await ctx.success(f"`{prefix}` was added as a **Server prefix**")

    @prefix.command(
        name="reset", aliases=["rs"], description="Reset your server's custom prefixes"
    )
    @has_permissions(manage_guild=True)
    async def prefix_reset(self, ctx: Context):
        try:
            await self.bot.db.execute(
                """UPDATE config SET prefixes = $1 WHERE guild_id = $2""",
                [","],
                ctx.guild.id,
            )
        except Exception:
            pass
        return await ctx.success(
            "This server's **custom prefixes** have been reset to `,`"
        )

    @prefix.command(
        name="remove",
        aliases=["rm"],
        description="Remove a custom command prefix for your server",
    )
    @has_permissions(manage_guild=True)
    async def prefix_remove(self: "Commands", ctx: Context, prefix: str):
        current_prefix = await self.bot.db.fetchval(
            """SELECT prefixes FROM config WHERE guild_id = $1""", ctx.guild.id
        )
        if prefix not in current_prefix:
            raise CommandError("Prefix not found in the server")
        if current_prefix != [","]:
            current_prefix.remove(prefix)
            if len(current_prefix) == 0:
                current_prefix = [","]
            await self.bot.db.execute(
                """UPDATE config SET prefixes = $1 WHERE guild_id = $2""",
                current_prefix,
                ctx.guild.id,
            )
            return await ctx.success(
                f"This server's **custom prefix** `{prefix}` has been **removed**"
            )
        else:
            return await ctx.fail(
                "There is no **custom prefix** set to remove for this server"
            )

    @prefix.group(
        name="self",
        description="Set personal command prefix across all servers with coffin",
        example=",prefix self k!",
        invoke_without_command=True,
    )
    async def prefix_self(self: "Commands", ctx: Context, prefix: str):
        if len(prefix) > 3:
            raise CommandError("Prefix cannot exceed **3** characters")
        await self.bot.db.execute(
            """INSERT INTO self_prefix (user_id, prefix) VALUES($1, $2) ON CONFLICT(user_id) DO UPDATE SET prefix = excluded.prefix""",
            ctx.author.id,
            prefix,
        )
        return await ctx.success(f"**Self prefix** updated to `{prefix}`")

    @prefix_self.command(
        name="remove",
        aliases=["clear", "cl", "del", "delete", "d", "c", "r"],
        description="clear your self prefix",
    )
    async def prefix_self_remove(self: "Commands", ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM self_prefix WHERE user_id = $1""", ctx.author.id
        )
        return await ctx.success("**Self prefix** has been cleared")

    @group(
        name="tracker",
        aliases=["trackers"],
        description="track username or vanity availability",
        invoke_without_command=True,
    )
    async def tracker(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @tracker.group(
        name="username",
        aliases=["names", "users", "usernames"],
        description="set the channel for tracking usernames",
        example=",tracker usernames add #names",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def tracker_username(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @tracker_username.command(
        name="add",
        aliases=["create", "set", "c", "a", "s"],
        description="add a channel for username notifications",
        example=",tracker username add #names",
    )
    @has_permissions(manage_guild=True)
    async def tracker_username_add(
        self, ctx: Context, *, channel: Union[TextChannel, Thread]
    ):
        channel_ids = (
            await self.bot.db.fetchval(
                """SELECT channel_ids FROM trackers WHERE tracker_type = $1 AND guild_id = $2""",
                "username",
                ctx.guild.id,
            )
            or []
        )
        if len(channel_ids) >= 2:
            raise CommandError("you can only have **2** tracker channels per type")
        if channel.id in channel_ids:
            raise CommandError("that channel is already a **username tracker**")
        channel_ids.append(channel.id)
        await self.bot.db.execute(
            """INSERT INTO trackers (guild_id, tracker_type, channel_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, tracker_type) DO UPDATE SET channel_ids = excluded.channel_ids""",
            ctx.guild.id,
            "username",
            channel_ids,
        )
        return await ctx.success(
            f"successfully **ADDED** {channel.mention} as a **username tracker**"
        )

    @tracker_username.command(
        name="remove",
        aliases=["delete", "del", "d", "r"],
        description="remove a channel for username notifications",
        example=",tracker username remove #names",
    )
    @has_permissions(manage_guild=True)
    async def tracker_username_remove(
        self, ctx: Context, *, channel: Union[TextChannel, Thread]
    ):
        if not (
            channel_ids := await self.bot.db.fetchval(
                """SELECT channel_ids FROM trackers WHERE tracker_type = $1 AND guild_id = $2""",
                "username",
                ctx.guild.id,
            )
        ):
            raise CommandError("No **username tracker** channels have been added")
        if channel.id not in channel_ids:
            raise CommandError(f"no **username tracker** found in {channel.mention}")
        channel_ids.remove(channel.id)
        if len(channel_ids) != 0:
            await self.bot.db.execute(
                """INSERT INTO trackers (guild_id, tracker_type, channel_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, tracker_type) DO UPDATE SET channel_ids = excluded.channel_ids""",
                ctx.guild.id,
                "username",
                channel_ids,
            )
        else:
            await self.bot.db.execute(
                """DELETE FROM trackers WHERE guild_id = $1 AND tracker_type = $2""",
                ctx.guild.id,
                "vanity",
            )
        return await ctx.success(
            f"successfully **REMOVED** {channel.mention} as a **username tracker**"
        )

    @tracker.group(
        name="vanity",
        aliases=["vanitys"],
        description="set the channel for tracking vanitys",
        example=",tracker vanitys add #vanities",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def tracker_vanity(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @tracker_vanity.command(
        name="add",
        aliases=["create", "set", "c", "a", "s"],
        description="add a channel for vanity notifications",
        example=",tracker vanity add #vanities",
    )
    @has_permissions(manage_guild=True)
    async def tracker_vanity_add(
        self, ctx: Context, *, channel: Union[TextChannel, Thread]
    ):
        channel_ids = (
            await self.bot.db.fetchval(
                """SELECT channel_ids FROM trackers WHERE tracker_type = $1 AND guild_id = $2""",
                "vanity",
                ctx.guild.id,
            )
            or []
        )
        if len(channel_ids) >= 2:
            raise CommandError("you can only have **2** tracker channels per type")
        if channel.id in channel_ids:
            raise CommandError("that channel is already a **username tracker**")
        channel_ids.append(channel.id)
        await self.bot.db.execute(
            """INSERT INTO trackers (guild_id, tracker_type, channel_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, tracker_type) DO UPDATE SET channel_ids = excluded.channel_ids""",
            ctx.guild.id,
            "vanity",
            channel_ids,
        )
        return await ctx.success(
            f"successfully **ADDED** {channel.mention} as a **vanity tracker**"
        )

    @tracker_vanity.command(
        name="remove",
        aliases=["delete", "del", "d", "r"],
        description="remove a channel for vanity notifications",
        example=",tracker vanity remove #vanities",
    )
    @has_permissions(manage_guild=True)
    async def tracker_vanity_remove(
        self, ctx: Context, *, channel: Union[TextChannel, Thread]
    ):
        if not (
            channel_ids := await self.bot.db.fetchval(
                """SELECT channel_ids FROM trackers WHERE tracker_type = $1 AND guild_id = $2""",
                "vanity",
                ctx.guild.id,
            )
        ):
            raise CommandError("No **vanity tracker** channels have been added")
        if channel.id not in channel_ids:
            raise CommandError(f"no **vanity tracker** found in {channel.mention}")
        channel_ids.remove(channel.id)
        if len(channel_ids) != 0:
            await self.bot.db.execute(
                """INSERT INTO trackers (guild_id, tracker_type, channel_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, tracker_type) DO UPDATE SET channel_ids = excluded.channel_ids""",
                ctx.guild.id,
                "vanity",
                channel_ids,
            )
        else:
            await self.bot.db.execute(
                """DELETE FROM trackers WHERE guild_id = $1 AND tracker_type = $2""",
                ctx.guild.id,
                "vanity",
            )
        return await ctx.success(
            f"successfully **REMOVED** {channel.mention} as a **vanity tracker**"
        )

    @tracker.command(
        name="settings",
        aliases=["config", "show", "view", "ls"],
        description="show your tracker configuration",
    )
    @has_permissions(manage_guild=True)
    async def tracker_settings(self, ctx: Context):
        if not (
            trackers := await self.bot.db.fetch(
                """SELECT tracker_type, channel_ids FROM trackers WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("no **trackers** have been setup")
        fields = []
        username_field = None
        vanity_field = None
        embed = Embed(title="Tracker Settings")

        def get_channels(tracker: Record):
            def get_name(channel_id: int):
                if channel := ctx.guild.get_channel(channel_id):
                    return channel.mention
                else:
                    return f"Unknown (`{channel_id}`)"

            channels = [
                f"`{i}` {get_name(channel_id)}" for channel_id in tracker.channel_ids
            ]
            return "\n.".join(m for m in channels)

        for i, tracker in enumerate(trackers, start=1):
            if tracker.tracker_type == "username":
                username_field = get_channels(tracker)
            if tracker.tracker_type == "vanity":
                vanity_field = get_channels(tracker)

        if vanity_field:
            fields.append({"name": "Vanity", "value": vanity_field, "inline": False})
        else:
            fields.append({"name": "Vanity", "value": "N/A", "inline": False})
        if username_field:
            fields.insert(
                0, {"name": "Username", "value": username_field, "inline": False}
            )
        else:
            fields.insert(0, {"name": "Username", "value": "N/A", "inline": False})
        for field in fields:
            embed.add_field(**field)
        return await ctx.send(embed=embed)

    @group(
        name="boosterrole",
        aliases=["boostrole", "br"],
        description="Get your own custom booster color role",
        example=",boosterrole ff0000 sexy",
        extras={"checks": "Boosters Only"},
        invoke_without_command=True,
    )
    async def boosterrole(
        self, ctx: Context
    ):  # color: Optional[ColorConverter] = None, *, name: Optional[str] = None):
        message = ctx.message
        message.content = message.content.replace("boosterrole", "boosterrole create")
        ctx = await self.bot.get_context(message)
        await ctx.reinvoke(restart=True, call_hooks=True)

    @boosterrole.command(
        name="create",
        deacription="Get your own custom booster color role",
        example=",boosterrole create #f47373 sup",
    )
    @is_booster()
    async def boosterrole_create(
        self,
        ctx: Context,
        color: Optional[ColorConverter] = None,
        *,
        name: Optional[str] = None,
    ):
        if not color and not name:
            return await ctx.send_help(ctx.command)
        kwargs = {}
        if name:
            if len(name) > 32:
                raise CommandError("Role name cannot exceed **32** characters")
            if len(name) < 2:
                raise CommandError("Role name must be at least **2** characters long")
            kwargs["name"] = name
        data = await self.bot.db.fetchrow(
            """SELECT base_id, role_limit FROM booster_roles WHERE guild_id = $1""",
            ctx.guild.id,
        )
        position = None
        if data:
            base_role = ctx.guild.get_role(data.base_id).position
            position = base_role.position - 1 if base_role.position > 1 else None
            if data.role_limit:
                if (
                    await self.bot.db.fetchval(
                        """SELECT COUNT(*) FROM custom_roles WHERE guild_id = $1""",
                        ctx.guild.id,
                    )
                    >= data.role_limit
                ):
                    raise CommandError(f"There is a max limit of {data.role_limit} set")
        role_id = await self.bot.db.fetchval(
            """SELECT role_id FROM custom_roles WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            ctx.author.id,
        )
        if not (role := ctx.guild.get_role(role_id)):
            if not name:
                name = ctx.author.name
            role = await ctx.guild.create_role(
                name=name, color=color, reason="booster role"
            )
            if position:
                await role.edit(position=position)
            await self.bot.db.execute(
                """INSERT INTO custom_roles (guild_id, user_id, role_id) VALUES($1, $2, $3) ON CONFLICT(guild_id, user_id) DO UPDATE SET role_id = excluded.role_id""",
                ctx.guild.id,
                ctx.author.id,
                role.id,
            )
            return await ctx.success(
                f"successfully made and assigned you {role.mention}"
            )
        else:
            await role.edit(color=color, **kwargs, reason="booster role")
            return await ctx.success(f"successfully set your color to `{color}`")

    @boosterrole.group(
        name="award",
        aliases=["reward"],
        description="Reward a member a specific role upon boost",
        example=",boosterrole award @rich",
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True, manage_guild=True)
    async def boosterrole_award(self, ctx: Context, *, role: Role):
        await self.bot.db.execute(
            """INSERT INTO booster_roles (guild_id, award_id) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET award_id = excluded.award_id""",
            ctx.guild.id,
            role.id,
        )
        for member in ctx.guild.premium_subscribers:
            if role not in member.roles:
                try:
                    await member.add_roles(role)
                except Exception:
                    pass
        return await ctx.success(f"now awarding all boosters with {role.mention}")

    @boosterrole_award.command(name="view", description="View the current award role")
    @has_permissions(manage_roles=True, manage_guild=True)
    async def boosterrole_award_view(self, ctx: Context):
        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT award_id FROM booster_roles WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("you have no booster role award set")
        role = ctx.guild.get_role(role_id)
        return await ctx.send(
            embed=Embed(
                title="Boost Award",
                description=f"**Role:** {role.mention}\n**Members:** {len(role.members)}",
            ).set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
        )

    @boosterrole_award.command(
        name="unset",
        description="Remove the reward role",
        aliases=["reset", "clear", "delete", "remove", "del", "d", "r", "c", "cl"],
    )
    @has_permissions(manage_roles=True, manage_guild=True)
    async def boosterrole_award_unset(self, ctx: Context):
        try:
            await self.bot.db.execute(
                """UPDATE booster_roles SET award_id = $1 WHERE guild_id = $2""",
                None,
                ctx.guild.id,
            )
        except Exception:
            raise CommandError("you have no booster role award set")
        return await ctx.success("booster role award has been removed")

    @boosterrole.command(
        name="base",
        description="Set the base role for where boost roles will go under",
        example=",boosterrole base @brs",
    )
    @has_permissions(manage_guild=True)
    async def boosterrole_base(self, ctx: Context, *, role: Role):
        if not role.is_assignable():
            raise CommandError(f"{role.mention} cannot be edited by me")
        tasks = []
        await self.bot.db.execute(
            """INSERT INTO booster_roles (guild_id, base_id) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET base_id = excluded.base_id""",
            ctx.guild.id,
            role.id,
        )
        role_ids = [
            role.role_id
            for role in await self.bot.db.fetch(
                """SELECT role_id FROM custom_roles WHERE guild_id = $1""", ctx.guild.id
            )
        ]
        for role_id in role_ids:
            booster_role = ctx.guild.get_role(role_id)
            if booster_role:
                await booster_role.edit(
                    position=role.position - 1 if role.position > 1 else 1,
                    reason=f"booster role base set by {str(ctx.author)}",
                )
            else:
                tasks.append(role_id)

        await self.bot.db.execute(
            """DELETE FROM custom_roles WHERE guild_id = $1 AND role_id = ANY($2::BIGINT[])""",
            ctx.guild.id,
            tasks,
        )
        return await ctx.success(f"successfully set the base role to {role.mention}")

    @boosterrole.command(
        name="limit",
        description="Set limit for booster roles",
        example=",boosterrole limit 30",
    )
    @has_permissions(manage_guild=True)
    async def boosterrole_limit(self, ctx: Context, limit: int):
        if limit < 1:
            limit = None
        await self.bot.db.execute(
            """INSERT INTO booster_roles (guild_id, limit) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET limit = excluded.limit""",
            ctx.guild.id,
            limit,
        )
        return await ctx.success(
            f"successfully set the booster role limit to {limit}"
            if limit
            else "successfully removed the booster role limit"
        )

    async def cleanup(self, ctx: Context, rows: List[Record]):
        for row in rows:
            if role := ctx.guild.get_role(row.role_id):
                try:
                    await role.delete(reason="booster role cleanup")
                except Exception:
                    pass
        await self.bot.db.execute(
            """DELETE FROM custom_roles WHERE guild_id = $1 AND role_id = ANY($2::BIGINT[])""",
            ctx.guild.id,
            [r.role_id for r in rows],
        )
        return True

    @boosterrole.command(name="list", description="View all booster roles")
    @has_permissions(manage_guild=True)
    async def boosterrole_list(self, ctx: Context):
        booster_roles = await self.bot.db.fetch(
            """SELECT user_id, role_id FROM custom_roles WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if not booster_roles:
            raise CommandError("No **Booster Roles** found")
        to_clear = [
            role
            for role in booster_roles
            if not ctx.guild.get_member(role.user_id)
            or not ctx.guild.get_role(role.role_id)
        ]
        booster_roles = [
            role for role in booster_roles if ctx.guild.get_member(role.user_id)
        ]
        rows = [
            f"`{i}` {ctx.guild.get_member(role.user_id).mention} - {ctx.guild.get_role(role.role_id).mention}"
            for i, role in enumerate(booster_roles, start=1)
        ]
        embed = Embed(title="Booster Roles").set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        if to_clear:
            asyncio.ensure_future(self.cleanup(ctx, to_clear))
        return await ctx.paginate(embed, rows)

    @boosterrole.command(
        name="dominant",
        description="Set booster roles color to the most dominant color in avatar",
    )
    @is_booster()
    async def boosterrole_dominant(self, ctx: Context):
        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM custom_roles WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                ctx.author.id,
            )
        ):
            raise CommandError("you have not setup a booster role using `boosterrole`")
        color = Color.from_str(await get_dominant_color(ctx.author) or "#303135")
        if role := ctx.guild.get_role(role_id):
            await role.edit(
                color=color, reason=f"booster role color changed by {str(ctx.author)}"
            )
            return await ctx.success(
                f"successfully changed your booster role **color** to `{str(color)}`"
            )
        else:
            raise CommandError(
                "your booster role got deleted, to resolve this do `boosterrole remove` then redo your setup using `booster role`"
            )

    @boosterrole.command(name="color", description="", example="")
    @is_booster()
    async def boosterrole_color(
        self, ctx: Context, color: ColorConverter, *, name: Optional[str] = None
    ):
        kwargs = {}
        if name:
            if len(name) > 32:
                raise CommandError("Role name cannot exceed **32** characters")
            if len(name) < 2:
                raise CommandError("Role name must be at least **2** characters long")
            kwargs["name"] = name
        data = await self.bot.db.fetchrow(
            """SELECT base_id, limit FROM booster_roles WHERE guild_id = $1""",
            ctx.guild.id,
        )
        position = ctx.guild.get_role(data.base_id).position - 1 or None
        if data.role_limit:
            if (
                await self.bot.db.fetchval(
                    """SELECT COUNT(*) FROM custom_roles WHERE guild_id = $1""",
                    ctx.guild.id,
                )
                >= data.role_limit
            ):
                raise CommandError(f"There is a max limit of {data.role_limit} set")

        role_id = await self.bot.db.fetchval(
            """SELECT role_id FROM custom_roles WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            ctx.author.id,
        )
        if not (role := ctx.guild.get_role(role_id)):
            if not name:
                name = ctx.author.name
            role = await ctx.guild.create_role(
                name=name, color=color, position=position, reason="booster role"
            )
            await self.bot.db.execute(
                """INSERT INTO custom_roles (guild_id, user_id, role_id) VALUES($1, $2, $3) ON CONFLICT(guild_id, user_id) DO UPDATE SET role_id = excluded.role_id""",
                ctx.guild.id,
                ctx.author.id,
                role.id,
            )
            return await ctx.success(
                f"successfully made and assigned you {role.mention}"
            )
        else:
            await role.edit(color=color, **kwargs, reason="booster role")
            return await ctx.success(f"successfully set your color to `{color}`")

    @boosterrole.command(name="remove", description="Remove custom color booster role")
    @is_booster()
    async def boosterrole_remove(self, ctx: Context):
        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM custom_roles WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                ctx.author.id,
            )
        ):
            raise CommandError("you have not setup a booster role using `boosterrole`")
        if role := ctx.guild.get_role(role_id):
            await role.delete(reason=f"booster role removed by {str(ctx.author)}")
        await self.bot.db.execute(
            """DELETE FROM custom_roles WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            ctx.author.id,
        )
        return await ctx.success("successfully removed your booster role")

    @boosterrole.command(name="cleanup", description="Clean up unused booster roles")
    @has_permissions(manage_roles=True, manage_guild=True)
    async def boosterrole_cleanup(self, ctx: Context):
        if not (
            roles := await self.bot.db.fetch(
                """SELECT role_id, user_id FROM custom_roles WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("there are no **booster roles**")
        role_ids = []
        for r in roles:
            if role := ctx.guild.get_role(r.role_id):
                if not ctx.guild.get_member(r.user_id):
                    await role.delete(
                        reason=f"booster role cleanup executed by {str(ctx.author)}"
                    )
                    role_ids.append(r.role_id)
            else:
                role_ids.append(r.role_id)

        await self.bot.db.execute(
            """DELETE FROM custom_roles WHERE role_id = ANY($2::BIGINT[]))""",
            ctx.guild.id,
            role_ids,
        )
        return await ctx.success(
            f"successfully cleaned up `{len(role_ids)}` **booster roles**"
        )

    @boosterrole.command(
        name="random", description="Set a booster role with a random hex code"
    )
    @is_booster()
    async def boosterrole_random(self, ctx: Context):
        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM custom_roles WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                ctx.author.id,
            )
        ):
            raise CommandError("you have not setup a booster role using `boosterrole`")
        random_color = random.randint(0, 0xFFFFFF)
        color = Color.from_str(f"#{random_color:06X}")
        if role := ctx.guild.get_role(role_id):
            await role.edit(
                color=color, reason=f"booster role color changed by {str(ctx.author)}"
            )
            return await ctx.success(
                f"successfully changed your booster role **color** to `{str(color)}`"
            )
        else:
            raise CommandError(
                "your booster role got deleted, to resolve this do `boosterrole remove` then redo your setup using `booster role`"
            )

    @boosterrole.command(
        name="icon",
        description="Set an icon for booster role",
        example=",boosterrole icon https://rival.rocks/yes.png",
    )
    @is_booster()
    async def boosterrole_icon(
        self,
        ctx: Context,
        *,
        icon: Optional[Union[Emoji, PartialEmoji, str]] = None,
    ):
        if "role_icons" not in [r.lower() for r in ctx.guild.features]:
            raise CommandError("This server does not have the **Role Icons** feature")

        async def get_icon(url: Optional[Union[Emoji, PartialEmoji, str]] = None):
            if url is None:
                return None
            if isinstance(url, Emoji):
                return await url.read()
            elif isinstance(url, PartialEmoji):
                return await url.read()
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        data = await resp.read()
                return data

        if isinstance(icon, str):
            if not icon.startswith("https://"):
                return await ctx.fail("that is not a valid URL")
        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM custom_roles WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                ctx.author.id,
            )
        ):
            raise CommandError(
                "you have not setup your booster role using `boosterrole`"
            )
        if not (role := ctx.guild.get_role(role_id)):
            raise CommandError(
                "your booster role got deleted, to resolve this do `boosterrole remove` then redo your setup using `booster role`"
            )
        await role.edit(
            display_icon=await get_icon(icon) if icon else None,
            reason=f"booster role icon changed by {str(ctx.author)}",
        )
        return await ctx.success(
            "successfully set your booster role icon"
            if icon
            else "successfully cleared your booster role icon"
        )

    @boosterrole.command(
        name="rename",
        description="Edit your booster roles name",
        example=",boosterrole rename richnigga",
    )
    @is_booster()
    async def boosterrole_rename(self, ctx: Context, *, name: str):
        if len(name) > 32:
            raise CommandError("Role name cannot exceed **32** characters")
        if len(name) < 2:
            raise CommandError("Role name must be at least **2** characters long")
        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM custom_roles WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                ctx.author.id,
            )
        ):
            raise CommandError("you have not setup a booster role using `boosterrole`")
        if role := ctx.guild.get_role(role_id):
            await role.edit(
                name=name, reason=f"booster role name changed by {str(ctx.author)}"
            )
            return await ctx.success("successfully renamed your booster role")
        else:
            raise CommandError(
                "your booster role got deleted, to resolve this do `boosterrole remove` then redo your setup using `booster role`"
            )

    @group(
        name="settings",
        description="No Description Provided",
        example=",settings jail #jail",
        invoke_without_command=True,
    )
    async def settings(self, ctx: Context):
        return await ctx.send_help()

    @settings.group(
        name="welcome",
        example=",settings welcome add #hi Hi {user.mention}! --self_destruct 10",
        aliases=["welc"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def settings_welcome(self, ctx: Context) -> Message:
        """
        Set up a welcome message in one or multiple channels
        """

        return await ctx.send_help()

    @settings_welcome.command(
        name="add",
        example=",settings welcome add #hi Hi {user.mention}! --self_destruct 10",
        aliases=["create"],
        flags=Parameters,
    )
    @has_permissions(manage_guild=True)
    async def settings_welcome_add(
        self, ctx: Context, channel: TextChannel, *, message: EmbedConverter
    ) -> Message:
        """
        Add a welcome message for a channel
        """

        if self_destruct := ctx.flags.get("self_destruct"):
            if self_destruct < 6:
                return await ctx.warn(
                    "**Self-destruct** timer must be at least `6` seconds"
                )

            elif self_destruct > 120:
                return await ctx.warn(
                    "**Self-destruct** timer must be below `120` seconds"
                )

        try:
            await self.bot.db.execute(
                """
				INSERT INTO join_messages (
					guild_id,
					channel_id,
					message,
					self_destruct
				) VALUES ($1, $2, $3, $4);
				""",
                ctx.guild.id,
                channel.id,
                message.script,
                self_destruct,
            )
        except UniqueViolationError:
            return await ctx.fail(
                "Theres already a **join message** for this channel, you can't have multiple for one channel. Remove the current **join message** then try again."
            )
        else:
            return await ctx.success(
                "Created "
                + ("an embed" if message.type == "embed" else "a")
                + f" **join message** and set the join channel to {channel.mention}"
                + (
                    f"\nEvery **join message** will self-destruct after `{self_destruct}` seconds"
                    if self_destruct
                    else ""
                )
            )

    @settings_welcome.command(
        name="remove",
        example=",settings goodbye remove #joneral",
        aliases=[
            "delete",
            "del",
        ],
    )
    @has_permissions(manage_guild=True)
    async def settings_welcome_remove(
        self, ctx: Context, *, channel: TextChannel
    ) -> Message:
        """
        Remove a welcome message from a channel
        """

        if await self.bot.db.fetchval(
            """
			DELETE FROM join_messages
			WHERE guild_id = $1
			AND channel_id = $2
			RETURNING channel_id;
			""",
            ctx.guild.id,
            channel.id,
        ):
            return await ctx.success(
                f"Removed the **join message** for {channel.mention}"
            )
        else:
            return await ctx.fail(f"No **join message** exists for {channel.mention}")

    @settings_welcome.command(
        name="view",
        example=",settings goodbye remove #joneral",
        aliases=["check"],
    )
    @has_permissions(manage_guild=True)
    async def settings_welcome_view(
        self, ctx: Context, *, channel: TextChannel
    ) -> Message:
        """
        View welcome message for a channel
        """

        if not (
            message := await self.bot.db.fetchval(
                """
			SELECT message FROM join_messages
			WHERE guild_id = $1
			AND channel_id = $2;
			""",
                ctx.guild.id,
                channel.id,
            )
        ):
            return await ctx.fail(f"No **join message** exists for {channel.mention}")

        return await self.bot.send_embed(ctx, message, member=ctx.author)

    @settings_welcome.command(name="list")
    @has_permissions(manage_guild=True)
    async def settings_welcome_list(self, ctx: Context) -> Message:
        """
        View all welcome messages
        """

        channels = [
            f"{channel.mention} (`{channel.id}`)"
            for row in await self.bot.db.fetch(
                """
				SELECT channel_id FROM join_messages
				WHERE guild_id = $1
				""",
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(row["channel_id"]))
        ]
        if not channels:
            return await ctx.search("No **welcome channels** are set")

        return await ctx.paginate(
            Embed(
                title="Welcome channels",
            ),
            channels,
        )

    @settings_welcome.command(name="variables")
    @has_permissions(manage_guild=True)
    async def settings_welcome_variables(self, ctx: Context) -> Message:
        """
        View all available variables for welcome messages
        """

        return await ctx.normal(
            "You can view all **variables** here: https://docs.bleed.bot/bot/embed-code-variables/variables",
            emoji=":information_source:",
        )

    @settings.group(
        name="goodbye",
        usage="(subcommand) <args> --params",
        example="add #goodbye See you soon! {user}",
        aliases=["bye"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def settings_goodbye(self, ctx: Context) -> Message:
        """
        Set up a goodbye message in one or multiple channels
        """

        return await ctx.send_help()

    @settings_goodbye.command(
        name="add",
        usage="(channel) (message) --params",
        example="#goodbye See you soon! {user}",
        aliases=["create"],
        flags=Parameters,
    )
    @has_permissions(manage_guild=True)
    async def settings_goodbye_add(
        self, ctx: Context, channel: TextChannel, *, message: EmbedConverter
    ) -> Message:
        """
        Add a goodbye message for a channel
        """

        if self_destruct := ctx.flags.get("self_destruct"):
            if self_destruct < 6:
                return await ctx.warn(
                    "**Self-destruct** timer must be at least `6` seconds"
                )

            elif self_destruct > 120:
                return await ctx.warn(
                    "**Self-destruct** timer must be below `120` seconds"
                )

        try:
            await self.bot.db.execute(
                """
				INSERT INTO leave_messages (
					guild_id,
					channel_id,
					message,
					self_destruct
				) VALUES ($1, $2, $3, $4);
				""",
                ctx.guild.id,
                channel.id,
                message.script,
                self_destruct,
            )
        except UniqueViolationError:
            return await ctx.fail(
                "Theres already a **leave message** for this channel, you can't have multiple for one channel. Remove the current **leave message** then try again."
            )
        else:
            return await ctx.success(
                "Created "
                + ("an embed" if message.type == "embed" else "a")
                + f" **leave message** and set the leave channel to {channel.mention}"
                + (
                    f"\nEvery **leave message** will self-destruct after `{self_destruct}` seconds"
                    if self_destruct
                    else ""
                )
            )

    @settings_goodbye.command(
        name="remove",
        example=",settings goodbye remove #joneral",
        aliases=[
            "delete",
            "del",
        ],
    )
    @has_permissions(manage_guild=True)
    async def settings_goodbye_remove(
        self, ctx: Context, *, channel: TextChannel
    ) -> Message:
        """
        Remove a goodbye message from a channel
        """

        if await self.bot.db.fetchval(
            """
			DELETE FROM leave_messages
			WHERE guild_id = $1
			AND channel_id = $2
			RETURNING channel_id;
			""",
            ctx.guild.id,
            channel.id,
        ):
            return await ctx.success(
                f"Removed the **leave message** for {channel.mention}"
            )
        else:
            return await ctx.fail(f"No **leave message** exists for {channel.mention}")

    @settings_goodbye.command(
        name="view",
        example=",settings goodbye remove #joneral",
        aliases=["check"],
    )
    @has_permissions(manage_guild=True)
    async def settings_goodbye_view(
        self, ctx: Context, *, channel: TextChannel
    ) -> Message:
        """
        View goodbye message for a channel
        """

        if not (
            message := await self.bot.db.fetchval(
                """
			SELECT message FROM leave_messages
			WHERE guild_id = $1
			AND channel_id = $2;
			""",
                ctx.guild.id,
                channel.id,
            )
        ):
            return await ctx.fail(f"No **leave message** exists for {channel.mention}")

        return await self.bot.send_embed(ctx, message, member=ctx.author)

    @settings_goodbye.command(name="list")
    @has_permissions(manage_guild=True)
    async def settings_goodbye_list(self, ctx: Context) -> Message:
        """
        View all goodbye messages
        """

        channels = [
            f"{channel.mention} (`{channel.id}`)"
            for row in await self.bot.db.fetch(
                """
				SELECT channel_id FROM leave_messages
				WHERE guild_id = $1
				""",
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(row["channel_id"]))
        ]
        if not channels:
            return await ctx.search("No **goodbye channels** are set")

        return await ctx.paginate(
            Embed(
                title="Goodbye channels",
            ),
            channels,
        )

    @settings_goodbye.command(name="variables")
    @has_permissions(manage_guild=True)
    async def settings_goodbye_variables(self, ctx: Context) -> Message:
        """
        View all available variables for goodbye messages
        """

        return await ctx.normal(
            "You can view all **variables** here: https://docs.bleed.bot/bot/embed-code-variables/variables",
            emoji=":information_source:",
        )

    @settings.group(
        name="boost",
        usage="(subcommand) <args> --params",
        example="add #hi Thanks {user.mention}!",
        aliases=["boosts"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def settings_boost(self, ctx: Context) -> Message:
        """
        Set up a boost message in one or multiple channels
        """

        return await ctx.send_help()

    @settings_boost.command(
        name="add",
        usage="(channel) (message) --params",
        example="#hi Thanks {user.mention}!",
        aliases=["create"],
        flags=Parameters,
    )
    @has_permissions(manage_guild=True)
    async def settings_boost_add(
        self, ctx: Context, channel: TextChannel, *, message: EmbedConverter
    ) -> Message:
        """
        Add a boost message for a channel
        """

        if self_destruct := ctx.flags.get("self_destruct"):
            if self_destruct < 6:
                return await ctx.warn(
                    "**Self-destruct** timer must be at least `6` seconds"
                )

            elif self_destruct > 120:
                return await ctx.warn(
                    "**Self-destruct** timer must be below `120` seconds"
                )

        try:
            await self.bot.db.execute(
                """
				INSERT INTO boost_messages (
					guild_id,
					channel_id,
					message,
					self_destruct
				) VALUES ($1, $2, $3, $4);
				""",
                ctx.guild.id,
                channel.id,
                message.script,
                self_destruct,
            )
        except UniqueViolationError:
            return await ctx.fail(
                "Theres already a **boost message** for this channel, you can't have multiple for one channel. Remove the current **boost message** then try again."
            )
        else:
            return await ctx.success(
                "Created "
                + ("an embed" if message.type == "embed" else "a")
                + f" **boost message** and set the boost channel to {channel.mention}"
                + (
                    f"\nEvery **boost message** will self-destruct after `{self_destruct}` seconds"
                    if self_destruct
                    else ""
                )
            )

    @settings_boost.command(
        name="remove",
        example=",settings goodbye remove #joneral",
        aliases=[
            "delete",
            "del",
        ],
    )
    @has_permissions(manage_guild=True)
    async def settings_boost_remove(
        self, ctx: Context, *, channel: TextChannel
    ) -> Message:
        """
        Remove a boost message from a channel
        """

        if await self.bot.db.fetchval(
            """
			DELETE FROM boost_messages
			WHERE guild_id = $1
			AND channel_id = $2
			RETURNING channel_id;
			""",
            ctx.guild.id,
            channel.id,
        ):
            return await ctx.success(
                f"Removed the **boost message** for {channel.mention}"
            )
        else:
            return await ctx.fail(f"No **boost message** exists for {channel.mention}")

    @settings_boost.command(
        name="view",
        example=",settings goodbye remove #joneral",
        aliases=["check"],
    )
    @has_permissions(manage_guild=True)
    async def settings_boost_view(
        self, ctx: Context, *, channel: TextChannel
    ) -> Message:
        """
        View boost message for a channel
        """

        if not (
            message := await self.bot.db.fetchval(
                """
			SELECT message FROM boost_messages
			WHERE guild_id = $1
			AND channel_id = $2;
			""",
                ctx.guild.id,
                channel.id,
            )
        ):
            return await ctx.fail(f"No **boost message** exists for {channel.mention}")
        return await self.bot.send_embed(ctx, message, member=ctx.author)

    @settings_boost.command(name="list")
    @has_permissions(manage_guild=True)
    async def settings_boost_list(self, ctx: Context) -> Message:
        """
        View all boost messages
        """

        channels = [
            f"{channel.mention} (`{channel.id}`)"
            for row in await self.bot.db.fetch(
                """
				SELECT channel_id FROM boost_messages
				WHERE guild_id = $1
				""",
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(row["channel_id"]))
        ]
        if not channels:
            return await ctx.search("No **boost channels** are set")

        return await ctx.paginate(
            Embed(
                title="Goodbye channels",
            ),
            channels,
        )

    @settings_boost.command(name="variables")
    @has_permissions(manage_guild=True)
    async def settings_boost_variables(self, ctx: Context) -> Message:
        """
        View all available variables for boost messages
        """

        return await ctx.normal(
            "You can view all **variables** here: https://docs.bleed.bot/bot/embed-code-variables/variables",
            emoji=":information_source:",
        )

    @group(
        name="alias",
        description="Create your own shortcuts for commands",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def alias(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @alias.command(
        name="view",
        description="View command execution for alias",
        example=",alias view hi",
    )
    @has_permissions(manage_guild=True)
    async def alias_view(self, ctx: Context, *, shortcut: str):
        if not (
            command := await self.bot.db.fetchval(
                """SELECT command_name FROM aliases WHERE guild_id = $1 AND alias = $2""",
                ctx.guild.id,
                shortcut,
            )
        ):
            raise CommandError(f"No alias under the shortcut `{shortcut[:25]}`")
        command = self.bot.get_command(command)
        return await ctx.normal(
            f"**{shortcut}** executes `{command.qualified_name}`", emoji="ℹ️"
        )

    @alias.command(
        name="removeall",
        description="Remove an alias for command",
        example=",alias removeall avatar",
    )
    @has_permissions(manage_guild=True)
    async def alias_removeall(self, ctx: Context, *, command: CommandConverter):
        await self.bot.db.execute(
            """DELETE FROM aliases WHERE command_name = $1 AND guild_id = $2""",
            command.qualified_name,
            ctx.guild.id,
        )
        return await ctx.success(
            f"Deleted **all aliases** matching `{command.qualified_name}`"
        )

    @alias.command(
        name="list",
        aliases=["ls", "l"],
        description="List every alias for all commands",
    )
    @has_permissions(manage_guild=True)
    async def alias_list(self, ctx: Context):
        if not (
            aliases := await self.bot.db.fetchall(
                """SELECT alias, command_name FROM aliases WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No aliases have been added")
        rows = [
            f"`{i}` **{a.alias}** executes `{a.command_name}`"
            for i, a in enumerate(aliases, start=1)
        ]
        return await ctx.paginate(
            Embed(color=self.bot.color, title="Aliases").set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            ),
            rows,
        )

    @alias.command(
        name="add",
        description="Create an alias for command",
        example=",alias add hi avatar",
    )
    @has_permissions(manage_guild=True)
    async def alias_add(
        self, ctx: Context, shortcut: str, *, command: CommandConverter
    ):
        await self.bot.db.execute(
            """INSERT INTO aliases (guild_id, command_name, alias) VALUES($1, $2, $3) ON CONFLICT(guild_id, alias) DO UPDATE SET command_name = excluded.command_name""",
            ctx.guild.id,
            command.qualified_name,
            shortcut,
        )
        return await ctx.success(f"Added **{shortcut}** for `{command.qualified_name}`")

    @alias.command(
        name="remove",
        description="Remove an alias for command",
        example=",alias remove hi",
    )
    @has_permissions(manage_guild=True)
    async def alias_remove(self, ctx: Context, *, shortcut: str):
        await self.bot.db.execute(
            """DELETE FROM aliases WHERE guild_id = $1 AND alias = $2""",
            ctx.guild.id,
            shortcut,
        )
        return await ctx.success(
            f"Deleted **all aliases** with the shortcut `{shortcut}`"
        )

    @alias.command(name="reset", description="Reset every alias for all commands")
    @has_permissions(manage_guild=True)
    async def alias_reset(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM aliases WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("reset **all aliases**")

    @group(
        name="stickymessage",
        aliases=["stickymsg"],
        description="Set up a sticky message in one or multiple channels",
    )
    @has_permissions(manage_guild=True)
    async def stickymessage(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @stickymessage.command(
        name="view", description="View the sticky message for a channel"
    )
    @has_permissions(manage_guild=True)
    async def stickymessage_view(self, ctx: Context, *, channel: TextChannel):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT code FROM sticky_message WHERE guild_id = $1 AND channel_id = $2""",
                ctx.guild.id,
                channel.id,
            )
        ):
            raise CommandError(f"No **sticky message** exists for {channel.mention}")
        return await ctx.bot.send_embed(ctx.channel, message, user=ctx.author)

    @stickymessage.command(
        name="add",
        description="Add a sticky message to a channel",
        example=",stickymessage add #general hi",
    )
    @has_permissions(manage_guild=True)
    async def stickymessage_add(
        self, ctx: Context, channel: TextChannel, *, message: str
    ):
        await self.bot.db.execute(
            """INSERT INTO sticky_message (guild_id, channel_id, code) VALUES($1, $2, $3) ON CONFLICT(guild_id, channel_id) DO UPDATE SET code = excluded.code""",
            ctx.guild.id,
            channel.id,
            message,
        )
        return await ctx.success(f"Added **sticky message** to {channel.mention}")

    @stickymessage.command(name="list", description="View all sticky messages")
    @has_permissions(manage_guild=True)
    async def stickymessage_list(self, ctx: Context):
        if not (
            messages := await self.bot.db.fetch(
                """SELECT channel_id, code FROM sticky_message WHERE guild-id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No **sticky messages** exist")
        rows = [
            f"`{i}` {ctx.guild.get_channel(row.channel_id)}"
            for i, row in enumerate(messages, start=1)
        ]
        return await ctx.paginate(
            Embed(title="Sticky messages", color=self.bot.color).set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            ),
            rows,
        )

    @stickymessage.command(
        name="remove",
        description="Remove a sticky message from a channe",
        example=",stickymessage remove #general",
    )
    @has_permissions(manage_guild=True)
    async def stickymessage_remove(self, ctx: Context, *, channel: TextChannel):
        await self.bot.db.execute(
            """DELETE FROM sticky_message WHERE guild_id = $1 AND channel_id = $2""",
            ctx.guild.id,
            channel.id,
        )
        return await ctx.success(
            f"successfully removed **sticky message** for {channel.mention}"
        )

    @group(name="invoke", description="", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke.group(
        name="softban",
        description="Change softban message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_softban(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_softban.group(
        name="dm",
        description="Change softban message for Direct Messages",
        example=",invoke softban dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_softban_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "softban",
            message,
        )
        return await ctx.success("successfully updated the softban DM")

    @invoke_softban_dm.command(
        name="view", description="View the softban message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_softban_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "softban",
            )
        ):
            raise CommandError("no **softban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_softban.group(
        name="message",
        aliases=["msg"],
        description="Change softban message for command response",
        example=",invoke softban message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_softban_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "softban",
            message,
        )
        return await ctx.success("successfully updated the softban message")

    @invoke_softban_message.command(
        name="view", description="View the softban message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_softban_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "softban",
            )
        ):
            raise CommandError("no **softban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="jail",
        description="Change jail message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_jail(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_jail.group(
        name="dm",
        description="Change jail message for Direct Messages",
        example=",invoke jail dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_jail_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "jail",
            message,
        )
        return await ctx.success("successfully updated the jail DM")

    @invoke_jail_dm.command(
        name="view", description="View the jail message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_jail_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "jail",
            )
        ):
            raise CommandError("no **jail message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_jail.group(
        name="message",
        aliases=["msg"],
        description="Change jail message for command response",
        example=",invoke jail message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_jail_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "jail",
            message,
        )
        return await ctx.success("successfully updated the jail message")

    @invoke_jail_message.command(
        name="view", description="View the jail message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_jail_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "jail",
            )
        ):
            raise CommandError("no **jail message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="timeout",
        description="Change timeout message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_timeout.group(
        name="dm",
        description="Change timeout message for Direct Messages",
        example=",invoke timeout dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "timeout",
            message,
        )
        return await ctx.success("successfully updated the timeout DM")

    @invoke_timeout_dm.command(
        name="view", description="View the timeout message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "timeout",
            )
        ):
            raise CommandError("no **timeout message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_timeout.group(
        name="message",
        aliases=["msg"],
        description="Change timeout message for command response",
        example=",invoke timeout message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "timeout",
            message,
        )
        return await ctx.success("successfully updated the timeout message")

    @invoke_timeout_message.command(
        name="view", description="View the timeout message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "timeout",
            )
        ):
            raise CommandError("no **timeout message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="kick",
        description="Change kick message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_kick.group(
        name="dm",
        description="Change kick message for Direct Messages",
        example=",invoke kick dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "kick",
            message,
        )
        return await ctx.success("successfully updated the kick DM")

    @invoke_kick_dm.command(
        name="view", description="View the kick message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "kick",
            )
        ):
            raise CommandError("no **kick message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_kick.group(
        name="message",
        aliases=["msg"],
        description="Change kick message for command response",
        example=",invoke kick message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "kick",
            message,
        )
        return await ctx.success("successfully updated the kick message")

    @invoke_kick_message.command(
        name="view", description="View the kick message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "kick",
            )
        ):
            raise CommandError("no **kick message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="unban",
        description="Change unban message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_unban.group(
        name="dm",
        description="Change unban message for Direct Messages",
        example=",invoke unban dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "unban",
            message,
        )
        return await ctx.success("successfully updated the unban DM")

    @invoke_unban_dm.command(
        name="view", description="View the unban message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "unban",
            )
        ):
            raise CommandError("no **unban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_unban.group(
        name="message",
        aliases=["msg"],
        description="Change unban message for command response",
        example=",invoke unban message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "unban",
            message,
        )
        return await ctx.success("successfully updated the unban message")

    @invoke_unban_message.command(
        name="view", description="View the unban message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "unban",
            )
        ):
            raise CommandError("no **unban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="unjail",
        description="Change unjail message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_unjail(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_unjail.group(
        name="dm",
        description="Change unjail message for Direct Messages",
        example=",invoke unjail dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_unjail_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "unjail",
            message,
        )
        return await ctx.success("successfully updated the unjail DM")

    @invoke_unjail_dm.command(
        name="view", description="View the unjail message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_unjail_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "unjail",
            )
        ):
            raise CommandError("no **unjail message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_unjail.group(
        name="message",
        aliases=["msg"],
        description="Change unjail message for command response",
        example=",invoke unjail message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_unjail_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "unjail",
            message,
        )
        return await ctx.success("successfully updated the unjail message")

    @invoke_unjail_message.command(
        name="view", description="View the unjail message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_unjail_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "unjail",
            )
        ):
            raise CommandError("no **unjail message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="hardban",
        description="Change hardban message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_hardban(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_hardban.group(
        name="dm",
        description="Change hardban message for Direct Messages",
        example=",invoke hardban dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_hardban_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "hardban",
            message,
        )
        return await ctx.success("successfully updated the hardban DM")

    @invoke_hardban_dm.command(
        name="view", description="View the hardban message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_hardban_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "hardban",
            )
        ):
            raise CommandError("no **hardban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_hardban.group(
        name="message",
        aliases=["msg"],
        description="Change hardban message for command response",
        example=",invoke hardban message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_hardban_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "hardban",
            message,
        )
        return await ctx.success("successfully updated the hardban message")

    @invoke_hardban_message.command(
        name="view", description="View the hardban message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_hardban_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "hardban",
            )
        ):
            raise CommandError("no **hardban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="untimeout",
        description="Change untimeout message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_untimeout.group(
        name="dm",
        description="Change untimeout message for Direct Messages",
        example=",invoke untimeout dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "untimeout",
            message,
        )
        return await ctx.success("successfully updated the untimeout DM")

    @invoke_untimeout_dm.command(
        name="view", description="View the untimeout message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "untimeout",
            )
        ):
            raise CommandError("no **untimeout message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_untimeout.group(
        name="message",
        aliases=["msg"],
        description="Change untimeout message for command response",
        example=",invoke untimeout message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "untimeout",
            message,
        )
        return await ctx.success("successfully updated the untimeout message")

    @invoke_untimeout_message.command(
        name="view", description="View the untimeout message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "untimeout",
            )
        ):
            raise CommandError("no **untimeout message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="tempban",
        description="Change tempban message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_tempban(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_tempban.group(
        name="dm",
        description="Change tempban message for Direct Messages",
        example=",invoke tempban dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_tempban_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "tempban",
            message,
        )
        return await ctx.success("successfully updated the tempban DM")

    @invoke_tempban_dm.command(
        name="view", description="View the tempban message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_tempban_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "tempban",
            )
        ):
            raise CommandError("no **tempban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_tempban.group(
        name="message",
        aliases=["msg"],
        description="Change tempban message for command response",
        example=",invoke tempban message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_tempban_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "tempban",
            message,
        )
        return await ctx.success("successfully updated the tempban message")

    @invoke_tempban_message.command(
        name="view", description="View the tempban message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_tempban_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "tempban",
            )
        ):
            raise CommandError("no **tempban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="warn",
        description="Change warn message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_warn(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_warn.group(
        name="dm",
        description="Change warn message for Direct Messages",
        example=",invoke warn dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_warn_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "warn",
            message,
        )
        return await ctx.success("successfully updated the warn DM")

    @invoke_warn_dm.command(
        name="view", description="View the warn message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_warn_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "warn",
            )
        ):
            raise CommandError("no **warn message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_warn.group(
        name="message",
        aliases=["msg"],
        description="Change warn message for command response",
        example=",invoke warn message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_warn_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "warn",
            message,
        )
        return await ctx.success("successfully updated the warn message")

    @invoke_warn_message.command(
        name="view", description="View the warn message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_warn_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "warn",
            )
        ):
            raise CommandError("no **warn message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke.group(
        name="ban",
        description="Change ban message for DM or command response",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @invoke_ban.group(
        name="dm",
        description="Change ban message for Direct Messages",
        example=",invoke ban dm {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban_dm(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, dm_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "ban",
            message,
        )
        return await ctx.success("successfully updated the ban DM")

    @invoke_ban_dm.command(
        name="view", description="View the ban message for Direct Messages"
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban_dm_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "ban",
            )
        ):
            raise CommandError("no **ban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @invoke_ban.group(
        name="message",
        aliases=["msg"],
        description="Change ban message for command response",
        example=",invoke ban message {embed}...",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban_message(self, ctx: Context, *, message: str):
        await self.bot.db.execute(
            """INSERT INTO invocation (guild_id, command, message_code) VALUES($1, $2, $3) ON CONFLICT(guild_id, command) DO UPDATE SET dm_code = excluded.dm_code""",
            ctx.guild.id,
            "ban",
            message,
        )
        return await ctx.success("successfully updated the ban message")

    @invoke_ban_message.command(
        name="view", description="View the ban message for command response"
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchval(
                """SELECT message_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                "ban",
            )
        ):
            raise CommandError("no **ban message** is set for this server")
        return await self.bot.send_embed(
            ctx.channel, message, user=ctx.author, moderator=ctx.author
        )

    @group(
        name="pagination",
        description="Set up multiple embeds on one message",
        invoke_without_command=True,
    )
    async def pagination(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @pagination.command(name="add", description="Add a page to a pagination embed")
    @has_permissions(manage_messages=True)
    async def pagination_add(
        self, ctx: Context, message: Message, *, embed_code: EmbedConverter
    ):
        if not (
            paginator := await self.bot.db.fetchrow(
                """SELECT * FROM pagination WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
                ctx.guild.id,
                message.channel.id,
                message.id,
            )
        ):
            raise CommandError("That message isn't a paginator")
        paginator.pages.append(embed_code)
        await self.bot.db.execute(
            """UPDATE pagination SET pages = $1 WHERE WHERE guild_id = $2 AND channel_id = $3 AND message_id = $$""",
            paginator.pages,
            ctx.guild.id,
            message.channel.id,
            message.id,
        )
        return await ctx.success("Added that page")

    @pagination.command(
        name="update", description="Update an existing page on pagination embed"
    )
    @has_permissions(manage_messages=True)
    async def pagination_update(
        self, ctx: Context, message: Message, id: int, *, embed_code: EmbedConverter
    ):
        if not (
            paginator := await self.bot.db.fetchrow(
                """SELECT * FROM pagination WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
                ctx.guild.id,
                message.channel.id,
                message.id,
            )
        ):
            raise CommandError("That message isn't a paginator")
        try:
            paginator.pages[id - 1 if id > 0 else id] = embed_code
        except Exception:
            raise CommandError("That page doesn't exist")
        if paginator.current_page == id - 1 if id > 0 else id:
            self.bot.dispatch(
                "paginator_update", message, paginator, id - 1 if id > 0 else id
            )
        await self.bot.db.execute(
            """UPDATE pagination SET pages = $1 WHERE WHERE guild_id = $2 AND channel_id = $3 AND message_id = $$""",
            paginator.pages,
            ctx.guild.id,
            message.channel.id,
            message.id,
        )
        return await ctx.success("Updated that page")

    @pagination.command(
        name="reset", description="Remove every existing pagination in guild"
    )
    @has_permissions(administrator=True)
    async def pagination_reset(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM pagination WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("Reset pagination in this guild")

    @pagination.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View all existing pagination embeds",
    )
    @has_permissions(manage_messages=True)
    async def pagination_list(self, ctx: Context):
        if not (
            paginators := await self.bot.db.fetch(
                """SELECT * FROM pagination WHERE guild_id = $1""", ctx.guild.id
            )
        ):
            raise CommandError("No **paginators** have been setup")
        embed = Embed(title="Pagination Embeds").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = []
        i = 0

        def get_paginator(record: Record) -> str:
            return f"[{record.message_id}](https://discordapp.com/channels/{record.guild_id}/{record.channel_id}/{record.message_id})"

        def get_user(user_id: int) -> str:
            return f"<@!{user_id}>"

        for paginator in paginators:
            i += 1
            rows.append(
                f"`{i}` {get_paginator(paginator)} - {get_user(paginator.creator_id)} (`{len(paginator.pages)}`)"
            )

        if not rows:
            raise CommandError("No **paginators** have been setup")
        return await ctx.paginate(embed, rows)

    @pagination.command(
        name="restorereactions",
        description="Restore reactions to an existing pagination",
    )
    @has_permissions(manage_messages=True)
    async def pagination_restorereactions(self, ctx: Context, message: Message):
        if not (
            paginator := await self.bot.db.fetchrow(
                """SELECT * FROM pagination WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
                ctx.guild.id,
                message.channel.id,
                message.id,
            )
        ):
            raise CommandError("That message isn't a paginator")
        await message.add_reaction(":arrow_left:")
        await message.add_reaction(":arrow_right:")
        return await ctx.message.add_reaction(":white_check_mark:")

    @pagination.command(
        name="set", description="Set up an existing embed to be paginated"
    )
    @has_permissions(manage_messages=True)
    async def pagination_set(self, ctx: Context, message: Message):
        try:
            new_embed = message.embeds[0]
            code = embed_to_code(new_embed, message.content)
            new_embed.set_footer(text="Page 1 of 1")
            await message.edit(embed=new_embed)
        except Exception:
            raise CommandError("I cannot edit that message")
        await self.bot.db.execute(
            """INSERT INTO pagination (guild_id, message_id, channel_id, creator_id, pages) VALUES($1, $2, $3, $4, $5)""",
            ctx.guild.id,
            message.id,
            message.channel.id,
            ctx.author.id,
            [code],
        )
        return await ctx.success(
            f"Set [`{message.id}`]({message.jump_url}) as a **pagination embed**"
        )

    @pagination.command(name="delete", description="Delete a pagination embed entirely")
    @has_permissions(manage_messages=True)
    async def pagination_delete(self, ctx: Context, message: Message):
        if not (
            paginator := await self.bot.db.fetchrow(
                """SELECT * FROM pagination WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
                ctx.guild.id,
                message.channel.id,
                message.id,
            )
        ):
            raise CommandError("That message isn't a paginator")
        await self.bot.db.execute(
            """DELETE FROM pagination WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
            ctx.guild.id,
            message.channel.id,
            message.id,
        )
        return await ctx.success(
            f"Deleted [`{message.id}`]({message.jump_url}) from the **pagination embeds**"
        )

    @pagination.command(
        name="remove", description="Remove a page from a pagination embed"
    )
    @has_permissions(manage_messages=True)
    async def pagination_remove(self, ctx: Context, message: Message, id: int):
        if not (
            paginator := await self.bot.db.fetchrow(
                """SELECT * FROM pagination WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
                ctx.guild.id,
                message.channel.id,
                message.id,
            )
        ):
            raise CommandError("That message isn't a paginator")
        try:
            paginator.pages.pop(id - 1 if id > 0 else id)
        except IndexError:
            raise CommandError("That page doesn't exist")
        if paginator.current_page == id - 1 if id > 0 else id:
            self.bot.dispatch(
                "paginator_update", message, paginator, id - 1 if id > 0 else id
            )
        return await ctx.success(
            f"Removed page **{id}** from [`{message.id}`]({message.jump_url})"
        )

    @group(
        name="enablecommand",
        description="Enable a previously disabled command in a channel",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def enablecommand(
        self,
        ctx: Context,
        channel_or_member: Union[TextChannel, Member],
        *,
        command: CommandConverter,
    ):
        if not (
            data := await self.bot.db.fetchrow(
                """SELECT * FROM disabled_commands WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                command.qualified_name,
            )
        ):
            raise CommandError(
                f"command `{command.qualified_name}` hasn't been disabled anywhere"
            )
        i = data.object_ids.index(channel_or_member.id)
        object_ids = data.object_ids
        object_types = data.object_types
        object_ids.pop(i)
        object_types.pop(i)
        await self.bot.db.execute(
            """UPDATE disabled_commands SET object_ids = $1, object_types = $2 WHERE guild_id = $3 AND command = $4""",
            object_types,
            object_types,
            ctx.guild.id,
            command.qualified_name,
        )
        return await ctx.success(
            f"**Enabled** command `{command.qualified_name}` for {channel_or_member.mention}"
        )

    @enablecommand.command(name="all", description="Enable a command in every channel")
    @has_permissions(manage_channels=True)
    async def enablecommand_all(self, ctx: Context, *, command: CommandConverter):
        if not (
            data := await self.bot.db.fetchrow(
                """SELECT * FROM disabled_commands WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                command.qualified_name,
            )
        ):
            raise CommandError(
                f"command `{command.qualified_name}` hasn't been disabled anywhere"
            )
        object_ids = data.object_ids
        object_types = data.object_types
        for channel in ctx.guild.channels:
            try:
                i = object_ids.index(channel.id)
                object_ids.pop(i)
                object_types.pop(i)
            except Exception:
                pass
            await self.bot.db.execute(
                """UPDATE disabled_commands SET object_ids = $1, object_types = $2 WHERE guild_id = $3 AND command = $4""",
                object_types,
                object_types,
                ctx.guild.id,
                command.qualified_name,
            )
            return await ctx.success(
                f"**Enabled** command `{command.qualified_name}` for **all channels**"
            )

    @command(
        name="copydisabled",
        description="Copy disabled modules, events, filters and commands to another channel",
        example=",copydisabled #text",
    )
    @has_permissions(manage_channels=True)
    async def copydisabled(self, ctx: Context, *, channel: TextChannel):
        pass

    @group(
        name="disablecommand",
        description="Disable a command in a channel",
        invoke_without_command=True,
        example=",disablecommand @jon ping",
    )
    @has_permissions(manage_channels=True)
    async def disablecommand(
        self,
        ctx: Context,
        channel_or_member: Union[TextChannel, Member],
        *,
        command: CommandConverter,
    ):
        if data := await self.bot.db.fetchrow(
            """SELECT * FROM disabled_commands WHERE guild_id = $1 AND command = $2""",
            ctx.guild.id,
            command.qualified_name,
        ):
            object_ids = data.object_ids
            if channel_or_member.id in object_ids:
                raise CommandError(
                    f"{channel_or_member.mention} is already incapable of using `{command.qualified_name}`"
                )
            object_types = data.object_types
            object_ids.append(channel_or_member.id)
            object_types.append(
                "channel" if isinstance(channel_or_member, TextChannel) else "member"
            )
            await self.bot.db.execute(
                """UPDATE disabled_commands SET object_ids = $1, object_types = $2 WHERE guild_id = $3 AND command = $4""",
                object_types,
                object_types,
                ctx.guild.id,
                command.qualified_name,
            )
        else:
            await self.bot.db.execute(
                """INSERT INTO disabled_commands (guild_id, command, object_ids, object_types) VALUES($1, $2, $3, $4)""",
                ctx.guild.id,
                command.qualified_name,
                [channel_or_member.id],
                ["channel" if isinstance(channel_or_member, TextChannel) else "member"],
            )
        return await ctx.success(
            f"**Enabled** command `{command.qualified_name}` for {channel_or_member.mention}"
        )

    @disablecommand.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of disabled commands in guild",
    )
    @has_permissions(manage_channels=True)
    async def disablecommand_list(self, ctx: Context):
        if not (
            data := await self.bot.db.fetch(
                """SELECT object_ids, object_types, command FROM disabled_commands WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No commands have been **DISABLED**")
        rows = []

        def get_object(r: int):
            if member := ctx.guild.get_member(r):
                return member
            elif channel := ctx.guild.get_channel(r):
                return channel
            return None

        for row in data:
            for r in data.object_ids:
                if not (obj := get_object(r)):
                    continue
                rows.append(f"**{row.command}** - {obj.mention}")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        return await ctx.paginate(
            Embed(color=self.bot.color, title="Disabled Commands").set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            )
        )

    @disablecommand.command(name="all", description="", example="")
    @has_permissions(manage_channels=True)
    async def disablecommand_all(self, ctx: Context, *, command: CommandConverter):
        if data := await self.bot.db.fetchrow(
            """SELECT * FROM disabled_commands WHERE guild_id = $1 AND command = $2""",
            ctx.guild.id,
            command.qualified_name,
        ):
            object_ids = data.object_ids
            object_types = data.object_types
            to_append = [
                c.id for c in ctx.guild.text_channels if c.id not in object_ids
            ]
            object_types.extend(["channel"] * len(to_append))
            await self.bot.db.execute(
                """UPDATE disabled_commands SET object_ids = $1, object_types = $2 WHERE guild_id = $3 AND command = $4""",
                object_ids,
                object_types,
                ctx.guild.id,
                command.qualified_name,
            )
        else:
            to_append = [c.id for c in ctx.guild.text_channels]
            await self.bot.db.execute(
                """INSERT INTO disabled_commands (guild_id, command, object_ids, object_types) VALUES($1, $2, $3, $4)""",
                ctx.guild.id,
                command.qualified_name,
                to_append,
                ["channel"] * len(to_append),
            )

    @group(
        name="enableevent",
        description="Enable a bot event in a channel",
        example=",enableevent repost #text",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def enableevent(
        self, ctx: Context, event: EventConverter, channel: TextChannel
    ):
        if not (
            channel_ids := await self.bot.db.fetchval(
                """SELECT channel_ids FROM disabled_events WHERE guild_id = $1 AND event = $2""",
                ctx.guild.id,
                event,
            )
        ):
            raise CommandError("that event hasn't been **DISABLED** anywhere")
        if channel.id not in channel_ids:
            raise CommandError(f"That event hasn't been disabled in {channel.mention}")
        channel_ids.remove(channel.id)
        await self.bot.db.execute(
            """UPDATE disabled_events SET channel_ids = $1 WHERE guild_id = $2 AND event = $3""",
            channel_ids,
            ctx.guild.id,
            event,
        )
        return await ctx.success(
            f"**Enabled** bot event `{EVENT_MAPPING[event][0]}` in channel {channel.mention}"
        )

    @enableevent.command(
        name="all",
        description="Enables a bot event in every channel",
        example=",enableevent all repost",
    )
    @has_permissions(manage_channels=True)
    async def enableevent_all(self, ctx: Context, event: EventConverter):
        await self.bot.db.execute(
            """DELETE FROM disabled_events WHERE guild_id = $1 AND event = $2""",
            ctx.guild.id,
            event,
        )
        return await ctx.success(
            f"**Enabled** bot event `{EVENT_MAPPING[event][0]}` in **all channels**"
        )

    @group(
        name="disableevent",
        description="Disable a bot event in a channel",
        example=",disableevent repost #text",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def disableevent(
        self, ctx: Context, event: EventConverter, *, channel: TextChannel
    ):
        if row := await self.bot.db.fetchrow(
            """SELECT * FROM disabled_events WHERE guild_id = $1 AND event = $2""",
            ctx.guild.id,
            event,
        ):
            channel_ids = row.channel_ids
            channel_ids.append(channel.id)
            await self.bot.db.execute(
                """UPDATE disabled_events SET channel_ids = $1 WHERE guild_id = $2 AND event = $3""",
                channel_ids,
                ctx.guild.id,
                event,
            )
        else:
            await self.bot.db.execute(
                """INSERT INTO disabled_events (guild_id, event, channel_ids) VALUES($1, $2, $3)""",
                ctx.guild.id,
                event,
                [channel.id],
            )
        return await ctx.success(
            f"**Disabled** bot event `{EVENT_MAPPING[event][0]}` in channel {channel.mention}"
        )

    @disableevent.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of disabled events in guild",
    )
    @has_permissions(manage_channels=True)
    async def disableevent_list(self, ctx: Context):
        rows = []
        for row in await self.bot.db.fetch(
            """SELECT event, channel_ids FROM disabled_events WHERE guild_id = $1""",
            ctx.guild.id,
        ):
            event_name = EVENT_MAPPING[row.event][0]
            for channel in row.channel_ids:
                if channel_object := ctx.guild.get_channel(channel):
                    rows.append(f"'{event_name}' ({channel_object.mention})")
        if len(rows) == 0:
            raise CommandError("No events have been disabled")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        return await ctx.paginate(
            Embed(title="Disabled Bot Events", color=self.bot.color).set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            ),
            rows,
        )

    @disableevent.command(
        name="all", description="", example=",disableevent all member_join"
    )
    @has_permissions(manage_channels=True)
    async def disableevent_all(self, ctx: Context, event: EventConverter):
        await self.bot.db.execute(
            """INSERT INTO disabled_events (guild_id, event, channel_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, event) DO UPDATE SET channel_ids = excluded.channel_ids""",
            ctx.guild.id,
            event,
            [c.id for c in ctx.guild.channels],
        )
        return await ctx.success(
            f"**Disabled** bot event `{EVENT_MAPPING[event][0]}` in **all channels**"
        )

    @group(
        name="enablemodule",
        description="Enable a module in a channel",
        example=",enablemodule servers #text",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def enablemodule(
        self, ctx: Context, module: ModuleConverter, channel: TextChannel
    ):
        if not (
            channel_ids := await self.bot.db.fetchval(
                """SELECT channel_ids FROM disabled_modules WHERE guild_id = $1 AND event = $2""",
                ctx.guild.id,
                module,
            )
        ):
            raise CommandError("that module hasn't been **DISABLED** anywhere")
        if channel.id not in channel_ids:
            raise CommandError(f"that module hasn't been disabled in {channel.mention}")
        channel_ids.remove(channel.id)
        await self.bot.db.execute(
            """UPDATE disabled_modules SET channel_ids = $1 WHERE guild_id = $2 AND event = $3""",
            channel_ids,
            ctx.guild.id,
            module,
        )
        return await ctx.success(
            f"**Enabled** bot module `{module.replace('_', ' ')}` in channel {channel.mention}"
        )

    @enablemodule.command(
        name="all",
        description="Enables a module in every channel",
        example=",enablemodule all servers",
    )
    @has_permissions(manage_channels=True)
    async def enablemodule_all(self, ctx: Context, *, module: ModuleConverter):
        await self.bot.db.execute(
            """DELETE FROM disabled_modules WHERE guild_id = $1 AND module = $2""",
            ctx.guild.id,
            module,
        )
        return await ctx.success(
            f"**Enabled** bot module `{module.replace('_', ' ')}` in **all channels**"
        )

    @group(
        name="disablemodule",
        description="Disable a bot module in a channel",
        example=",disablemodule servers #text",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def disablemodule(
        self, ctx: Context, module: ModuleConverter, channel: TextChannel
    ):
        if row := await self.bot.db.fetchrow(
            """SELECT * FROM disabled_modules WHERE guild_id = $1 AND event = $2""",
            ctx.guild.id,
            module,
        ):
            channel_ids = row.channel_ids
            channel_ids.append(channel.id)
            await self.bot.db.execute(
                """UPDATE disabled_modules SET channel_ids = $1 WHERE guild_id = $2 AND event = $3""",
                channel_ids,
                ctx.guild.id,
                module,
            )
        else:
            await self.bot.db.execute(
                """INSERT INTO disabled_modules (guild_id, event, channel_ids) VALUES($1, $2, $3)""",
                ctx.guild.id,
                module,
                [channel.id],
            )
        return await ctx.success(
            f"**Disabled** bot module `{module.replace('_', ' ')}` in channel {channel.mention}"
        )

    @disablemodule.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of disabled modules in guild",
    )
    @has_permissions(manage_channels=True)
    async def disablemodule_list(self, ctx: Context):
        if not (
            data := await self.bot.db.fetch(
                """SELECT module, channel_ids FROM disabled_modules WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No modules have been **disabled**")
        rows = []
        for row in data:
            module = row.module
            for channel_id in row.channel_ids:
                if not (channel := ctx.guild.get_channel(channel_id)):
                    continue
                rows.append(f"**{module.replace('_', ' ')}** - ({channel.mention})")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        return await ctx.paginate(
            Embed(color=self.bot.color, title="Disabled Modules").set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            ),
            rows,
        )

    @disablemodule.command(
        name="all",
        description="Disable a module in every channel",
        example=",disablemodule all servers",
    )
    @has_permissions(manage_channels=True)
    async def disablemodule_all(self, ctx: Context, module: ModuleConverter):
        if data := await self.bot.db.fetchrow(
            """SELECT * FROM disabled_modules WHERE guild_id = $1 AND module = $2""",
            ctx.guild.id,
            module,
        ):
            to_append = [
                c.id for c in ctx.guild.text_channels if c.id not in data.channel_ids
            ]
            data.channel_ids.extend(to_append)
            await self.bot.db.execute(
                """UPDATE disabled_modules SET channel_ids = $1 WHERE guild_id = $2 AND module = $3""",
                data.channel_ids,
                ctx.guild.id,
                module,
            )
        else:
            to_append = [c.id for c in ctx.guild.text_channels]
            await self.bot.db.execute(
                """INSERT INTO disabled_modules (guild_id, module, channel_ids) VALUES($1, $2, $3)""",
                ctx.guild.id,
                module,
                to_append,
            )

    @group(
        name="ignore", description="No description given", invoke_without_command=True
    )
    @has_permissions(administrator=True)
    async def ignore(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @ignore.command(
        name="remove",
        description="Remove ignoring for a member or channel",
        example=",ignore remove @jon",
    )
    @has_permissions(administrator=True)
    async def ignore_remove(
        self, ctx: Context, *, member_or_channel: Union[Member, TextChannel]
    ):
        if not (
            await self.bot.db.fetchrow(
                """SELECT * FROM ignored WHERE guild_id = $1 AND object_id = $2""",
                ctx.guild.id,
                member_or_channel.id,
            )
        ):
            raise CommandError(f"{member_or_channel.mention} has not been ignored")
        await self.bot.db.execute(
            """DELETE FROM ignored WHERE guild_id = $1 AND object_id = $2""",
            ctx.guild.id,
            member_or_channel.id,
        )
        return await ctx.success(
            f"{member_or_channel.mention} is no longer being ignored"
        )

    @ignore.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of ignored members or channels",
    )
    @has_permissions(administrator=True)
    async def ignore_list(self, ctx: Context):
        if not (
            data := await self.bot.db.fetch(
                """SELECT object_id FROM ignored WHERE guild_id = $1""", ctx.guild.id
            )
        ):
            raise CommandError("No member's or channel's have been ignored")

        def get_object(r: int):
            if member := ctx.guild.get_member(r):
                return member
            elif channel := ctx.guild.get_channel(r):
                return channel
            return None

        rows = []
        for record in data:
            if obj := get_object(record.object_id):
                rows.append(f"{obj.mention}")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        return await ctx.paginate(
            Embed(color=self.bot.color, title="Ignore List").set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            ),
            rows,
        )

    @ignore.command(
        name="add", description="Ignore a member or channel", example=",ignore add @jon"
    )
    @has_permissions(administrator=True)
    async def ignore_add(
        self, ctx: Context, *, member_or_channel: Union[Member, TextChannel]
    ):
        await self.bot.db.execute(
            """INSERT INTO ignored (guild_id, object_id, object_type) VALUES($1, $2, $3) ON CONFLICT(guild_id, object_id) DO NOTHING""",
            ctx.guild.id,
            member_or_channel.id,
            "channel" if isinstance(member_or_channel, TextChannel) else "member",
        )
        return await ctx.success(f"successfully ignoring {member_or_channel.mention}")

    @group(
        name="autoresponder",
        aliases=["autoresponders", "ars", "ar"],
        description="Set up automatic replies to messages that match a trigger",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def autoresponder(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @autoresponder.command(
        name="role",
        description="Set exclusive permission for an autoresponder to a role",
        example=",autoresponder role @boosters ignore sup",
    )
    @has_permissions(manage_channels=True)
    async def autoresponder_role(
        self, ctx: Context, role: Role, action: AutoResponderAction, *, trigger: str
    ):
        if action == "deny":
            role_ids = await self.bot.db.fetchval(
                """SELECT denied_role_ids FROM auto_responders WHERE guild_id = $1 AND trigger = $2""",
                ctx.guild.id,
                trigger,
            )
            if not role_ids:
                role_ids = [role.id]
            else:
                role_ids.append(role.id)
            query = "INSERT INTO auto_responders (guild_id, trigger, denied_role_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, trigger) DO UPDATE SET denied_role_ids = excluded.denied_role_ids"
            args = (ctx.guild.id, trigger, role_ids)
        else:
            data = await self.bot.db.fetch(
                """SELECT denied_role_ids, allowed_role_ids FROM auto_responders WHERE guild_id = $1 AND trigger = $2""",
                ctx.guild.id,
                trigger,
            )
            if data.denied_role_ids:
                if role.id in data.denied_role_ids:
                    data.denied_role_ids.remove(role.id)
            role_ids = data.allowed_role_ids or []
            role_ids.append(role.id)
            query = "INSERT INTO auto_responders (guild_id, trigger, allowed_role_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, trigger) DO UPDATE SET allowed_role_ids = excluded.allowed_role_ids"
            args = (ctx.guild.id, trigger, role_ids)
        await self.bot.db.execute(query, *args)
        return await ctx.success(
            f"Added **exclusive** access for {role.mention} to `{trigger}`"
        )

    @autoresponder.command(
        name="channel",
        description="Set exclusive permission for an autoresponder to a channel",
        example=",autoresponder channel #text deny sup",
    )
    @has_permissions(manage_channels=True)
    async def autoresponder_channel(
        self,
        ctx: Context,
        channel: TextChannel,
        action: AutoResponderAction,
        *,
        trigger: str,
    ):
        if action == "deny":
            channel_ids = await self.bot.db.fetchval(
                """SELECT denied_channel_ids FROM auto_responders WHERE guild_id = $1 AND trigger = $2""",
                ctx.guild.id,
                trigger,
            )
            if not channel_ids:
                channel_ids = [channel.id]
            else:
                channel_ids.append(channel.id)
            query = "INSERT INTO auto_responders (guild_id, trigger, denied_channel_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, trigger) DO UPDATE SET denied_channel_ids = excluded.denied_channel_ids"
            args = (ctx.guild.id, trigger, channel_ids)
        else:
            data = await self.bot.db.fetch(
                """SELECT denied_channel_ids, allowed_channel_ids FROM auto_responders WHERE guild_id = $1 AND trigger = $2""",
                ctx.guild.id,
                trigger,
            )
            if data.denied_channel_ids:
                if channel.id in data.denied_channel_ids:
                    data.denied_channel_ids.remove(channel.id)
            channel_ids = data.allowed_channel_ids or []
            channel_ids.append(channel.id)
            query = "INSERT INTO auto_responders (guild_id, trigger, allowed_channel_ids) VALUES($1, $2, $3) ON CONFLICT(guild_id, trigger) DO UPDATE SET allowed_channel_ids = excluded.allowed_channel_ids"
            args = (ctx.guild.id, trigger, channel_ids)
        await self.bot.db.execute(query, *args)
        return await ctx.success(
            f"Added **exclusive** access for {channel.mention} to `{trigger}`"
        )

    @autoresponder.command(
        name="reset", description="Remove every auto response", aliases=["clear"]
    )
    @has_permissions(manage_channels=True)
    async def autoresponder_reset(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM auto_responders WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("successfully **reset** auto responders")

    @autoresponder.command(
        name="variables", description="View a list of available variables"
    )
    @has_permissions(manage_channels=True)
    async def autoresponder_variables(self, ctx: Context):
        pass

    @autoresponder.command(
        name="update",
        description="Update a reply for a trigger word",
        example=",autoresponder update Hi, Goodbye",
        usage=",autoresponder update (trigger), (response)",
    )
    @has_permissions(manage_channels=True)
    async def autoresponder_update(self, ctx: Context, *, args: str):
        args = [a.lstrip().rstrip() for a in args.split(",")]
        if len(args) == 1:
            args = [a.lstrip().rstrip() for a in args.split(" ")]
        try:
            trigger, response = args
        except Exception:
            raise CommandError(
                "Unexpected amount of arguments provided, expected trigger, response"
            )
        await self.bot.db.execute(
            """UPDATE auto_responders SET response = $1 WHERE trigger = $2 AND guild_id = $3""",
            response,
            trigger,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**Set** the response of **{trigger}** to `{response}`"
        )

    @autoresponder.command(
        name="remove",
        aliases=["del", "delete", "d", "rem"],
        description="Remove a reply for a trigger word",
        example=",autoresponder remove Hi",
    )
    @has_permissions(manage_channels=True)
    async def autoresponder_remove(self, ctx: Context, *, trigger: str):
        await self.bot.db.execute(
            """DELETE FROM auto_responders WHERE trigger = $1 AND guild_id = $2""",
            trigger,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**Deleted** auto responder trigger under `{trigger}` if there was one"
        )

    @autoresponder.command(
        name="list",
        aliases=["view", "show", "ls"],
        description="View a list of auto-reply triggers in guild",
    )
    @has_permissions(manage_channels=True)
    async def autoresponder_list(self, ctx: Context):
        data = await self.bot.db.fetch(
            """SELECT trigger, strict FROM auto_responders WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if not data:
            raise CommandError("No Auto Responses found for this server")
        embed = Embed(title="Auto Responders").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = [
            f"`{i}` **{row.trigger}** (strict: `{'yes' if row.strict else 'no'}`)"
            for i, row in enumerate(data, start=1)
        ]
        return await ctx.paginate(embed, rows)

    @autoresponder.command(
        name="add",
        aliases=["a", "create", "c"],
        description="Create a reply for a trigger word",
        # flags = AutoResponderParameters
        parameters={
            "self_destruct": {
                "converter": int,
                "default": None,
            },
            "not_strict": {
                "no_value": True,
                "default": False,
            },
            "reply": {
                "no_value": True,
                "default": False,
            },
            "ignore_command_check": {
                "no_value": True,
                "default": False,
            },
        },
    )
    @has_permissions(manage_channels=True)
    async def autoresponder_add(self, ctx: Context, *, args: str):
        arguments = [a.lstrip().rstrip() for a in args.split(",", 1)]
        if len(arguments) == 1:
            arguments = [a.lstrip().rstrip() for a in args.split(" ", 1)]
        try:
            trigger, response = arguments
        except Exception:
            raise CommandError(
                "Unexpected amount of arguments provided, expected trigger, response"
            )
        self_destruct = ctx.parameters.get("self_destruct", None)
        strict = False if ctx.parameters.get("not_strict", True) else True
        reply = True if ctx.parameters.get("reply", False) else False
        ignore_command_check = (
            True if ctx.parameters.get("ignore_command_check") else False
        )

        await self.bot.db.execute(
            """
			INSERT INTO auto_responders (
				guild_id, trigger, response, strict, reply, self_destruct, ignore_command_checks
			) 
			VALUES ($1, $2, $3, $4, $5, $6, $7)
			ON CONFLICT (guild_id, trigger) 
			DO UPDATE SET 
				response = EXCLUDED.response,
				strict = EXCLUDED.strict,
				reply = EXCLUDED.reply,
				self_destruct = EXCLUDED.self_destruct,
				ignore_command_checks = EXCLUDED.ignore_command_checks;
			""",
            ctx.guild.id,
            trigger,
            response,
            strict,
            reply,
            self_destruct,
            ignore_command_check,
        )
        f = ""
        f += "(strict match)" if strict else "(non strict match)"
        f += "(reply)" if reply else ""
        f += "(ignore command check)" if ignore_command_check else ""
        f += (
            f"\nThis **autoresponder** will self-destruct after `{self_destruct} seconds`"
            if self_destruct
            else ""
        )
        return await ctx.success(
            f"**Added** auto responder for **{trigger}** with **a text response** {f}"
        )

    @group(
        name="imageonly",
        aliases=["imgonly", "ionly"],
        description="Set up image + caption only channels",
        invoke_without_command=True,
    )
    async def imageonly(self, ctx: Context):
        return await ctx.send_help()

    @imageonly.command(
        name="remove",
        aliases=["delete", "del", "d", "rem", "r"],
        description="Remove a gallery channel",
        example=",imageonly remove #img",
    )
    @has_permissions(manage_guild=True)
    async def imageonly_remove(self, ctx: Context, *, channel: TextChannel):
        await self.bot.db.execute(
            """DELETE FROM image_only WHERE guild_id = $1 AND channel_id = $2""",
            ctx.guild.id,
            channel.id,
        )
        return await ctx.success(
            f"successfully removed {channel.mention} from the **gallery**"
        )

    @imageonly.command(
        name="add",
        aliases=["a", "set", "create", "s", "c"],
        description="Add a gallery channel",
        example=",imageonly add #img",
    )
    @has_permissions(manage_guild=True)
    async def imageonly_add(self, ctx: Context, *, channel: TextChannel):
        await self.bot.db.execute(
            """INSERT INTO image_only (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT(guild_id, channel_id) DO NOTHING""",
            ctx.guild.id,
            channel.id,
        )
        return await ctx.success(
            f"successfully added {channel.mention} as a **gallery**"
        )

    @imageonly.command(
        name="list",
        aliases=["ls", "view", "show"],
        description="View all gallery channels",
    )
    @has_permissions(manage_guild=True)
    async def imageonly_list(self, ctx: Context):
        data = await self.bot.db.fetch(
            """SELECT channel_id FROM image_only WHERE guild_id = $1""", ctx.guild.id
        )

        deletion = []
        rows = []

        for row in data:
            if not (channel := ctx.guild.get_channel(row.channel_id)):
                deletion.append(row.channel_id)
                continue
            rows.append(f"{channel.mention} (`{row.channel_id}`)")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        embed = Embed(title="Image Only Channels").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(embed, rows)

    @group(
        name="filter",
        aliases=["automod"],
        description="View a variety of options to help clean chat",
        invoke_without_command=True,
    )
    async def filter_(self, ctx: Context):
        return await ctx.send_help()

    @filter_.command(name="reset", description="Reset all filtered words")
    @has_permissions(manage_guild=True)
    async def filter_reset(self, ctx: Context):
        automod = next(
            (
                a
                for a in await ctx.guild.fetch_automod_rules()
                if a.creator_id == self.bot.user.id and not a.trigger.regex_patterns
            ),
            None,
        )

        if not automod:
            raise CommandError("There's no words automod rule found")

        keyword_filter = automod.trigger.keyword_filter
        keyword_filter.clear()
        await automod.edit(
            trigger=AutoModTrigger(
                type=AutoModRuleTriggerType.keyword,
                keyword_filter=keyword_filter,
            ),
            reason=f"Automod rule reset by {ctx.author}",
        )
        return await ctx.success("successfully reset the filtered words")

    @filter_.group(
        name="caps",
        description="Delete messages that contain too many uppercase characters",
        example=",filter caps ",
    )
    @has_permissions(manage_guild=True)
    async def filter_caps(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, str]] = None,
        setting: Optional[Boolean] = False,
        *,
        flags: FilterFlags,
    ):
        if not channel:
            channel = "all"
        channels = (
            [channel.id]
            if isinstance(channel, TextChannel)
            else [c.id for c in ctx.guild.text_channels]
        )
        await self.bot.db.execute(
            """INSERT INTO moderation.caps (guild_id, channel_ids, threshold, action) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id) DO UPDATE SET channel_ids = excluded.channel_ids, threshold = excluded.threshold, action = excluded.action""",
            ctx.guild.id,
            channels,
            flags.threshold,
            flags.punishment,
        )
        return await ctx.success(
            f"successfully **{'ENABLED' if setting else 'DISABLED'}** the caps filter"
        )

    @filter_caps.group(
        name="exempt",
        aliases=["wl", "ex"],
        description="Exempt roles from the caps filter",
        example=",filter caps exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_caps_exempt(self, ctx: Context, *, roles: MultipleRoles):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.caps WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup caps filtering yet")
        rs = exempt.roles or []
        exempt = list(set(rs))

        for r in roles:
            role_id = r.id
            if role_id in exempt:
                exempt.remove(role_id)
            else:
                exempt.append(role_id)

        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )

        await self.bot.db.execute(
            """UPDATE moderation.caps SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )

        # Return success message
        return await ctx.success(
            f"Successfully made the following roles exempt: {human_join([r.mention for r in exempt_roles], final='and')}"
        )

    @filter_caps_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from caps filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_caps_exempt_list(self, ctx: Context):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.caps WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup caps filtering yet")
        if not exempt.roles:
            raise CommandError("No roles are exempted from the **caps** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt.roles),
            )
        )
        embed = Embed(title="Exempted roles for caps").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @filter_.group(
        name="spam",
        aliases=["antispam", "flood", "flooding"],
        description="Delete messages from users that send messages too fast",
        example=",filter spam all on --threshold 5",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_spam(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, str]] = "all",
        setting: Optional[Boolean] = True,
        *,
        flags: SpamFilterFlags,
    ):
        channels = (
            [channel.id]
            if isinstance(channel, TextChannel)
            else [c.id for c in ctx.guild.text_channels]
        )
        await self.bot.db.execute(
            """INSERT INTO moderation.caps (guild_id, channel_ids, threshold, action) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id) DO UPDATE SET channel_ids = excluded.channel_ids, threshold = excluded.threshold, action = excluded.action""",
            ctx.guild.id,
            channels,
            flags.threshold,
            flags.punishment,
        )
        return await ctx.success(
            f"{'ENABLED' if setting else 'DISABLED'} **spam** filter in {len(channels)}** {'channel' if len(channels) == 1 else 'channels'}. Punishment is set to {flags.punishment}. Threshold is set to **{flags.threshold}** messages in 5 seconds"
        )

    @filter_spam.group(
        name="exempt",
        aliases=["wl", "ex"],
        description="Exempt roles from the spam filter",
        example=",filter spam exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_spam_exempt(self, ctx: Context, *, roles: MultipleRoles):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.spam WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup spam filtering yet")
        rs = exempt.roles or []
        exempt = list(set(rs))

        for r in roles:
            role_id = r.id
            if role_id in exempt:
                exempt.remove(role_id)
            else:
                exempt.append(role_id)

        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )

        await self.bot.db.execute(
            """UPDATE moderation.spam SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )

        # Return success message
        return await ctx.success(
            f"Successfully made the following roles exempt: {human_join([r.mention for r in exempt_roles], final='and')}"
        )

    @filter_spam_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from spam filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_spam_exempt_list(self, ctx: Context):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.spam WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup spam filtering yet")
        if not exempt.roles:
            raise CommandError("No roles are exempted from the **spam** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt.roles),
            )
        )
        embed = Embed(title="Exempted roles for spam").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @filter_.command(
        name="add",
        aliases=["create", "set", "c", "a"],
        description="Add a filtered word",
        example=",filter add hitler",
    )
    @has_permissions(manage_guild=True)
    async def filter_add(self, ctx: Context, *, words: MultipleWords):
        if any(len(word) > 60 or len(word) < 1 for word in words):
            raise CommandError("word must be between 1 and 60 characters in length")
        automod = next(
            (
                a
                for a in await ctx.guild.fetch_automod_rules()
                if a.creator_id == self.bot.user.id and not a.trigger.regex_patterns
            ),
            None,
        )

        if not automod:
            actions = [
                AutoModRuleAction(
                    custom_message=f"Message blocked by {self.bot.user.name} for containing a blacklisted word"
                )
            ]
            if len(words) >= 1000:
                raise CommandError("You can only filter 1000 words")
            automod = await ctx.guild.create_automod_rule(
                name=f"{self.bot.user.name} - words",
                event_type=AutoModRuleEventType.message_send,
                trigger=AutoModTrigger(
                    type=AutoModRuleTriggerType.keyword,
                    keyword_filter=[f"*{word}*" for word in words],
                ),
                enabled=True,
                actions=actions,
                reason=f"Automod rule enabled by {ctx.author}",
            )
        else:
            keyword_filter = automod.trigger.keyword_filter
            keyword_filter.extend([f"*{word}*" for word in words])
            if len(keyword_filter) >= 1000:
                raise CommandError(
                    "You have reached the maximum number of words that can be filtered"
                )
            await automod.edit(
                trigger=AutoModTrigger(
                    type=AutoModRuleTriggerType.keyword,
                    keyword_filter=keyword_filter,
                ),
                reason=f"Automod rule edited by {ctx.author}",
            )

        return await ctx.success(
            f"Added the following words to the blacklist {human_join(words, final='and', markdown='`')}"
        )

    @filter_.group(
        name="links",
        aliases=["urls"],
        description="Delete any message that contains a link",
        example=",filter links all on",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_links(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, str]] = "all",
        setting: Optional[Boolean] = True,
        *,
        flags: FilterFlags,
    ):
        channels = (
            [channel.id]
            if isinstance(channel, TextChannel)
            else [c.id for c in ctx.guild.text_channels]
        )
        await self.bot.db.execute(
            """INSERT INTO moderation.links (guild_id, channel_ids, action) VALUES($1, $2, $3) ON CONFLICT(guild_id) DO UPDATE SET channel_ids = excluded.channel_ids, action = excluded.action""",
            ctx.guild.id,
            channels,
            flags.punishment,
        )
        return await ctx.success(
            f"{'ENABLED' if setting else 'DISABLED'} **link** filter in {len(channels)}** {'channel' if len(channels) == 1 else 'channels'}. Punishment is set to {flags.punishment}"
        )

    @filter_links.group(
        name="exempt",
        aliases=["ex"],
        description="Exempt roles from the links filter",
        example=",filter links exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_links_exempt(self, ctx: Context, *, roles: MultipleRoles):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.links WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup links filtering yet")
        rs = exempt.roles or []
        exempt = list(set(rs))

        for r in roles:
            role_id = r.id
            if role_id in exempt:
                exempt.remove(role_id)
            else:
                exempt.append(role_id)

        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )

        await self.bot.db.execute(
            """UPDATE moderation.links SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )

        # Return success message
        return await ctx.success(
            f"Successfully made the following roles exempt: {human_join([r.mention for r in exempt_roles], final='and')}"
        )

    @filter_links_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from links filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_links_exempt_list(self, ctx: Context):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.links WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup links filtering yet")
        if not exempt.roles:
            raise CommandError("No roles are exempted from the **links** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt.roles),
            )
        )
        embed = Embed(title="Exempted roles for links").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @filter_links.command(
        name="whitelist",
        description="Whitelist links from the links filter",
        aliases=["wl"],
        example=",filter links whitelist https://...",
    )
    @has_permissions(manage_guild=True)
    async def filter_links_whitelist(self, ctx: Context, *, invite: MultipleLinks):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, whitelist FROM moderation.links WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup links filtering yet")
        whitelist = list(set(exempt.whitelist or []) + [invite_ for invite_ in invite])
        await self.bot.db.execute(
            """UPDATE moderation.links SET whitelist = $1 WHERE guild_id = $2""",
            whitelist,
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully whitelisted the following links {human_join(invite, final='and')}"
        )

    @filter_.group(
        name="invites",
        aliases=["invite", "invs", "inv"],
        description="Delete any message that contains a server invite",
        example=",filter invites all on",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_invites(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, str]] = "all",
        setting: Optional[Boolean] = True,
        *,
        flags: FilterFlags,
    ):
        channels = (
            [channel.id]
            if isinstance(channel, TextChannel)
            else [c.id for c in ctx.guild.text_channels]
        )
        await self.bot.db.execute(
            """INSERT INTO moderation.invites (guild_id, channel_ids, action) VALUES($1, $2, $3) ON CONFLICT(guild_id) DO UPDATE SET channel_ids = excluded.channel_ids, action = excluded.action""",
            ctx.guild.id,
            channels,
            flags.punishment,
        )
        return await ctx.success(
            f"{'ENABLED' if setting else 'DISABLED'} **link** filter in {len(channels)}** {'channel' if len(channels) == 1 else 'channels'}. Punishment is set to {flags.punishment}"
        )

    @filter_invites.group(
        name="exempt",
        aliases=["ex"],
        description="Exempt roles from the invites filter",
        example=",filter invites exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_invites_exempt(self, ctx: Context, *, roles: MultipleRoles):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.invites WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not set up invites filtering yet")

        rs = exempt.roles or []
        exempt = list(set(rs))

        for r in roles:
            role_id = r.id
            if role_id in exempt:
                exempt.remove(role_id)
            else:
                exempt.append(role_id)

        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )

        await self.bot.db.execute(
            """UPDATE moderation.invites SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )

        # Return success message
        return await ctx.success(
            f"Successfully made the following roles exempt: {human_join([r.mention for r in exempt_roles], final='and')}"
        )

    @filter_invites.command(
        name="whitelist",
        description="Whitelist links from the links filter",
        aliases=["wl"],
        example=",filter invites whitelist rival",
    )
    @has_permissions(manage_guild=True)
    async def filter_invites_whitelist(self, ctx: Context, *, invite: MultipleInvites):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, whitelist FROM moderation.invites WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup invites filtering yet")
        whitelist = list(set(exempt.whitelist or []) + [invite_ for invite_ in invite])
        await self.bot.db.execute(
            """UPDATE moderation.invites SET whitelist = $1 WHERE guild_id = $2""",
            whitelist,
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully whitelisted the following invites {human_join(invite, final='and')}"
        )

    @filter_invites_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from invites filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_invites_exempt_list(self, ctx: Context):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.invites WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup invites filtering yet")
        if not exempt.roles:
            raise CommandError("No roles are exempted from the **invites** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt.roles),
            )
        )
        embed = Embed(title="Exempted roles for invites").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @filter_.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of filtered words in guild",
    )
    @has_permissions(manage_guild=True)
    async def filter_list(self, ctx: Context):
        automod = next(
            (
                a
                for a in await ctx.guild.fetch_automod_rules()
                if a.creator_id == self.bot.user.id and not a.trigger.regex_patterns
            ),
            None,
        )
        if not automod:
            raise CommandError("You have not setup a **word filter** yet")
        words = [w.replace("*", "") for w in automod.trigger.keyword_filter]
        embed = Embed(title="Filtered words").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed, [f"`{i}` {word}" for i, word in enumerate(words, start=1)]
        )

    @filter_.command(
        name="remove",
        aliases=["del", "delete", "d", "r", "rem"],
        description="",
        example="",
    )
    @has_permissions(manage_guild=True)
    async def filter_remove(self, ctx: Context, *, words: MultipleWords):
        automod = next(
            (
                a
                for a in await ctx.guild.fetch_automod_rules()
                if a.creator_id == self.bot.user.id and not a.trigger.regex_patterns
            ),
            None,
        )
        if not automod:
            raise CommandError("You have not setup a **word filter** yet")
        filtered_words = [w for w in automod.trigger.keyword_filter]
        removed = []
        for word in words:
            if f"*{word.lower()}*" in filtered_words:
                filtered_words.remove(f"*{word.lower()}*")
                removed.append(word.lower())

        await automod.edit(
            trigger=AutoModTrigger(
                type=AutoModRuleTriggerType.keyword,
                keyword_filter=filtered_words,
            ),
            reason=f"Automod rule edited by {ctx.author}",
        )
        return await ctx.success(
            f"successfully **removed** the following {'word' if len(words) == 1 else {'words'}} {human_join(words, final='and')}"
        )

    @filter_.group(
        name="spoilers",
        description="Delete any message exceeding the threshold for spoilers",
        example="filter spoilers #general on --threshold 2",
    )
    @has_permissions(manage_guild=True)
    async def filter_spoilers(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, str]] = "all",
        setting: Optional[Boolean] = True,
        *,
        flags: SpamFilterFlags,
    ):
        channels = (
            [channel.id]
            if isinstance(channel, TextChannel)
            else [c.id for c in ctx.guild.text_channels]
        )
        await self.bot.db.execute(
            """INSERT INTO moderation.spoilers (guild_id, channel_ids, threshold, action) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id) DO UPDATE SET channel_ids = excluded.channel_ids, threshold = excluded.threshold, action = excluded.action""",
            ctx.guild.id,
            channels,
            flags.threshold,
            flags.punishment,
        )
        return await ctx.success(
            f"{'ENABLED' if setting else 'DISABLED'} **spoiler** filter in {len(channels)}** {'channel' if len(channels) == 1 else 'channels'}. Punishment is set to **{flags.punishment}**. Threshold is set to **{flags.threshold}**"
        )

    @filter_spoilers.group(
        name="exempt",
        aliases=["wl", "ex"],
        description="Exempt roles from the spoilers filter",
        example=",filter spoilers exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_spoilers_exempt(self, ctx: Context, *, roles: MultipleRoles):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.spoilers WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup spoilers filtering yet")
        rs = exempt.roles or []
        exempt = list(set(rs + [r.id for r in roles]))
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )
        await self.bot.db.execute(
            """UPDATE moderation.spoilers SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully made the following roles exempt {human_join(exempt_roles, final='and')}"
        )

    @filter_spoilers_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from spoilers filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_spoilers_exempt_list(self, ctx: Context):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.spoilers WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup spoilers filtering yet")
        if not exempt.roles:
            raise CommandError("No roles are exempted from the **spoilers** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt.roles),
            )
        )
        embed = Embed(title="Exempted roles for spoilers").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @filter_.group(
        name="musicfiles",
        description="Delete any message that contains a music file",
        example="filter musicfiles #general on",
    )
    @has_permissions(manage_guild=True)
    async def filter_musicfile(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, str]] = "all",
        setting: Optional[Boolean] = True,
        *,
        flags: SpamFilterFlags,
    ):
        channels = (
            [channel.id]
            if isinstance(channel, TextChannel)
            else [c.id for c in ctx.guild.text_channels]
        )
        await self.bot.db.execute(
            """INSERT INTO moderation.spoilers (guild_id, channel_ids, action) VALUES($1, $2, $3) ON CONFLICT(guild_id) DO UPDATE SET channel_ids = excluded.channel_ids, action = excluded.action""",
            ctx.guild.id,
            channels,
            flags.punishment,
        )
        return await ctx.success(
            f"{'ENABLED' if setting else 'DISABLED'} **spoiler** filter in {len(channels)}** {'channel' if len(channels) == 1 else 'channels'}. Punishment is set to **{flags.punishment}**"
        )

    @filter_musicfile.group(
        name="exempt",
        aliases=["wl", "ex"],
        description="Exempt roles from the musicfile filter",
        example=",filter musicfile exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_musicfile_exempt(self, ctx: Context, *, roles: MultipleRoles):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.music WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup music filtering yet")
        rs = exempt.roles or []
        exempt = list(set(rs + [r.id for r in roles]))
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )
        await self.bot.db.execute(
            """UPDATE moderation.music SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully made the following roles exempt {human_join(exempt_roles, final='and')}"
        )

    @filter_musicfile_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from music filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_musicfile_exempt_list(self, ctx: Context):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.music WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup musicfile filtering yet")
        if not exempt.roles:
            raise CommandError("No roles are exempted from the **musicfile** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt.roles),
            )
        )
        embed = Embed(title="Exempted roles for musicfiles").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @filter_.group(
        name="massmention",
        aliases=["mm", "mention"],
        description="Delete any message exceeding the threshold for user mentions",
        example=",filter massmention all on --threshold 5 --do delete",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_massmention(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, str]] = "all",
        setting: Optional[Boolean] = True,
        *,
        flags: SpamFilterFlags,
    ):
        channels = (
            [channel.id]
            if isinstance(channel, TextChannel)
            else [c.id for c in ctx.guild.text_channels]
        )
        await self.bot.db.execute(
            """INSERT INTO moderation.mention (guild_id, channel_ids, threshold, action) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id) DO UPDATE SET channel_ids = excluded.channel_ids, threshold = excluded.threshold, action = excluded.action""",
            ctx.guild.id,
            channels,
            flags.threshold,
            flags.punishment,
        )
        return await ctx.success(
            f"{'ENABLED' if setting else 'DISABLED'} **mass mention** filter in {len(channels)}** {'channel' if len(channels) == 1 else 'channels'}. Punishment is set to **{flags.punishment}**. Threshold is set to **{flags.threshold}**"
        )

    @filter_massmention.group(
        name="exempt",
        aliases=["wl", "ex"],
        description="Exempt roles from the massmention filter",
        example=",filter massmention exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_massmention_exempt(self, ctx: Context, *, roles: MultipleRoles):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.mention WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup mass mention filtering yet")
        rs = exempt.roles or []
        exempt = list(set(rs + [r.id for r in roles]))
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )
        await self.bot.db.execute(
            """UPDATE moderation.mention SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully made the following roles exempt {human_join(exempt_roles, final='and')}"
        )

    @filter_massmention_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from massmention filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_massmention_exempt_list(self, ctx: Context):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.mention WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup mass mention filtering yet")
        if not exempt.roles:
            raise CommandError("No roles are exempted from the **mass mention** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt.roles),
            )
        )
        embed = Embed(title="Exempted roles for mass mention").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @filter_.group(
        name="emoji",
        aliases=["emojis", "emote", "emotes"],
        description="Delete any message exceeding the threshold for emojis",
        example=",filter emoji all on --threshold 5 --do delete",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_emoji(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, str]] = "all",
        setting: Optional[Boolean] = True,
        *,
        flags: SpamFilterFlags,
    ):
        channels = (
            [channel.id]
            if isinstance(channel, TextChannel)
            else [c.id for c in ctx.guild.text_channels]
        )
        await self.bot.db.execute(
            """INSERT INTO moderation.emoji (guild_id, channel_ids, threshold, action) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id) DO UPDATE SET channel_ids = excluded.channel_ids, threshold = excluded.threshold, action = excluded.action""",
            ctx.guild.id,
            channels,
            flags.threshold,
            flags.punishment,
        )
        return await ctx.success(
            f"{'ENABLED' if setting else 'DISABLED'} **mass mention** filter in {len(channels)}** {'channel' if len(channels) == 1 else 'channels'}. Punishment is set to **{flags.punishment}**. Threshold is set to **{flags.threshold}**"
        )

    @filter_emoji.group(
        name="exempt",
        aliases=["wl", "ex"],
        description="Exempt roles from the emoji filter",
        example=",filter emoji exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_emoji_exempt(self, ctx: Context, *, roles: MultipleRoles):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.emoji WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup emoji filtering yet")
        rs = exempt.roles or []
        exempt = list(set(rs + [r.id for r in roles]))
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )
        await self.bot.db.execute(
            """UPDATE moderation.emoji SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully made the following roles exempt {human_join(exempt_roles, final='and')}"
        )

    @filter_emoji_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from emoji filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_emoji_exempt_list(self, ctx: Context):
        if not (
            exempt := await self.bot.db.fetchval(
                """SELECT guild_id, exempt_roles FROM moderation.emoji WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("You have not setup emoji filtering yet")
        if not exempt.roles:
            raise CommandError("No roles are exempted from the **emoji** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt.roles),
            )
        )
        embed = Embed(title="Exempted roles for emoji").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @filter_.group(
        name="regex",
        aliases=["re"],
        description="Add or remove a regex pattern",
        example=",filter regex \b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_regex(
        self, ctx: Context, pattern: RegexConverter, *, flags: FilterFlags
    ):
        if await self.bot.db.fetchrow(
            """SELECT * FROM moderation.regex WHERE guild_id = $1 AND regex = $2""",
            ctx.guild.id,
            pattern,
        ):
            await self.bot.db.execute(
                """DELETE FROM moderation.regex WHERE guild_id = $1 AND regex = $2""",
                ctx.guild.id,
                pattern,
            )
            return await ctx.success(
                f"**{pattern}** has been removed from the regex filter"
            )
        else:
            await self.bot.db.execute(
                """INSERT INTO moderation.regex (guild_id, regex, action) VALUES($1, $2, $3) ON CONFLICT(guild_id, regex) DO UPDATE SET action = excluded.action""",
                ctx.guild.id,
                pattern,
                flags.punishment,
            )
            return await ctx.success(
                f"Added regex pattern **{pattern}**. Punishment is set to **{flags.punishment}**"
            )

    @filter_regex.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="view regex patterns that have been setup",
    )
    @has_permissions(manage_guild=True)
    async def filter_regex_list(self, ctx: Context):
        if not (
            regex := await self.bot.db.fetch(
                "SELECT regex FROM moderation.regex WHERE guild_id = $1" "",
                ctx.guild.id,
            )
        ):
            raise CommandError("No regex patterns have been setup")
        regex = [r.regex for r in regex]
        embed = Embed(title="Regex patterns").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed, [f"`{i}` **{pattern}**" for i, pattern in enumerate(regex, start=1)]
        )

    @filter_regex.group(
        name="exempt",
        aliases=["wl", "ex"],
        description="Exempt roles from the regex filter",
        example=",filter regex exempt @mods",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def filter_regex_exempt(self, ctx: Context, *, roles: MultipleRoles):
        rs = (
            await self.bot.db.fetchval(
                """SELECT exempt_roles FROM moderation.regex_exempt WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or []
        )
        exempt = list(set(rs + [r.id for r in roles]))
        exempt_roles = list(
            filter(
                lambda r: r is not None,
                (ctx.guild.get_role(role_id) for role_id in exempt),
            )
        )
        await self.bot.db.execute(
            """UPDATE moderation.regex SET exempt_roles = $1 WHERE guild_id = $2""",
            [r.id for r in exempt_roles],
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully made the following roles exempt {human_join(exempt_roles, final='and')}"
        )

    @filter_regex_exempt.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of roles exempted from regex filter",
    )
    @has_permissions(manage_guild=True)
    async def filter_regex_exempt_list(self, ctx: Context):
        rs = (
            await self.bot.db.fetchval(
                """SELECT exempt_roles FROM moderation.regex_exempt WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or []
        )
        if not rs:
            raise CommandError("No roles are exempted from the **regex** filter")
        exempt_roles = list(
            filter(
                lambda r: r is not None, (ctx.guild.get_role(role_id) for role_id in rs)
            )
        )
        embed = Embed(title="Exempted roles for regex").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(
            embed,
            [
                f"`{i}` {role.mention} (`{role.id}`)"
                for i, role in enumerate(exempt_roles, start=1)
            ],
        )

    @group(
        name="pins",
        description="Pin archival system commands",
        invoke_without_command=True,
    )
    async def pins(self, ctx: Context):
        return await ctx.send_help()

    @pins.command(name="archive", description="Archive the pins in the current channel")
    @has_permissions(manage_guild=True)
    async def pins_archive(self, ctx: Context):
        if not (
            config := await self.bot.db.fetchrow(
                """SELECT channel_id, enabled, unpinning FROM pin_config WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("Pin archival hasn't been setup")
        if not config.channel_id:
            raise CommandError("Pin archival channel hasn't been set")
        if not config.enabled:
            raise CommandError("Pin archival is **disabled**")
        if not (channel := ctx.guild.get_channel(config.channel_id)):
            raise CommandError("Pin archival channel has been deleted")
        embed = Embed(
            color=self.bot.color,
            description="Starting **archival process**.. this may take a while",
        )
        message = await ctx.send(embed=embed)
        pins = await ctx.channel.archive_pins(channel, config.unpinning)
        return await message.edit(
            embed=await ctx.success(
                f"Archived **{len(pins)}** {'pin' if len(pins) == 1 else 'pins'}",
                return_embed=True,
            )
        )

    @pins.command(
        name="config",
        description="View the pin archival config",
        aliases=["show", "cfg", "settings"],
    )
    @has_permissions(manage_guild=True)
    async def pins_config(self, ctx: Context):
        if not (
            config := await self.bot.db.fetchrow(
                """SELECT * FROM pin_config WHERE guild_id = $1""", ctx.guild.id
            )
        ):
            raise CommandError("Pin archival hasn't been setup")
        if not config.channel_id:
            channel_value = "N/A"
        elif not (channel := ctx.guild.get_channel(config.channel_id)):
            channel_value = "Channel has been deleted"
        else:
            channel_value = f"{channel.mention}"

        def bool_to_emoji(s: bool):
            return (
                self.bot.config["emojis"]["success"]
                if s
                else self.bot.config["emojis"]["fail"]
            )

        embed = Embed(color=self.bot.color, title="Pin Archival Config")
        embed.description = f"""**Enabled:** {bool_to_emoji(config.enabled)}\n**Unpin:** {bool_to_emoji(config.unpinning)}\n**Channel:** {channel_value}"""
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        return await ctx.send(embed=embed)

    @pins.command(
        name="unpin",
        description="Enable or disable the unpinning of messages during archival",
    )
    @has_permissions(manage_guild=True)
    async def pins_unpin(self, ctx: Context, option: Boolean):
        await self.bot.db.execute(
            """INSERT INTO pin_config (guild_id, unpinning) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET unpinning = excluded.unpinning""",
            ctx.guild.id,
            option,
        )
        return await ctx.success(
            f"Pin archival unpinning **{'enabled' if option else 'disabled'}**"
        )

    @pins.command(name="set", description="Enable or disable the pin archival system")
    @has_permissions(manage_guild=True)
    async def pins_set(self, ctx: Context, option: Boolean):
        await self.bot.db.execute(
            """INSERT INTO pin_config (guild_id, enabled) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET enabled = excluded.enabled""",
            ctx.guild.id,
            option,
        )
        return await ctx.success(
            f"Pin archival **{'enabled' if option else 'disabled'}**"
        )

    @pins.command(name="channel", description="Set the pin archival channel")
    @has_permissions(manage_guild=True)
    async def pins_channel(self, ctx: Context, *, channel: TextChannel):
        await self.bot.db.execute(
            """INSERT INTO pin_config (guild_id, channel_id) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id""",
            ctx.guild.id,
            channel.id,
        )
        return await ctx.success(f"Pin archival channel set to {channel.mention}")

    @pins.command(name="reset", description="Reset the pin archival config")
    @has_permissions(manage_guild=True)
    async def pins_reset(self, ctx: Context):
        message = await ctx.warning(
            "Are you sure you want to clear the **pin archive** config?"
        )
        confirmed: bool = await confirm(self, ctx, message, ctx.author)
        if not confirmed:
            return await message.delete()
        await self.bot.db.execute(
            """DELETE FROM pin_config WHERE guild_id = $1""", ctx.guild.id
        )
        return await message.edit(
            embed=await ctx.success("**Pin archival** config reset", return_embed=True)
        )

    @group(
        name="fakepermissions",
        aliases=["fp", "fakeperms", "fakeperm"],
        description="Set up fake permissions for role through the bot!",
        invoke_without_command=True,
    )
    async def fakepermissions(self, ctx: Context):
        return await ctx.send_help()

    @fakepermissions.command(
        name="remove",
        aliases=["rem", "delete", "del", "r", "d"],
        description="Remove a fake permission from a role",
        example="fakepermissions remove @everyone manage_messages",
    )
    @has_permissions(server_owner=True)
    async def fakepermissions_remove(
        self, ctx: Context, role: Role, *, permissions: FakePermissionConverter
    ):
        if not (
            fake_permission := await self.bot.db.fetchval(
                """SELECT permissions FROM fake_permissions WHERE guild_id = $1 AND role_id = $2""",
                ctx.guild.id,
                role.id,
            )
        ):
            raise CommandError(
                f"{role.mention} doesn't have any fake permissions setup"
            )
        removed = []
        for permission in permissions:
            try:
                fake_permission.remove(str(permission))
                removed.append(permission)
            except ValueError:
                continue
        await self.bot.db.execute(
            """UPDATE fake_permissions SET permissions = $1 WHERE guild_id = $2 AND role_id = $3""",
            fake_permission,
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(
            f"Removed the following permissions from {role.mention}: {', '.join(f'`{p}`' for p in removed)}"
        )

    @fakepermissions.command(
        name="add",
        aliases=["create", "c", "a", "set", "grant", "g"],
        description="Grant a fake permission to a role",
        example="fakepermissions add @everyone manage_messages",
    )
    @has_permissions(server_owner=True)
    async def fakepermissions_add(
        self, ctx: Context, role: Role, *, permissions: FakePermissionConverter
    ):
        await self.bot.db.execute(
            """INSERT INTO fake_permissions (guild_id, role_id, permissions) VALUES($1, $2, $3) ON CONFLICT(guild_id, role_id) DO UPDATE SET permissions = ARRAY(SELECT DISTINCT unnest(fake_permissions.permissions || EXCLUDED.permissions));""",
            ctx.guild.id,
            role.id,
            permissions,
        )
        return await ctx.success(
            f"Added the following permissions to {role.mention}: {', '.join(f'`{p}`' for p in permissions)}"
        )

    @fakepermissions.command(name="reset", description="Resets all fake permissions")
    @has_permissions(server_owner=True)
    async def fakepermissions_reset(self, ctx: Context):
        message = await ctx.warning(
            "Are you sure you want to clear the **fake permissions** config?"
        )
        confirmed: bool = await confirm(self, ctx, message, ctx.author)
        if not confirmed:
            return await message.delete()
        await self.bot.db.execute(
            """DELETE FROM fake_permissions WHERE guild_id = $1""", ctx.guild.id
        )
        return await message.edit(
            embed=await ctx.success(
                "**Fake Permissions** config reset", return_embed=True
            )
        )

    @fakepermissions.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="List all fake permissions",
        example=",fakepermissions list Moderator",
    )
    @has_permissions(server_owner=True)
    async def fakepermissions_list(self, ctx: Context, *, role: Optional[Role] = None):
        if role:
            fake_permissions = await self.bot.db.fetchval(
                """SELECT permissions FROM fake_permissions WHERE guild_id = $1 AND role_id = $2""",
                ctx.guild.id,
                role.id,
            )
            if not fake_permissions:
                raise CommandError(
                    f"{role.mention} doesn't have any **fake permissions** setup"
                )
            else:
                rows = [
                    f"`{i}` {permission}"
                    for i, permission in enumerate(fake_permissions, start=1)
                ]
                embed = Embed(
                    color=self.bot.color, title=f"Fake Permissions for {role.name}"
                )
                embed.set_author(
                    name=str(ctx.author), icon_url=ctx.author.display_avatar.url
                )
                return await ctx.paginate(embed, rows)
        else:
            if not (
                fake_permissions := await self.bot.db.fetch(
                    """SELECT role_id, permissions FROM fake_permissions WHERE guild_id = $1""",
                    ctx.guild.id,
                )
            ):
                raise CommandError("No **fake permissions** are setup")

            embed = Embed(color=self.bot.color, title="Fake Permissions")
            embed.set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            )
            i = 0
            rows = []
            for row in fake_permissions:
                if not (role := ctx.guild.get_role(row.role_id)):
                    continue
                i += 1
                rows.append(
                    f"`{i}` {role.mention} - {', '.join(f'**{permission}**' for permission in row.permissions)}"
                )
            return await ctx.paginate(embed, rows)

    @group(
        name="colorme",
        description="Set your color to a custom color if enabled",
        invoke_without_command=True,
        aliases=["cr"],
        example=",colorme purple",
    )
    async def colorme(self, ctx: Context, *, color: ColorConverter):
        if not (
            config := await self.bot.db.fetchrow(
                """SELECT * FROM config WHERE guild_id = $1""", ctx.guild.id
            )
        ):
            raise CommandError("This server doesn't have **colorme** enabled")
        if not config.colorme:
            raise CommandError("This server doesn't have **colorme** enabled")
        current_roles = (
            await self.bot.db.fetchval(
                """SELECT roles FROM color_roles WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )

        current_roles = [i.split("-", 1) for i in current_roles]
        current_role_ids = [int(i[1]) for i in current_roles]
        author_roles = [r for r in ctx.author.roles]
        author_role_ids = [int(role.id) for role in ctx.author.roles]
        if any(item in current_role_ids for item in author_role_ids):
            current_color_role = ctx.guild.get_role(
                [i for i in current_role_ids if i in author_role_ids][0]
            )
            if len(current_color_role.members) == 1:
                current = [
                    i for i in current_roles if i[1] == str(current_color_role.id)
                ][0]
                current_roles.remove(current)
                await current_color_role.delete(reason="Colorme Cleanup")
            author_roles.remove(current_color_role)

        matches = [i for i in current_roles if i[0] == str(color.value)]
        if matches:
            match = matches[0]
            new_role = ctx.guild.get_role(int(match[1]))
            if not new_role:
                current_roles.remove(match)
                new_role = await ctx.guild.create_role(
                    name=str(color.value),
                    color=color,
                    reason="Colorme",
                )
                if config.colorme_base:
                    if base_role := ctx.guild.get_role(config.colorme_base):
                        await new_role.edit(
                            position=base_role.position, reason="Colorme Base"
                        )
                current_roles.append((f"{str(color.value)}", str(new_role.id)))
        else:
            new_role = await ctx.guild.create_role(
                name=str(color.value), color=color, reason="Colorme"
            )
            if config.colorme_base:
                if base_role := ctx.guild.get_role(config.colorme_base):
                    await new_role.edit(
                        position=base_role.position, reason="Colorme Base"
                    )
            current_roles.append((f"{str(color.value)}", str(new_role.id)))
        author_roles.append(new_role)
        await ctx.author.edit(roles=author_roles, reason="Colorme")
        await self.bot.db.execute(
            """UPDATE color_roles SET roles = $1 WHERE guild_id = $2""",
            [f"{i[0]}-{i[1]}" for i in current_roles],
            ctx.guild.id,
        )
        return await ctx.success(f"Set your color to {str(color.value)}")

    @colorme.command(
        name="enable",
        aliases=["on"],
        description="Turn colorme on so users can change their color role",
    )
    @has_permissions(manage_guild=True)
    async def colorme_enable(self, ctx: Context):
        await self.bot.db.execute(
            """INSERT INTO config (guild_id, colorme) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET colorme = excluded.colorme""",
            ctx.guild.id,
            True,
        )
        return await ctx.success("Colorme is now enabled")

    @colorme.command(
        name="disable",
        aliases=["off"],
        description="Turn colorme off so users can't change their color role",
    )
    @has_permissions(manage_guild=True)
    async def colorme_disable(self, ctx: Context):
        await self.bot.db.execute(
            """INSERT INTO config (guild_id, colorme) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET colorme = excluded.colorme""",
            ctx.guild.id,
            False,
        )
        current_roles = (
            await self.bot.db.fetchval(
                """SELECT roles FROM color_roles WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        for role_value in current_roles:
            role_id = int(role_value.split("-", 1)[1])
            if not (role := ctx.guild.get_role(role_id)):
                continue
            await role.delete(reason="Colorme Cleanup")
        await self.bot.db.execute(
            """DELETE FROM color_roles WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("Colorme is now disabled")

    @colorme.command(name="cleanup", description="Cleanup unused color roles")
    @has_permissions(manage_guild=True)
    async def colorme_cleanup(self, ctx: Context):
        current_roles = await self.bot.db.fetchval(
            """SELECT roles FROM color_roles WHERE guild_id = $1""", ctx.guild.id
        )
        if not current_roles:
            raise CommandError("No **color roles** have been created")
        validated = []
        delete = []
        for value in current_roles:
            role_id = int(value.split("-", 1)[1])
            if not (role := ctx.guild.get_role(role_id)):
                delete.append(role_id)
            if len(role.members) > 0:
                validated.append(value)
            else:
                delete.append(role)

        async def delete():
            for role in delete:
                if isinstance(role, int):
                    continue
                await role.delete(reason="Colorme Cleanup")

        message = await ctx.normal(
            f"Cleaning up **{len(delete)}** unused color roles, this may take a while..."
        )
        await delete()
        await self.bot.db.execute(
            """UPDATE color_roles SET roles = $1 WHERE guild_id = $2""",
            validated,
            ctx.guild.id,
        )
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @colorme.command(
        name="baserole",
        aliases=["base", "br"],
        descripton="set the role for the color roles to be under when created",
    )
    @has_permissions(manage_guild=True)
    async def colorme_baserole(self, ctx: Context, *, role: Role):
        current_roles = (
            await self.bot.db.fetchval(
                """SELECT roles FROM color_roles WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        await self.bot.db.execute(
            """INSERT INTO config (guild_id, colorme_base) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET colorme_base = excluded.colorme_base""",
            ctx.guild.id,
            role.id,
        )
        if not len(current_roles) > 0:
            return await ctx.success(
                f"Set the **color me base role** to {role.mention}"
            )
        else:
            message = await ctx.normal(
                f"Repositioning **{len(current_roles)}** colorme roles, this may take a while..."
            )
            for value in current_roles:
                role_id = int(value.split("-", 1)[1])
                if not (role := ctx.guild.get_role(role_id)):
                    continue
                await role.edit(position=role.position, reason="Colorme Base Role")
            return await message.edit(
                embed=Embed(
                    color=self.bot.color,
                    description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
                )
            )

    @group(
        name="allow",
        description="Allow or Disallow a user to use a command without checking permissions",
        example=",allow jonathan ban",
        invoke_without_command=True,
    )
    @has_permissions(server_owner=True)
    async def allow(self, ctx: Context, member: Member, command: CommandOrGroup):
        try:
            await self.bot.db.execute(
                """INSERT INTO command_allowed (guild_id, user_id, command) VALUES($1, $2, $3)""",
                ctx.guild.id,
                member.id,
                command,
            )
            return await ctx.success(f"Allowed **{str(member)}** to use **{command}**")
        except Exception:
            await self.bot.db.execute(
                """DELETE FROM command_allowed WHERE guild_id = $1 AND user_id = $2 AND command = $3""",
                ctx.guild.id,
                member.id,
                command,
            )
            return await ctx.success(
                f"Disallowed **{str(member)}** from using **{command}**"
            )

    @allow.command(
        name="list",
        description="List all users who are allowed to use commands",
        aliases=["ls", "show", "view"],
    )
    @has_permissions(server_owner=True)
    async def allow_list(self, ctx: Context):
        if not (
            allowed_users := await self.bot.db.fetch(
                "SELECT user_id, command FROM command_allowed WHERE guild_id = $1" "",
                ctx.guild.id,
            )
        ):
            raise CommandError("No users have been allowed to use commands")
        embed = Embed(title="Allowed Users").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )

        def get_row(index: int, record: Record) -> str:
            if user := self.bot.get_user(record.user_id):
                return (
                    f"`{index}` **{str(user)}** (`{record.user_id}`) - {record.command}"
                )
            else:
                return f"`{index}` **Unknown User** (`{record.user_id}`) - {record.command}"

        rows = [get_row(i, record) for i, record in enumerate(allowed_users, start=1)]
        return await ctx.paginate(embed, rows)
