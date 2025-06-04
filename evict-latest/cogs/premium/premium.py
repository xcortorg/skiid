import config
import re
import time
import boto3

from main import Evict
from managers.patches.permissions import donator
from tools.handlers.reskin import create_reskin, ValidReskinName
from core.client.context import Context
from tools import quietly_delete

from logging import getLogger
from typing import List, Optional, Callable
from datetime import timedelta

from discord import Message
from discord.utils import utcnow
from discord.ext.commands import (
    Cog, 
    command, 
    check, 
    group, 
    CommandError
)

log = getLogger(__name__)

class Premium(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "Donate to use these commands."

    async def do_removal(
        self,
        ctx: Context,
        amount: int,
        predicate: Callable[[Message], bool] = lambda _: True,
        *,
        before: Optional[Message] = None,
        after: Optional[Message] = None,
    ) -> List[Message]:
        """
        A helper function to do bulk message removal.
        """

        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            raise CommandError("I don't have permission to delete messages!")

        if not before:
            before = ctx.message

        def check(message: Message) -> bool:
            if message.created_at < (utcnow() - timedelta(weeks=2)):
                return False

            elif message.pinned:
                return False

            return predicate(message)

        await quietly_delete(ctx.message)
        messages = await ctx.channel.purge(
            limit=amount,
            check=check,
            before=before,
            after=after,
        )
        if not messages:
            raise CommandError("No messages were found, try a larger search?")

        return messages

    @donator()
    @command(brief="donor")
    @check(
        lambda ctx: bool(
            ctx.guild
            and ctx.guild.id in [892675627373699072]
            or ctx.author.id in config.CLIENT.OWNER_IDS
        )
    )
    async def me(self, ctx: Context, amount: int = 100):
        """
        Clean up your messages.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(
                message.author == ctx.author
                or (
                    message.reference
                    and isinstance(message.reference.resolved, Message)
                    and message.reference.resolved.author == ctx.author
                )
            ),
        )

    @donator()
    @group(invoke_without_command=True)
    async def reskin(self, ctx: Context):
        """
        Customize the outputs for Evict's command outputs.
        """
        return await ctx.send_help(ctx.command)

    @donator()
    @reskin.command(name="enable")
    async def reskin_enable(self, ctx: Context):
        """
        Enable the customization of outputs for Evict's command outputs.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM reskin 
            WHERE user_id = $1 
            AND toggled = $2
            """,
            ctx.author.id,
            False,
        )

        if record == None or record["toggled"] == False:

            if not await self.bot.db.fetchrow(
                """
                SELECT * FROM reskin 
                WHERE user_id = $1
                """, 
                ctx.author.id
            ):
                await self.bot.db.execute(
                    """
                    INSERT INTO reskin (user_id, toggled, username, avatar) 
                    VALUES ($1, $2, $3, $4)
                    """,
                    ctx.author.id,
                    True,
                    ctx.author.name,
                    ctx.author.avatar.url,
                )

            else:
                await self.bot.db.execute(
                    """
                    UPDATE reskin
                    SET toggled = $1 
                    WHERE user_id = $2
                    """,
                    True,
                    ctx.author.id,
                )

            return await ctx.approve("Reskin has been enabled!")

        return await ctx.warn("Reskin is already enabled!")

    @donator()
    @reskin.command(name="disable")
    async def reskin_disable(self, ctx: Context):
        """
        Disable the customization of outputs for Evict's command outputs.
        """
        if not await self.bot.db.fetchrow(
            """
            SELECT * FROM reskin
            WHERE user_id = $1
            """, 
            ctx.author.id
        ):
            return await ctx.warn("Reskin is not enabled!")

        await self.bot.db.execute(
            """
            DELETE FROM reskin
            WHERE user_id = $1
            """, 
            ctx.author.id
        )

        return await ctx.approve("Reskin is now disabled!")

    @donator()
    @create_reskin()
    @reskin.command(name="name", example="x")
    async def reskin_name(self, ctx: Context, *, name: ValidReskinName):
        """
        Edit the name that appears on Evict's command outputs.
        """
        await self.bot.db.execute(
            """
            UPDATE reskin SET username = $1 
            WHERE user_id = $2
            """,
            name,
            ctx.author.id,
        )

        return await ctx.warn(f"Updated your reskin name to **{name}**")

    @donator()
    @create_reskin()
    @reskin.command(name="avatar", aliases=["icon", "pfp", "av"])
    async def reskin_avatar(self, ctx: Context, url: str = None):
        """
        Change the avatar that appears on Evict's command outputs.
        """
        if url is None:
            url = await ctx.get_attachment()
            if not url:
                return ctx.send_help(ctx.command)
            else:
                url = url.url

        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»""'']))"
        if not re.findall(regex, url):
            return await ctx.warn("The image provided is not an url")

        try:
            async with self.bot.session.get(url) as response:
                if response.status != 200:
                    return await ctx.warn("Failed to fetch the image")
                image_data = await response.read()

            file_ext = url.split('.')[-1].lower()
            if file_ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                file_ext = 'png'

            filename = f"reskins/{ctx.author.id}_{int(time.time())}.{file_ext}"
            
            log.info(f"[R2] Uploading reskin avatar for {ctx.author} ({ctx.author.id})")
            s3 = boto3.client(
                's3',
                endpoint_url='https://ed57b2c738838b61759d7f3aea14d4b7.r2.cloudflarestorage.com',
                aws_access_key_id='1c681be37b484fba3da97fbb29fce500',
                aws_secret_access_key='38fb08c7a2ed22606a799964aa563af511954c49ecfacd4d7aa68bae3211df43'
            )

            s3.put_object(
                Bucket='evict',
                Key=filename,
                Body=image_data,
                ContentType=f'image/{file_ext}'
            )
            log.info(f"[R2] Successfully uploaded {filename}")

            r2_url = f"https://r2.evict.bot/{filename}"

        except Exception as e:
            log.info(f"[R2] Error uploading reskin avatar: {str(e)}")
            return await ctx.warn(f"Failed to upload image: {str(e)}")

        await self.bot.db.execute(
            """
            UPDATE reskin SET avatar = $1 
            WHERE user_id = $2
            """, 
            r2_url, 
            ctx.author.id
        )

        log.info(f"[R2] Updated reskin avatar in database for {ctx.author} ({ctx.author.id})")
        return await ctx.approve(f"Updated your reskin [**avatar**]({r2_url})")

    @donator()
    @reskin.command(name="remove", aliases=["delete", "reset"])
    async def reskin_delete(self, ctx: Context):
        """
        Delete the reskin output for yourself.
        """
        await ctx.prompt(f"Are you sure you want to remove your reskin?")
        await self.bot.db.execute(
            """
            DELETE FROM reskin
            WHERE user_id = $1
            """, 
            ctx.author.id
        )
        return await ctx.approve("Reskin config has been deleted!")