import discord


async def get_or_fetch_member(self, guild, member_id):
    """Looks up a member in cache or fetches if not found.
    Parameters
    -----------
    guild: Guild
        The guild to look in.
    member_id: int
        The member ID to search for.
    Returns
    ---------
    Optional[Member]
        The member or None if not found.
    """

    member = guild.get_member(member_id)
    if member is not None:
        return member

    shard = self.bot.get_shard(guild.shard_id)
    if shard.is_ws_ratelimited():
        try:
            member = await guild.fetch_member(member_id)
        except discord.HTTPException:
            return None
        else:
            return member

    members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
    if not members:
        return None
    return members[0]
