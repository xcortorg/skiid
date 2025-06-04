import asyncio
import logging
import traceback

from discord.ext import tasks
from discord.ext.commands import AutoShardedBot as AB

from modules.misc.functions import reminder, bump, vote, giveaway, jail, timer, nuke, pingtimeout, revive, blacklist, autoposting_pfps, autoposting_banners, voicetrack, twitter, youtube, tiktok, instagram, leaderboard, counter, snipe, birthday, freegames

logger = logging.getLogger(__name__)

async def run_task_safely(task_func, name):
    try:
        await task_func
        return True
    except Exception as e:
        logger.error(f"Error in task {name}: {e}")
        logger.debug(traceback.format_exc())
        return False

@tasks.loop(minutes=1)
async def oneminute_loop(bot: AB):
    task_functions = [
        (reminder(bot), "reminder"),
        (bump(bot), "bump"),
        (vote(bot), "vote"),
        (giveaway(bot), "giveaway"),
        (jail(bot), "jail"),
        (timer(bot), "timer"),
        (nuke(bot), "nuke"),
        # (twitch(bot), "twitch"),
        (pingtimeout(bot), "pingtimeout"),
        (revive(bot), "revive"),
        (blacklist(bot), "blacklist"),
    ]
    await asyncio.gather(*[run_task_safely(func, name) for func, name in task_functions])

@tasks.loop(minutes=5)
async def fiveminutes_loop(bot: AB):
    task_functions = [
        # (autoposting_pfps(bot), "autoposting_pfps"),
        # (autoposting_banners(bot), "autoposting_banners"),
        (voicetrack(bot), "voicetrack"),
        (twitter(bot), "twitter"),
        (youtube(bot), "youtube"),
        (tiktok(bot), "tiktok"),
        (instagram(bot), "instagram"),
        # (leaderboard(bot), "leaderboard"),
    ]
    await asyncio.gather(*[run_task_safely(func, name) for func, name in task_functions])

@tasks.loop(minutes=10)
async def tenminutes_loop(bot: AB):
    task_functions = [
        (counter(bot), "counter"),
        (snipe(bot), "snipe"),
        (birthday(bot), "birthday"),
        (freegames(bot), "freegames"),
    ]
    await asyncio.gather(*[run_task_safely(func, name) for func, name in task_functions])