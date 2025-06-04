async def resolve_variables(self, script: str = None, **kwargs):
    """Format the variables inside the script"""
    # Use provided script or instance script
    script_to_resolve = script if script is not None else self.script

    # Get current time in PST and UTC
    pst_now = datetime.now(timezone('US/Pacific'))
    utc_now = datetime.now(timezone('UTC'))

    # Add date/time variables...

    if guild := kwargs.get("guild"):
        script_to_resolve = (
            script_to_resolve
            # Existing guild replacements...
            .replace("{guild}", str(guild))
            .replace("{guild.id}", str(guild.id))
            .replace("{guild.name}", str(guild.name))
            
            # New guild replacements
            .replace("{guild.region}", str(getattr(guild, "region", "N/A")))  # Voice region might be None
            .replace("{guild.created_at_timestamp}", str(int(guild.created_at.timestamp())))
            .replace(
                "{guild.discovery}", 
                str(guild.discovery_splash.url if guild.discovery_splash else "N/A")
            )
            .replace(
                "{guild.channels_count}",
                str(comma(len(guild.channels))),
            )
            .replace(
                "{guild.text_channels_count}",
                str(comma(len(guild.text_channels))),
            )
            .replace(
                "{guild.voice_channels_count}",
                str(comma(len(guild.voice_channels))),
            )
            .replace(
                "{guild.category_channels_count}",
                str(comma(len(guild.categories))),
            )
            # ... rest of existing guild replacements ...
        )

    if user := kwargs.get("user"):
        script_to_resolve = (
            script_to_resolve.replace("{member", "{user")
            # Existing user replacements...
            .replace("{user}", str(user))
            .replace("{user.id}", str(user.id))
            
            # New user replacements
            .replace("{user.display_avatar}", str(user.display_avatar.url if user.display_avatar else user.default_avatar.url))
            .replace("{user.joined_at_timestamp}", str(int(user.joined_at.timestamp())) if isinstance(user, Member) else "N/A")
            .replace("{user.created_at_timestamp}", str(int(user.created_at.timestamp())))
            .replace(
                "{user.boost_since_timestamp}", 
                str(int(user.premium_since.timestamp())) if isinstance(user, Member) and user.premium_since else "Never"
            )
            .replace("{user.badges_icons}", self._get_user_badge_icons(user))  # You'll need to implement this method
            .replace("{user.badges}", self._get_user_badges(user))  # You'll need to implement this method
            .replace(
                "{user.join_position}", 
                str(sorted(guild.members, key=lambda m: m.joined_at).index(user) + 1) if isinstance(user, Member) and guild else "N/A"
            )
            # ... rest of existing user replacements ...
        )

    # ... rest of method ...

def _get_user_badge_icons(self, user: Union[Member, User]) -> str:
    """Get user badge icons"""
    badges = []
    flags = user.public_flags
    
    # Map flags to emojis - you'll need to define these emojis somewhere
    if flags.staff:
        badges.append("<:staff:emoji_id>")
    if flags.partner:
        badges.append("<:partner:emoji_id>")
    if flags.hypesquad:
        badges.append("<:hypesquad:emoji_id>")
    if flags.bug_hunter:
        badges.append("<:bughunter:emoji_id>")
    if flags.hypesquad_bravery:
        badges.append("<:bravery:emoji_id>")
    if flags.hypesquad_brilliance:
        badges.append("<:brilliance:emoji_id>")
    if flags.hypesquad_balance:
        badges.append("<:balance:emoji_id>")
    if flags.early_supporter:
        badges.append("<:early_supporter:emoji_id>")
    if flags.verified_bot_developer:
        badges.append("<:verified_developer:emoji_id>")
    
    return " ".join(badges) if badges else "N/A"

def _get_user_badges(self, user: Union[Member, User]) -> str:
    """Get user badges as text"""
    badges = []
    flags = user.public_flags
    
    if flags.staff:
        badges.append("Discord Staff")
    if flags.partner:
        badges.append("Partnered Server Owner")
    if flags.hypesquad:
        badges.append("HypeSquad Events")
    if flags.bug_hunter:
        badges.append("Bug Hunter")
    if flags.hypesquad_bravery:
        badges.append("HypeSquad Bravery")
    if flags.hypesquad_brilliance:
        badges.append("HypeSquad Brilliance")
    if flags.hypesquad_balance:
        badges.append("HypeSquad Balance")
    if flags.early_supporter:
        badges.append("Early Supporter")
    if flags.verified_bot_developer:
        badges.append("Verified Bot Developer")
    
    return ", ".join(badges) if badges else "N/A"