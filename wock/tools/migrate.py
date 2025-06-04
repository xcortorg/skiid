from typing import Literal, Optional, Union

from discord import (AutoModAction, AutoModTrigger, AutoModTriggerType,
                     ForumChannel, Guild, Member, Role, TextChannel, User,
                     utils)
from discord.ext.commands import CommandError

invite_regex = r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"

def str_to_action(string: str):
    _ = string.lower()
    if _ in ["timeout", "mute"]:
        return AutoModAction.timeout
    elif _ == "block":
        return AutoModAction.block_message
    else:
        return AutoModAction.send_alert_message


async def add_keyword(guild: Guild, keyword: str) -> bool:
    val = False
    automod_rules = await guild.fetch_automod_rules()
    if keyword_rule := utils.get(automod_rules, name = "wock-keywords"):
        if keyword_rule.trigger.type == AutoModTriggerType.keyword:
            new_keywords = keyword_rule.trigger.keyword_filter + [keyword[:59]]
            if len(new_keywords) > 1000:
                raise CommandError("You are limited to 1000 filtered words")
            else:
                trigger = AutoModTrigger(
                    type=AutoModTriggerType.keyword,
                    keyword_filter=new_keywords
                )
                await keyword_rule.edit(trigger=trigger)
                val = True
    return val

async def remove_keyword(guild: Guild, keyword: str) -> bool:
    val = False
    automod_rules = await guild.fetch_automod_rules()
    if keyword_rule := utils.get(automod_rules, name = "wock-keywords"):
        if keyword_rule.trigger.type == AutoModTriggerType.keyword:
            new_keywords = keyword_rule.trigger.keyword_filter
            new_keywords.remove(keyword[:59])
            trigger = AutoModTrigger(
                type=AutoModTriggerType.keyword,
                keyword_filter=new_keywords
            )
            await keyword_rule.edit(trigger=trigger)
            val = True
    return val

async def change_punishment(guild: Guild, punishment: Optional[Literal["block", "alert", "timeout", "mute"]] = "block") -> bool:
    rules = await guild.fetch_automod_rules()
    for rule in rules:
        if rule.action


async def exempt(guild: Guild, obj: Union[TextChannel, ForumChannel, Role]):
    rules = await guild.fetch_automod_rules()
    kwargs = {}
    for rule in rules:
        if isinstance(obj, (TextChannel, ForumChannel)):
            if len(rule.exempt_channels) > 0:
                rule.exempt_channels.append(obj)
                kwargs["exempt_channels"] = rule.exempt_channels
            else:
                kwargs["exempt_channels"] = [obj]
        else:
            if len(rule.exempt_roles) > 0:
                rule.exempt_roles.append(obj)
                kwargs["exempt_roles"] = rule.exempt_roles
            else:
                kwargs["exempt_roles"]

        await rule.edit(**kwargs)
        return True

