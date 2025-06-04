from logging import getLogger
from typing import Dict, Optional, Union
from datetime import timedelta

log = getLogger("evict/processors")

def process_mod_action(
    action_data: Dict[str, Union[str, int, timedelta, None]]
) -> Dict[str, str]:
    """
    Process moderation action data in a separate process.
    """
    action = action_data['action']
    duration = action_data.get('duration')
    
    action_title = (
        "hardunbanned" if action == "hardunban" else
        "hardbanned" if action == "hardban" else
        "banned" if action == "ban" else
        "unbanned" if action == "unban" else
        "kicked" if action == "kick" else
        "jailed" if action == "jail" else
        "unjailed" if action == "unjail" else
        "muted" if action == "mute" else
        "unmuted" if action == "unmute" else
        "warned" if action == "warn" else
        "punished" if action.startswith("antinuke") else
        "punished" if action.startswith("antiraid") else
        action + "ed"
    )
    
    result = {
        'title': action_title,
        'is_unaction': action.startswith('un'),
        'is_antinuke': action.startswith('antinuke'),
        'is_antiraid': action.startswith('antiraid'),
        'should_dm': action not in ("timeout", "untimeout") 
    }
    return result

def process_dm_script(
    script_data: Dict[str, str],
    default_data: Dict[str, str]
) -> Dict[str, str]:
    """
    Process DM notification script in a separate process.
    """
    if script_data.get('custom_script'):
        return {'script': script_data['custom_script']}
    
    action = default_data['action']
    guild_name = default_data['guild_name']
    moderator = default_data['moderator']
    reason = default_data['reason']
    duration = default_data.get('duration')
    
    script = (
        f"You have been {action} in {guild_name}\n"
        f"Moderator: {moderator}\n"
        f"Reason: {reason}"
    )
    
    if duration:
        script += f"\nDuration: {duration}"

    return {'script': script}