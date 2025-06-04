import discord
from discord.ext import commands
from datetime import datetime, timezone

class Whois(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.developer_id = 785042666475225109  # The ID of the developer
        self.bot_id = 593921296224747521  # The ID of the specific bot to be treated with ego

    @commands.command(name="whois", aliases=['userinfo', 'ui', 'info'], help="Show detailed information about a user.")
    async def whois(self, ctx, member: discord.Member = None):
        """Displays detailed user information with badges, activity, and roles."""

        try:
            member = member or ctx.author

            # If the queried member is the special bot, give it a special ego reply
            if member.id == self.bot_id:
                await ctx.send("no")
                return

            # Check if the member's ID matches the developer's ID
            developer_title = " - Developer" if member.id == self.developer_id else ""

            badges = []
            if member.public_flags.active_developer:
                badges.append("<:active_developer:1297930880987431035>")
            if member.public_flags.discord_certified_moderator:
                badges.append("<:certified_moderator:1297932110514098290>")
            if member.public_flags.bug_hunter:
                badges.append("<:bug_hunter:1297931813121036321>")
            if member.public_flags.bug_hunter_level_2:
                badges.append("<:bug_hunter_level_2:1297931831521312850>")
            if member.public_flags.early_supporter:
                badges.append("<:early_supporter:1297931252158042283>")
            if member.public_flags.hypesquad:
                badges.append("<:hypesquad:1297930974633398293>")
            if member.public_flags.hypesquad_balance:
                badges.append("<:hypesquad_balance:1297930998864019509>")
            if member.public_flags.hypesquad_brilliance:
                badges.append("<:hypesquad_brilliance:1297931072503418890>")
            if member.public_flags.partner:
                badges.append("<:partner:1297931370357723198>")
            if member.public_flags.staff:
                badges.append("<:staff:1297931763229917246>")
            if member.public_flags.verified_bot_developer:
                badges.append("<:verified_bot_developer:1297931270139150338>")
            if member.premium_since:
                badges.append("<:boost:1297931223972450488>")
            if member == member.guild.owner:
                badges.append("<:server_owner:1297930836368167015>")

            custom_emojis = " ".join(badges) if badges else "No badges"

            activities = member.activities
            listening = None
            playing = None

            for activity in activities:
                if isinstance(activity, discord.Spotify):
                    listening = f"🎧 {activity.title} by {activity.artist}"
                elif isinstance(activity, discord.Game):
                    playing = f"🎮 {activity.name}"

            created_at = member.created_at.strftime("%B %d, %Y")
            joined_at = member.joined_at.strftime("%B %d, %Y")
            created_days_ago = (datetime.now(timezone.utc) - member.created_at).days
            joined_days_ago = (datetime.now(timezone.utc) - member.joined_at).days

            created_ago = f"{created_days_ago // 365} year{'s' if (created_days_ago // 365) > 1 else ''} ago" if created_days_ago >= 365 else f"{created_days_ago} day{'s' if created_days_ago > 1 else ''} ago"
            joined_ago = f"{joined_days_ago // 365} year{'s' if (joined_days_ago // 365) > 1 else ''} ago" if joined_days_ago >= 365 else f"{joined_days_ago} day{'s' if joined_days_ago > 1 else ''} ago"

            roles = [role.mention for role in member.roles[1:]] or ["No roles"]
            roles_string = " ".join(roles)

            embed = discord.Embed(color=discord.Color.dark_purple(), timestamp=datetime.utcnow())
            embed.set_author(name=f"{member.display_name}{developer_title}", icon_url=member.avatar.url)

            embed.add_field(name="User ID", value=f"`{member.id}`", inline=False)

            embed.add_field(name="Badges", value=custom_emojis, inline=False)

            if listening:
                embed.add_field(name="Listening", value=listening, inline=False)
            if playing:
                embed.add_field(name="Playing", value=playing, inline=False)

            embed.add_field(name="Created", value=f"{created_at}\n{created_ago}", inline=True)
            embed.add_field(name="Joined", value=f"{joined_at}\n{joined_ago}", inline=True)

            embed.add_field(name="Roles", value=roles_string, inline=False)

            embed.set_thumbnail(url=member.avatar.url)

            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"**Error**: Something went wrong - (No, nothing went wrong, you can't run this command in DMs, it only works in servers)")

async def setup(bot):
    await bot.add_cog(Whois(bot))
