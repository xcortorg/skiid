from datetime import datetime
import discord
from discord.ext import commands
import aiohttp


class Gang(commands.Cog):
    """Gang system to create, manage, and join gangs."""

    def __init__(self, bot):
        self.bot = bot
        self.nickname_toggle_cache = {}
        self.bot.loop.create_task(self.create_tables())
        self.gang_logs_webhook_url = "https://discord.com/api/webhooks/1330841749035417670/X8nCjROXq3CVMOuIlFtLdigomCmyG3Fwe7O1kWu2M7sZLhDw677dlG3Hx3QA5CWR2uqS"
        self.bot.loop.create_task(self.alter_gang_members_table())

    @staticmethod
    def generate_tag(gang_name: str):
        """Generate a gang tag: First and last letters in brackets."""
        return f"[{gang_name[0].upper()}{gang_name[-1].upper()}]"

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Listen for changes and auto-update nickname based on gang membership and toggle."""
        if before.nick == after.nick:
            return

        # Check if the user wants their nickname auto-updated
        if not self.nickname_toggle_cache.get(after.id, False):
            return

        # Check gang membership
        user_gang = await self.bot.db.fetchrow(
            "SELECT g.gang_name FROM gang_members m "
            "JOIN gangs g ON m.gang_name = g.gang_name WHERE m.user_id = $1",
            after.id,
        )
        if not user_gang:
            return  # User not in any gang

        # Generate tag and set nickname
        tag = self.generate_tag(user_gang["gang_name"])
        desired_nickname = f"{tag} {after.display_name}"
        if after.nick != desired_nickname:
            try:
                await after.edit(nick=desired_nickname, reason="Gang auto-tag update.")
            except discord.Forbidden:
                pass  # Bot lacks permissions to change nickname

    async def send_gang_log(self, message):
        """Send a log message via the webhook."""
        if not self.gang_logs_webhook_url:
            # No webhook URL is set
            return

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(
                self.gang_logs_webhook_url, session=session
            )
            await webhook.send(
                message, username="Gang Logger", avatar_url=self.bot.user.avatar.url
            )

    async def is_booster(self, user_id):
        # Placeholder method to check if the user is authorized (modify based on your requirements)
        return True

    def validate_gang_name(self, name):
        return True  # Placeholder validation

    async def create_tables(self):
        """Ensure the necessary tables exist in the database."""
        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS gangs (
                gang_name TEXT PRIMARY KEY,
                owner_id BIGINT NOT NULL,
                created_at TEXT NOT NULL,
                banner_url TEXT
            )
            """
        )
        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS gang_members (
                user_id BIGINT NOT NULL,
                gang_name TEXT NOT NULL,
                role TEXT NOT NULL,
                PRIMARY KEY (user_id, gang_name),
                FOREIGN KEY (gang_name) REFERENCES gangs(gang_name) ON DELETE CASCADE
            )
            """
        )

    async def alter_gang_members_table(self):
        """Ensure that the 'toggle' field exists in the gang_members table."""
        await self.bot.db.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'gang_members' AND column_name = 'toggle'
                ) THEN
                    ALTER TABLE gang_members ADD COLUMN toggle TEXT DEFAULT 'off';
                END IF;
            END $$;
            """
        )

    @commands.group(invoke_without_command=True)
    async def gang(self, ctx):
        """Base command for the Gang system."""
        return await ctx.send_help(ctx.command.qualified_name)

    @gang.command(name="toggle")
    async def gang_toggle(self, ctx):
        """Toggle the nickname tag for the user based on their gang affiliation."""
        # Check if the user is in a gang
        user_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gang_members WHERE user_id = $1", ctx.author.id
        )

        if not user_gang:
            await ctx.fail("You are not in any gang.")
            return

        gang_name = user_gang["gang_name"]

        # Check if the user has the toggle state set
        user_toggle = await self.bot.db.fetchrow(
            "SELECT toggle FROM gang_members WHERE user_id = $1 AND gang_name = $2",
            ctx.author.id,
            gang_name,
        )

        # If no toggle setting, we'll assume it's off by default
        if user_toggle is None:
            await self.bot.db.execute(
                "INSERT INTO gang_members (user_id, gang_name, role, toggle) VALUES ($1, $2, $3, $4)",
                ctx.author.id,
                gang_name,
                "Member",
                "off",
            )
            user_toggle = {"toggle": "off"}  # Default to "off"

        # Toggle action: Switch between 'on' and 'off'
        if user_toggle["toggle"] == "off":
            # Toggle to 'on', change nickname
            new_nickname = f"[{gang_name[0].upper()}{gang_name[-1].upper()}] {ctx.author.display_name}"
            try:
                await ctx.author.edit(nick=new_nickname)
            except discord.Forbidden:
                await ctx.fail("I don't have permission to change your nickname.")
                return
            # Update toggle in the database
            await self.bot.db.execute(
                "UPDATE gang_members SET toggle = 'on' WHERE user_id = $1 AND gang_name = $2",
                ctx.author.id,
                gang_name,
            )
            await ctx.success(
                f"Your gang tag has been added to your nickname: {new_nickname}"
            )

        else:
            # Toggle to 'off', revert nickname
            # Remove the gang tag from their nickname
            new_nickname = ctx.author.display_name.replace(
                f"[{gang_name[0]}{gang_name[-1]}] ", ""
            )
            try:
                await ctx.author.edit(nick=new_nickname)
            except discord.Forbidden:
                await ctx.fail("I don't have permission to change your nickname.")
                return
            # Update toggle in the database
            await self.bot.db.execute(
                "UPDATE gang_members SET toggle = 'off' WHERE user_id = $1 AND gang_name = $2",
                ctx.author.id,
                gang_name,
            )
            await ctx.success(f"Your gang tag has been removed from your nickname.")

    @gang.command(name="tag")
    async def tag_info(self, ctx):
        """View your gang's tag."""
        user_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gang_members WHERE user_id = $1",
            ctx.author.id,
        )

        if not user_gang:
            await ctx.fail("You are not in a gang.")
            return

        gang_name = user_gang["gang_name"]
        tag = self.generate_tag(gang_name)
        await ctx.success(f"Your gang tag is **{tag}**.")

    @gang.command(name="create", aliases=["gangc"])
    async def gang_create(self, ctx, gang_name: str):
        """Create a new gang."""
        # Check if the user is a booster
        is_booster = await self.bot.db.fetchrow(
            "SELECT 1 FROM boosters WHERE user_id = $1", ctx.author.id
        )

        if not is_booster:
            await ctx.fail(
                "You are not boosting [/greedbot](http://discord.gg/greedbot). Only boosters can create gangs."
            )
            return

        # Check if the gang name is 5 characters or fewer
        if len(gang_name) > 5:
            await ctx.fail(
                "The gang name must be 5 characters or fewer. Please choose a shorter name."
            )
            return

        if not self.validate_gang_name(gang_name):
            await ctx.fail(
                "The gang name contains prohibited or offensive content. Please choose another name."
            )
            return

        # Check if the user already owns a gang
        existing_ownership = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )
        if existing_ownership:
            await ctx.warning(
                f"You already own the gang '{existing_ownership['gang_name']}'. Disband it to create a new one."
            )
            return

        # Check if the gang name is already taken
        existing_gang = await self.bot.db.fetchrow(
            "SELECT 1 FROM gangs WHERE gang_name = $1", gang_name
        )
        if existing_gang:
            await ctx.fail(
                f"A gang with the name **{gang_name}** already exists. Please choose another name."
            )
            return

        # Create the gang
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await self.bot.db.execute(
            """
            INSERT INTO gangs (gang_name, owner_id, created_at, banner_url)
            VALUES ($1, $2, $3, $4)
            """,
            gang_name,
            ctx.author.id,
            created_at,
            None,
        )
        await self.bot.db.execute(
            "INSERT INTO gang_members (user_id, gang_name, role) VALUES ($1, $2, $3)",
            ctx.author.id,
            gang_name,
            "Owner",
        )

        # Log the gang creation
        await self.send_gang_log(
            f"**Gang Created**: **{gang_name}** by {ctx.author} (ID: {ctx.author.id})"
        )
        await ctx.success(
            f"Gang **{gang_name}** has been successfully created by {ctx.author.mention}."
        )

    @gang.command(name="disband", aliases=["gangd"])
    async def gang_disband(self, ctx):
        """Disband your gang."""
        owner_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )

        if not owner_gang:
            await ctx.fail("You do not own a gang to disband.")
            return

        gang_name = owner_gang["gang_name"]

        await self.bot.db.execute("DELETE FROM gangs WHERE gang_name = $1", gang_name)
        await self.bot.db.execute(
            "DELETE FROM gang_members WHERE gang_name = $1", gang_name
        )

        await ctx.success(f"The gang **{gang_name}** has been disbanded.")

    @gang.command(name="setbanner", aliases=["gangsb"])
    async def gang_set_banner(self, ctx, banner_url: str):
        """Set a banner for your gang."""
        owner_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )
        if not owner_gang:
            await ctx.fail("You do not own a gang to set a banner.")
            return

        gang_name = owner_gang["gang_name"]
        await self.bot.db.execute(
            "UPDATE gangs SET banner_url = $1 WHERE gang_name = $2",
            banner_url,
            gang_name,
        )

        # Log the banner update
        await self.send_gang_log(
            f"**Banner Updated**: Gang **{gang_name}** by {ctx.author} (ID: {ctx.author.id}) - New Banner URL: {banner_url}"
        )
        await ctx.success(f"Banner for gang **{gang_name}** has been set.")

    @gang.command(name="leave", aliases=["gangleave"])
    async def gang_leave(self, ctx):
        """Leave your current gang."""
        # Check if the user is in a gang
        user_gang = await self.bot.db.fetchrow(
            "SELECT gang_name, role FROM gang_members WHERE user_id = $1", ctx.author.id
        )

        if not user_gang:
            await ctx.fail("You are not in any gang.")
            return

        gang_name = user_gang["gang_name"]
        user_role = user_gang["role"]

        # Prevent the owner from leaving their own gang
        if user_role == "Owner":
            await ctx.fail(
                f"You are the owner of the gang **{gang_name}**. You must transfer ownership or disband the gang before leaving."
            )
            return

        # Remove the user from the gang
        await self.bot.db.execute(
            "DELETE FROM gang_members WHERE user_id = $1 AND gang_name = $2",
            ctx.author.id,
            gang_name,
        )

        # Notify success
        await ctx.success(f"You have successfully left the gang **{gang_name}**.")

        # Log the action
        await self.send_gang_log(
            f"**Member Left**: {ctx.author} (ID: {ctx.author.id}) left the gang **{gang_name}**."
        )

    @gang.command(name="info", aliases=["gangi"])
    async def gang_info(self, ctx):
        """Display information about your gang."""
        user_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gang_members WHERE user_id = $1", ctx.author.id
        )

        if not user_gang:
            await ctx.fail("You are not in a gang.")
            return

        gang_name = user_gang["gang_name"]

        gang = await self.bot.db.fetchrow(
            "SELECT owner_id, banner_url, created_at FROM gangs WHERE gang_name = $1",
            gang_name,
        )

        if not gang:
            await ctx.fail("Could not retrieve gang details.")
            return

        owner_id, banner_url, created_at = gang

        created_at_formatted = datetime.strptime(
            created_at, "%Y-%m-%d %H:%M:%S"
        ).strftime("%B %d, %Y at %I:%M %p")
        owner = ctx.guild.get_member(owner_id) or f"<@{owner_id}>"

        embed = discord.Embed(description=f"**{gang_name}**", color=self.bot.color)

        if banner_url:
            embed.set_image(url=banner_url)

        embed.add_field(name="Owner", value=f"**{owner}** 👑", inline=False)

        members = await self.bot.db.fetch(
            "SELECT user_id, role FROM gang_members WHERE gang_name = $1", gang_name
        )

        member_list = "\n".join([f"<@{m[0]}> - {m[1]}" for m in members])
        embed.add_field(name="Members", value=member_list or "None", inline=False)

        embed.set_footer(text=f"Time Created: {created_at_formatted}")

        await ctx.send(embed=embed)

    @gang.command(name="promote", aliases=["gangp"])
    async def gang_promote(self, ctx, member: discord.Member):
        """Promote a gang member to admin."""
        owner_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )

        if not owner_gang:
            await ctx.fail("You must own a gang to promote members.")
            return

        gang_name = owner_gang["gang_name"]

        member_gang = await self.bot.db.fetchrow(
            "SELECT role FROM gang_members WHERE user_id = $1 AND gang_name = $2",
            member.id,
            gang_name,
        )

        if not member_gang or member_gang["role"] == "Admin":
            await ctx.fail(
                f"{member.mention} is either not in your gang or is already an Admin."
            )
            return

        await self.bot.db.execute(
            "UPDATE gang_members SET role = 'Admin' WHERE user_id = $1 AND gang_name = $2",
            member.id,
            gang_name,
        )

        await ctx.success(f"{member.mention} has been promoted to Admin.")

    @gang.command(name="invite", aliases=["ganginv"])
    async def gang_invite(self, ctx, member: discord.Member):
        """Send an invite to a user to join your gang."""
        inviter_gang = await self.bot.db.fetchrow(
            "SELECT gang_name, role FROM gang_members WHERE user_id = $1", ctx.author.id
        )

        if not inviter_gang or inviter_gang["role"] not in ("Owner", "Admin"):
            await ctx.fail("You must be an Owner or Admin of a gang to invite members.")
            return

        gang_name = inviter_gang["gang_name"]

        member_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gang_members WHERE user_id = $1", member.id
        )

        if member_gang:
            await ctx.fail(
                f"{member.mention} is already in a gang ({member_gang['gang_name']})."
            )
            return

        embed = discord.Embed(
            title=f"Gang Invite: {gang_name}",
            description=f"{member.mention}, you have been invited to join the gang **{gang_name}** by {ctx.author.mention}.",
            color=self.bot.color,
        )

        view = discord.ui.View()

        async def accept_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                await interaction.response.send_message(
                    "This invitation is not for you.", ephemeral=True
                )
                return

            await self.bot.db.execute(
                "INSERT INTO gang_members (user_id, gang_name, role) VALUES ($1, $2, 'Member')",
                member.id,
                gang_name,
            )

            embed.title = f"{member.display_name} joined {gang_name}!"
            embed.description = (
                f"{member.mention} has accepted the invitation to join **{gang_name}**."
            )
            embed.color = self.bot.color

            await interaction.response.edit_message(embed=embed, view=None)

        async def deny_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                await interaction.response.send_message(
                    "This invitation is not for you.", ephemeral=True
                )
                return

            embed.title = f"Invitation Declined: {gang_name}"
            embed.description = (
                f"{member.mention} declined the invitation to join **{gang_name}**."
            )
            embed.color = self.bot.color

            await interaction.response.edit_message(embed=embed, view=None)

        accept_button = discord.ui.Button(
            label="Accept", style=discord.ButtonStyle.green
        )
        accept_button.callback = accept_callback

        deny_button = discord.ui.Button(label="Decline", style=discord.ButtonStyle.red)
        deny_button.callback = deny_callback

        view.add_item(accept_button)
        view.add_item(deny_button)

        await ctx.send(embed=embed, view=view)

    @gang.command(name="transfer", aliases=["gangt"])
    async def gang_transfer(self, ctx, member: discord.Member):
        """Transfer gang ownership to another member."""
        owner_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )

        if not owner_gang:
            await ctx.fail("You must own a gang to transfer ownership.")
            return

        gang_name = owner_gang["gang_name"]

        member_gang = await self.bot.db.fetchrow(
            "SELECT role FROM gang_members WHERE user_id = $1 AND gang_name = $2",
            member.id,
            gang_name,
        )

        if not member_gang:
            await ctx.fail(f"{member.mention} is not a member of your gang.")
            return

        await self.bot.db.execute(
            "UPDATE gangs SET owner_id = $1 WHERE gang_name = $2", member.id, gang_name
        )
        await self.bot.db.execute(
            "UPDATE gang_members SET role = 'Owner' WHERE user_id = $1 AND gang_name = $2",
            member.id,
            gang_name,
        )
        await self.bot.db.execute(
            "UPDATE gang_members SET role = 'Member' WHERE user_id = $1 AND gang_name = $2",
            ctx.author.id,
            gang_name,
        )

        await ctx.success(
            f"Gang ownership of **{gang_name}** has been transferred to {member.mention}."
        )

    @gang.command(name="delete", aliases=["gangdel"])
    @commands.is_owner()
    async def gang_delete(self, ctx, gang_name: str):
        """Delete a gang manually (Owner only)."""
        # Check if the gang exists and get the owner
        gang = await self.bot.db.fetchrow(
            "SELECT gang_name, owner_id FROM gangs WHERE gang_name = $1", gang_name
        )

        if not gang:
            await ctx.fail(f"The gang **{gang_name}** does not exist.")
            return

        # Delete gang from both tables
        await self.bot.db.execute(
            "DELETE FROM gang_members WHERE gang_name = $1", gang_name
        )
        await self.bot.db.execute("DELETE FROM gangs WHERE gang_name = $1", gang_name)

        # Log the gang deletion
        await self.send_gang_log(
            f"**Gang Deleted**: The gang **{gang_name}** was manually deleted by {ctx.author} (ID: {ctx.author.id})."
        )

        await ctx.success(f"The gang **{gang_name}** has been successfully deleted.")


async def setup(bot):
    await bot.add_cog(Gang(bot))
