def process_guild_data(guild_data: dict) -> dict:
    """
    Process guild information in a seperate process.
    """
    members = guild_data['members']
    member_count = guild_data['member_count']

    user_count = len([i for i in members if not i['bot']])
    bot_count = len([i for i in members if i['bot']])

    return {
        'user_count': user_count,
        'bot_count': bot_count,
        'user_percentage': (user_count / member_count) * 100,
        'bot_percentage': (bot_count / member_count) * 100,
    }