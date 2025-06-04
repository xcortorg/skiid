import discord
from discord.ext import commands, tasks

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_user_id = 785042666475225109
        self.statuses = [
            "https://playfairs.cc",
            "guns.lol/heresy",
            ".gg/heresy"
        ]
        self.current_status_index = 0
        self.custom_status = None
        self.status_rotator.start()

    def bot_owner_only():
        """Decorator to restrict commands to the bot owner."""
        async def predicate(ctx):
            return ctx.author.id == ctx.cog.allowed_user_id
        return commands.check(predicate)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(status=discord.Status.dnd)
        print("Bot is ready with default presence: Do Not Disturb")

    @tasks.loop(seconds=5)
    async def status_rotator(self):
        """Rotate through statuses every 5 seconds if no custom status is set."""
        if not self.custom_status:
            current_status = self.statuses[self.current_status_index]
            try:
                await self.bot.change_presence(
                    activity=discord.CustomActivity(name=current_status),
                    status=discord.Status.dnd
                )
                print(f"Rotating status to: {current_status}")
            except Exception as e:
                print(f"Error changing presence: {e}")
            self.current_status_index = (self.current_status_index + 1) % len(self.statuses)

    @commands.command(name="status")
    @bot_owner_only()
    async def set_custom_status(self, ctx, *, status: str):
        """Set the bot's custom status (activity) and pause the rotator."""
        self.custom_status = status
        self.status_rotator.stop()
        try:
            await self.bot.change_presence(
                activity=discord.CustomActivity(name=status),
                status=discord.Status.dnd
            )
            await ctx.send(f"Custom status changed to: `{status}`")
            print(f"Custom status changed to: {status}")
        except Exception as e:
            await ctx.send(f"Failed to change custom status: {e}")
            print(f"Error setting custom status: {e}")

    @commands.command(name="clearstatus")
    @bot_owner_only()
    async def clear_custom_status(self, ctx):
        """Clear the custom status and resume the rotating status loop."""
        self.custom_status = None
        self.status_rotator.start()
        await ctx.send("Custom status cleared. Rotating status resumed.")
        print("Custom status cleared. Rotating status resumed.")

async def setup(bot):
    await bot.add_cog(Status(bot))
