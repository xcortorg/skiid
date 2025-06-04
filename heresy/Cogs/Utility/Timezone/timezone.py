import discord
from discord.ext import commands
import datetime
import pytz
import json
import os

TIMEZONE_ABBR = {
    # Americas
    'CST': 'US/Central',
    'EST': 'US/Eastern',
    'PST': 'US/Pacific',
    'MST': 'US/Mountain',
    'AKST': 'US/Alaska',
    'HST': 'US/Hawaii',
    'AST': 'America/Puerto_Rico',  # Atlantic Standard Time
    'NST': 'America/St_Johns',    # Newfoundland Standard Time

    # Europe
    'GMT': 'GMT',
    'UTC': 'UTC',
    'BST': 'Europe/London',
    'CET': 'Europe/Berlin',      # Central European Time
    'EET': 'Europe/Athens',      # Eastern European Time
    'WEST': 'Europe/Lisbon',     # Western European Summer Time
    'EEST': 'Europe/Helsinki',   # Eastern European Summer Time

    # Asia
    'IST': 'Asia/Kolkata',       # Indian Standard Time
    'PKT': 'Asia/Karachi',       # Pakistan Standard Time
    'BST': 'Asia/Dhaka',         # Bangladesh Standard Time
    'SGT': 'Asia/Singapore',     # Singapore Standard Time
    'ICT': 'Asia/Bangkok',       # Indochina Time
    'HKT': 'Asia/Hong_Kong',     # Hong Kong Time
    'KST': 'Asia/Seoul',         # Korea Standard Time
    'JST': 'Asia/Tokyo',         # Japan Standard Time
    'CSTA': 'Asia/Shanghai', # China Standard Time

    # Australia
    'ACST': 'Australia/Adelaide',
    'AEST': 'Australia/Sydney',
    'AEDT': 'Australia/Sydney',
    'AWST': 'Australia/Perth',   # Australian Western Standard Time
    'ACDT': 'Australia/Adelaide',# Australian Central Daylight Time

    # Pacific
    'NZST': 'Pacific/Auckland',  # New Zealand Standard Time
    'ChST': 'Pacific/Guam',      # Chamorro Standard Time
    'FJT': 'Pacific/Fiji',       # Fiji Time

    # Africa
    'CAT': 'Africa/Harare',      # Central Africa Time
    'EAT': 'Africa/Nairobi',     # East Africa Time
    'WAT': 'Africa/Lagos',       # West Africa Time
    'SAST': 'Africa/Johannesburg', # South Africa Standard Time

    # Middle East
    'IRST': 'Asia/Tehran',       # Iran Standard Time
    'GST': 'Asia/Dubai',         # Gulf Standard Time
    'AST-ME': 'Asia/Riyadh',     # Arabia Standard Time

    # Miscellaneous
    'ART': 'America/Argentina/Buenos_Aires', # Argentina Time
    'BRST': 'America/Sao_Paulo', # Brazil Summer Time
    'CLT': 'America/Santiago',   # Chile Time
    'WIB': 'Asia/Jakarta',       # Western Indonesia Time
    'WEZ': 'Atlantic/Reykjavik', # Western European Zone
    'ACWST': 'Adelaide/Perth', # Australian Central Western Time
}

if not os.path.exists('db'):
    os.makedirs('db')

DB_FILE = 'db/timezones.json'

def load_timezones():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_timezones(timezones):
    with open(DB_FILE, 'w') as f:
        json.dump(timezones, f, indent=4)

class TimezoneCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="timezone", aliases=['tz'], help="Sets your timezone, e.g. 'UTC', 'PST', or 'GMT'.")
    async def timezone(self, ctx, timezone: str = None):
        """Set your timezone. Use a valid timezone abbreviation (e.g., 'CST', 'GMT')."""
        if timezone is None:
            await ctx.send("Please specify a timezone abbreviation. For example: `,timezone CST`")
            return

        timezone = timezone.upper()
        if timezone in TIMEZONE_ABBR:
            timezone = TIMEZONE_ABBR[timezone]
        else:
            await ctx.send(f"{timezone} is not a valid time zone abbreviation. Please try again.")
            return

        try:
            tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            await ctx.send(f"{timezone} is not a valid timezone. Please try again.")
            return

        timezones = load_timezones()

        timezones[str(ctx.author.id)] = timezone
        save_timezones(timezones)

        await ctx.send(f"Your timezone has been set to {timezone} ({TIMEZONE_ABBR[timezone] if timezone in TIMEZONE_ABBR else timezone}).")

    @commands.command()
    async def time(self, ctx, user: discord.User = None):
        """Get the current time for the user (or yourself if no user is mentioned)."""
        if user is None:
            user = ctx.author

        timezones = load_timezones()

        if str(user.id) not in timezones:
            await ctx.send(f"{user.mention} has not set a timezone. Use `,timezone` to set one.")
            return

        timezone = timezones[str(user.id)]

        tz = pytz.timezone(timezone)
        current_time = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

        embed = discord.Embed(
            title=f"Current time for {user.display_name}",
            description=f"The current time in {timezone} is: {current_time}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TimezoneCog(bot))
