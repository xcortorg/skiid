import subprocess
import discord
from discord.ext import commands

class Pip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="pip", invoke_without_command=True)
    async def pip(self, ctx):
        """Group for pip commands."""
        embed = discord.Embed(
            title="Pip Commands",
            description=(
                "**Available Commands:**\n"
                "`install` - Install packages.\n"
                "`download` - Download packages.\n"
                "`uninstall` - Uninstall packages.\n"
                "`freeze` - Output installed packages in requirements format.\n"
                "`inspect` - Inspect the Python environment.\n"
                "`list` - List installed packages.\n"
                "`show` - Show information about installed packages.\n"
                "`check` - Verify installed packages have compatible dependencies.\n"
                "`config` - Manage local and global configuration.\n"
                "`search` - Search PyPI for packages.\n"
                "`cache` - Inspect and manage pip's wheel cache.\n"
                "`index` - Inspect information available from package indexes.\n"
                "`wheel` - Build wheels from your requirements.\n"
                "`hash` - Compute hashes of package archives.\n"
                "`completion` - A helper command used for command completion.\n"
                "`debug` - Show information useful for debugging.\n"
                "`help` - Show help for commands."
            ),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    async def run_pip_command(self, ctx, *args):
        """Helper method to run pip commands and embed responses."""
        try:
            result = subprocess.run(["pip", *args], capture_output=True, text=True)
            output = result.stdout if result.returncode == 0 else result.stderr

            # Embed response
            embed = discord.Embed(
                title=f"pip {' '.join(args)}",
                description=output[:4000],  # Discord embeds limit description to 4096 chars
                color=discord.Color.green() if result.returncode == 0 else discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"An error occurred: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @pip.command(name="install")
    async def pip_install(self, ctx, *, package: str):
        """Install packages."""
        await self.run_pip_command(ctx, "install", package)

    @pip.command(name="download")
    async def pip_download(self, ctx, *, package: str):
        """Download packages."""
        await self.run_pip_command(ctx, "download", package)

    @pip.command(name="uninstall")
    async def pip_uninstall(self, ctx, *, package: str):
        """Uninstall packages."""
        await self.run_pip_command(ctx, "uninstall", "-y", package)

    @pip.command(name="freeze")
    async def pip_freeze(self, ctx):
        """Output installed packages in requirements format."""
        await self.run_pip_command(ctx, "freeze")

    @pip.command(name="inspect")
    async def pip_inspect(self, ctx):
        """Inspect the Python environment."""
        await self.run_pip_command(ctx, "debug", "inspect")

    @pip.command(name="list")
    async def pip_list(self, ctx):
        """List installed packages."""
        await self.run_pip_command(ctx, "list")

    @pip.command(name="show")
    async def pip_show(self, ctx, *, package: str):
        """Show information about installed packages."""
        await self.run_pip_command(ctx, "show", package)

    @pip.command(name="check")
    async def pip_check(self, ctx):
        """Verify installed packages have compatible dependencies."""
        await self.run_pip_command(ctx, "check")

    @pip.command(name="config")
    async def pip_config(self, ctx, *, command: str):
        """Manage local and global configuration."""
        await self.run_pip_command(ctx, "config", command)

    @pip.command(name="search")
    async def pip_search(self, ctx, *, query: str):
        """Search PyPI for packages."""
        await self.run_pip_command(ctx, "search", query)

    @pip.command(name="cache")
    async def pip_cache(self, ctx, *, command: str):
        """Inspect and manage pip's wheel cache."""
        await self.run_pip_command(ctx, "cache", command)

    @pip.command(name="index")
    async def pip_index(self, ctx, *, command: str):
        """Inspect information available from package indexes."""
        await self.run_pip_command(ctx, "index", command)

    @pip.command(name="wheel")
    async def pip_wheel(self, ctx, *, requirement: str):
        """Build wheels from your requirements."""
        await self.run_pip_command(ctx, "wheel", requirement)

    @pip.command(name="hash")
    async def pip_hash(self, ctx, *, file_path: str):
        """Compute hashes of package archives."""
        await self.run_pip_command(ctx, "hash", file_path)

    @pip.command(name="completion")
    async def pip_completion(self, ctx):
        """A helper command used for command completion."""
        await self.run_pip_command(ctx, "completion")

    @pip.command(name="debug")
    async def pip_debug(self, ctx):
        """Show information useful for debugging."""
        await self.run_pip_command(ctx, "debug")

    @pip.command(name="help")
    async def pip_help(self, ctx):
        """Show help for commands."""
        await self.run_pip_command(ctx, "--help")

async def setup(bot):
    await bot.add_cog(Pip(bot))