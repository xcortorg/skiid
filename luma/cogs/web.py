from discord.ext import commands
from quart import Quart, redirect, render_template, request


class Web(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.app = Quart(__name__)
        self.app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

        @self.app.route("/")
        async def index():
            return await render_template(
                "index.html",
                users=f"{sum(g.member_count for g in self.bot.guilds):,}",
                guilds=len(self.bot.guilds),
            )

        @self.app.route("/discord")
        async def discord():
            return redirect("https://discord.gg/2uGcc9hDYk")

        @self.app.route("/invite")
        async def invite():
            return redirect(
                "https://discord.com/oauth2/authorize?client_id=1263203971846242317&scope=bot+applications.commands&permissions=8"
            )

        @self.app.route("/commands")
        @self.app.route("/cmds")
        @self.app.route("/help")
        async def commands():
            commands = {
                c: {
                    "commands": [
                        {"name": cmd.qualified_name, "description": cmd.help}
                        for cmd in sorted(
                            set(cmds.walk_commands()), key=lambda r: r.qualified_name
                        )
                    ],
                }
                for c, cmds in self.bot.cogs.items()
                if not c in ["Jishaku", "Developer"]
                and len(set(cmds.walk_commands())) > 0
            }

            return await render_template("commands.html", commands=commands)

        @self.app.route("/idk", methods=["GET"])
        async def address():
            ip = request.headers.get("Cf-Connecting-Ip", "Unknown")
            print(ip)
            return ip

    async def cog_load(self):
        self.bot.loop.create_task(self.app.run_task(host="0.0.0.0", port=7856))

    async def cog_unload(self):
        await self.app.shutdown()


async def setup(bot: commands.Bot):
    return await bot.add_cog(Web(bot))
