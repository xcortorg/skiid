from logging import getLogger

log = getLogger("evict/processors")

def process_guild_data(guild_data: dict) -> dict:
    """
    Process guild data in a separate process.
    """
    total_members = guild_data['member_count']
    bot_count = sum(1 for member in guild_data['members'] if member['bot'])
    user_count = total_members - bot_count
    
    stats = {
        'bot_count': bot_count,
        'user_count': user_count,
        'bot_percentage': (bot_count / total_members) * 100 if total_members > 0 else 0,
        'user_percentage': (user_count / total_members) * 100 if total_members > 0 else 0
    }
    return stats

def process_jail_permissions(channel_id: int, role_id: int) -> dict:
    """
    Process jail permissions in a separate process.
    """
    permissions = {
        'view_channel': False,
        'send_messages': False,
        'add_reactions': False,
        'use_external_emojis': False
    }
    return permissions

def process_add_role(member, role, reason=None):
    """
    Process role addition in a separate process.
    """
    member.add_roles(role, reason=reason)
    return True