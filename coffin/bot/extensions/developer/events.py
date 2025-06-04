import asyncio

from discord import Client
from discord.ext import tasks
from discord.ext.commands import Cog
from loguru import logger
from system.classes.github import GithubPushEvent


class DeveloperEvents(Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    async def cog_load(self):
        self.global_ban_loop.start()

    async def cog_unload(self):
        self.global_ban_loop.stop()

    @tasks.loop(minutes=1)
    async def global_ban_loop(self):
        try:
            i = 0
            for ban in await self.bot.db.fetch("""SELECT user_id FROM global_ban"""):

                if not (user := self.bot.get_user(ban.user_id)):
                    continue

                for mutual in user.mutual_guilds:
                    member = mutual.get_member(ban.user_id)
                    if member.is_bannable:
                        await member.ban(reason="Global Ban")
                        i += 1
            logger.info(f"successfully executed {i} global bans")
        except Exception as e:
            logger.info(f"unhandled exception in global_ban_loop: {get_error(e)}")

    @Cog.listener("on_github_commit")
    async def github_commit(self, data: GithubPushEvent):
        process = await asyncio.create_subprocess_shell(
            "cd .. ; git init ; git pull",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait until the process finishes
        stdout, stderr = await process.communicate()

        # Check the return code
        if process.returncode == 0:
            total_changes = []
            total_changes.extend(data.head_commit.added)
            total_changes.extend(data.head_commit.removed)
            total_changes.extend(data.head_commit.modified)
            for change in total_changes:
                if "system" in change.lower():
                    logger.info(
                        f"Restarting due to a new commit being added from {data.head_commit.author.name}"
                    )
                    await self.bot.close()


async def setup(bot: Client):
    await bot.add_cog(DeveloperEvents(bot))
