import asyncio
from collections import defaultdict

from discord import (CategoryChannel, Embed, Member, PermissionOverwrite,
                     VoiceChannel, VoiceState)
from discord.ext.commands import (Cog, bot_has_guild_permissions, command,
                                  has_guild_permissions, hybrid_group)
from tools.bot import Akari
from tools.handlers.embedbuilder import EmbedBuilder
from tools.helpers import AkariContext
from tools.persistent.vm import ButtonScript, VoiceMasterView
from tools.predicates import check_vc_owner, is_vm, rename_cooldown


class Voicemaster(Cog):
    def __init__(self, bot: Akari):
        self.bot = bot
        self.description = "VoiceMaster commands"
        self.locks = defaultdict(asyncio.Lock)
        self.values = [
            ("<:lock:1234223571694518333>", "`lock` the voice channel"),
            ("<:unlock:1234223586412073011>", "`unlock` the voice channel"),
            ("<:ghost:1234223641869156362>", "`hide` the voice channel"),
            ("<:unghost:1234223631056244847>", "`reveal` the voice channel"),
            ("<:rename:1234223687679479879>", "`rename` the voice channel"),
            ("<:minus:1234223725004460053>", "`decrease` the member limit"),
            ("<:plus:1234223750266880051>", "`increase` the member limit"),
            ("<:info:1234223791949746287>", "`info` about the voice channel"),
            ("<:kick:1234223809876463657>", "`kick` someone from the voice channel"),
            ("<:claim:1234223830667624528>", "`claim` the voice channel"),
        ]

    async def get_channel_categories(
        self, channel: VoiceChannel, member: Member
    ) -> bool:
        """
        Check if there are maximum channels created in the voicemaster category
        """

        if len(channel.category.channels) == 50:
            await member.move_to(channel=None)

        return len(channel.category.channels) == 50

    async def get_channel_overwrites(
        self, channel: VoiceChannel, member: Member
    ) -> bool:
        """
        Check if the channel is locked by command. kicking admins that are not permitted
        """

        if not member.bot:
            if che := await self.bot.db.fetchrow(
                "SELECT * FROM vcs WHERE voice = $1", channel.id
            ):
                if che["user_id"] != member.id:
                    if (
                        channel.overwrites_for(channel.guild.default_role).connect
                        == False
                    ):
                        if (
                            channel.overwrites_for(member).connect == False
                            or channel.overwrites_for(member).connect is None
                        ):
                            if member.id != member.guild.owner_id:
                                try:
                                    return await member.move_to(
                                        channel=None,
                                        reason="not allowed to join this voice channel",
                                    )
                                except:
                                    pass

    async def create_temporary_channel(
        self, member: Member, category: CategoryChannel
    ) -> None:
        """
        Create a custom voice master voice channel
        """

        channel = await member.guild.create_voice_channel(
            name=f"{member.name}'s lounge",
            category=category,
            reason="creating temporary voice channel",
            overwrites=category.overwrites,
        )

        await member.move_to(channel=channel)
        await self.bot.db.execute(
            "INSERT INTO vcs VALUES ($1,$2)", member.id, channel.id
        )
        return None

    async def delete_temporary_channel(self, channel: VoiceChannel) -> None:
        """
        Delete a custom voice master channel
        """

        if await self.bot.db.fetchrow("SELECT * FROM vcs WHERE voice = $1", channel.id):
            if len(channel.members) == 0:
                await self.bot.db.execute(
                    "DELETE FROM vcs WHERE voice = $1", channel.id
                )
                if channel:
                    self.bot.cache.delete(f"vc-bucket-{channel.id}")
                    await channel.delete(reason="no one in the temporary voice channel")

        return None

    @Cog.listener()
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        if (
            member.guild.me.guild_permissions.administrator
            and before.channel != after.channel
        ):
            if check := await self.bot.db.fetchrow(
                "SELECT * FROM voicemaster WHERE guild_id = $1", member.guild.id
            ):
                jtc = int(check["channel_id"])

                if not before.channel and after.channel:
                    if after.channel.id == jtc:

                        if await self.get_channel_categories(after.channel, member):
                            return

                        return await self.create_temporary_channel(
                            member, after.channel.category
                        )
                    else:
                        return await self.get_channel_overwrites(after.channel, member)

                elif before.channel and after.channel:
                    if before.channel.id == jtc:
                        return

                    if before.channel.category == after.channel.category:
                        if after.channel.id == jtc:
                            if await self.bot.db.fetchrow(
                                "SELECT * FROM vcs WHERE voice = $1", before.channel.id
                            ):
                                if len(before.channel.members) == 0:
                                    return await member.move_to(channel=before.channel)

                            if await self.get_channel_categories(after.channel, member):
                                return

                            return await self.create_temporary_channel(
                                member, after.channel.category
                            )
                        elif before.channel.id != after.channel.id:
                            await self.get_channel_overwrites(after.channel, member)
                            await self.delete_temporary_channel(before.channel)
                    else:
                        if after.channel.id == jtc:
                            if (
                                await self.get_channel_categories(after.channel, member)
                                is True
                            ):
                                return

                            return await self.create_temporary_channel(
                                member, after.channel.category
                            )
                        else:
                            await self.get_channel_overwrites(after.channel, member)
                            await self.delete_temporary_channel(before.channel)

                elif before.channel and not after.channel:
                    if before.channel.id == jtc:
                        return

                    await self.delete_temporary_channel(before.channel)

    @hybrid_group(invoke_without_command=True, aliases=["vm"])
    async def voicemaster(self, ctx: AkariContext):
        """
        Create custom voice channels
        """

        await ctx.create_pages()

    @voicemaster.command(name="setup", brief="administrator")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    @is_vm()
    async def vm_setup(self, ctx: AkariContext):
        """
        Configure the voicemaster module
        """

        async with self.locks[ctx.guild.id]:
            mes = await ctx.reply(
                embed=Embed(
                    color=self.bot.color,
                    description=f"{ctx.author.mention}: Creating the VoiceMaster interface",
                )
            )
            await self.bot.db.execute(
                "DELETE FROM vm_buttons WHERE guild_id = $1", ctx.guild.id
            )
            category = await ctx.guild.create_category(
                name="voicemaster", reason="voicemaster category created"
            )
            voice = await ctx.guild.create_voice_channel(
                name="join to create",
                category=category,
                reason="voicemaster channel created",
            )
            text = await ctx.guild.create_text_channel(
                name="interface",
                category=category,
                reason="voicemaster interface created",
                overwrites={
                    ctx.guild.default_role: PermissionOverwrite(send_messages=False)
                },
            )
            embed = Embed(
                color=self.bot.color,
                title="VoiceMaster Interface",
                description=f"Control the voice channels created from {voice.mention}",
            )
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text="The Akari Team")
            embed.add_field(
                name="usage", value="\n".join(f"{x[0]} - {x[1]}" for x in self.values)
            )
            view = VoiceMasterView(self.bot)
            await view.add_default_buttons(ctx.guild)
            await text.send(embed=embed, view=view)
            await self.bot.db.execute(
                """
          INSERT INTO voicemaster 
          VALUES ($1,$2,$3)
          """,
                ctx.guild.id,
                voice.id,
                text.id,
            )
            return await mes.edit(
                embed=Embed(
                    color=self.bot.yes_color,
                    description=f"{self.bot.yes} {ctx.author.mention}: Succesfully configured the VoiceMaster module",
                )
            )

    @voicemaster.command(name="unsetup", brief="administrator")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def vm_unsetup(self, ctx: AkariContext):
        """
        Remove the voicemaster module
        """

        async with self.locks[ctx.guild.id]:
            check = await self.bot.db.fetchrow(
                "SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id
            )
            if not check:
                return await ctx.warning("VoiceMaster is **not** configured")

            mes = await ctx.reply(
                embed=Embed(
                    color=self.bot.color,
                    description=f"{ctx.author.mention}: Disabling the VoiceMaster interface",
                )
            )

            voice = ctx.guild.get_channel(check["channel_id"])
            if voice:
                for channel in voice.category.channels:
                    if channel:
                        await channel.delete(
                            reason=f"VoiceMaster module disabled by {ctx.author}"
                        )
                await voice.category.delete(
                    reason=f"VoiceMaster module disabled by {ctx.author}"
                )

            await self.bot.db.execute(
                "DELETE FROM voicemaster WHERE guild_id = $1", ctx.guild.id
            )
            await self.bot.db.execute(
                "DELETE FROM vm_buttons WHERE guild_id = $1", ctx.guild.id
            )
            return await mes.edit(
                embed=Embed(
                    color=self.bot.yes_color,
                    description=f"{self.bot.yes} {ctx.author.mention}: Succesfully disabled the VoiceMaster module",
                )
            )

    @command(brief="administrator")
    @has_guild_permissions(administrator=True)
    async def interface(self, ctx: AkariContext, *, code: str = None):
        """
        Create a custom voice master interface
        """

        await self.bot.db.execute(
            "DELETE FROM vm_buttons WHERE guild_id = $1", ctx.guild.id
        )
        view = VoiceMasterView(self.bot)
        if not code:
            embed = (
                Embed(
                    color=self.bot.color,
                    title="VoiceMaster Interface",
                    description=f"Control the voice channels created by the bot",
                )
                .set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
                .set_thumbnail(url=self.bot.user.display_avatar.url)
                .set_footer(text="The Akari Team")
                .add_field(
                    name="usage",
                    value="\n".join(f"{x[0]} - {x[1]}" for x in self.values),
                )
            )
            await view.add_default_buttons(ctx.guild)
            return await ctx.reply(embed=embed, view=view)

        items = ButtonScript.script(EmbedBuilder().embed_replacement(ctx.author, code))

        if len(items[2]) == 0:
            await view.add_default_buttons(ctx.guild)
        else:
            for item in items[2]:
                await view.add_button(
                    ctx.guild, item[0], label=item[1], emoji=item[2], style=item[3]
                )

        await ctx.reply(content=items[0], embed=items[1], view=view)

    @hybrid_group(aliases=["vc"], invoke_without_command=True)
    async def voice(self, ctx):
        """
        Manage your voice channel using commands
        """

        await ctx.create_pages()

    @voice.command(brief="vc owner")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def lock(self, ctx: AkariContext):
        """
        Lock the voice channel
        """

        overwrite = ctx.author.voice.channel.overwrites_for(ctx.guild.default_role)
        overwrite.connect = False
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"Channel locked by {ctx.author}",
        )
        return await ctx.success(f"locked <#{ctx.author.voice.channel.id}>")

    @voice.command(help="config", brief="vc owner")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def unlock(self, ctx: AkariContext):
        """
        Unlock the voice channel
        """

        overwrite = ctx.author.voice.channel.overwrites_for(ctx.guild.default_role)
        overwrite.connect = True
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"Channel unlocked by {ctx.author}",
        )
        return await ctx.success(f"Unlocked <#{ctx.author.voice.channel.id}>")

    @voice.command(brief="vc owner")
    @check_vc_owner()
    @rename_cooldown()
    @bot_has_guild_permissions(manage_channels=True)
    async def rename(self, ctx: AkariContext, *, name: str):
        """
        Rename the voice channel
        """

        await ctx.author.voice.channel.edit(name=name)
        return await ctx.success(f"Renamed the voice channel to **{name}**")

    @voice.command(brief="vc owner")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def hide(self, ctx: AkariContext):
        """
        Hide the voice channel
        """

        overwrite = ctx.author.voice.channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = False
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"Channel hidden by {ctx.author}",
        )
        return await ctx.success(f"Hidden <#{ctx.author.voice.channel.id}>")

    @voice.command(brief="vc owner")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def reveal(self, ctx: AkariContext):
        """
        Reveal the voice channel
        """

        overwrite = ctx.author.voice.channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = True
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"Channel revealed by {ctx.author}",
        )
        return await ctx.success(f"Revealed <#{ctx.author.voice.channel.id}>")

    @voice.command(brief="vc owner")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def permit(self, ctx: AkariContext, *, member: Member):
        """
        let someone join your locked voice channel
        """

        await ctx.author.voice.channel.set_permissions(member, connect=True)
        return await ctx.success(
            f"{member.mention} is allowed to join <#{ctx.author.voice.channel.id}>"
        )

    @voice.command(brief="vc owner")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def reject(self, ctx: AkariContext, *, member: Member):
        """
        Restrict someone from joining your voice channel
        """

        if member.id == ctx.author.id:
            return await ctx.reply("why would u wanna kick urself >_<")

        if member in ctx.author.voice.channel.members:
            await member.move_to(channel=None)

        await ctx.author.voice.channel.set_permissions(member, connect=False)
        return await ctx.success(
            f"{member.mention} is not allowed to join <#{ctx.author.voice.channel.id}> anymore"
        )

    @voice.command(brief="vc owner")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def kick(self, ctx: AkariContext, *, member: Member):
        """
        Kick a membert from your voice channel
        """

        if member.id == ctx.author.id:
            return await ctx.reply("why would u wanna kick urself >_<")

        if not member in ctx.author.voice.channel.members:
            return await ctx.error(f"{member.mention} isn't in **your** voice channel")

        await member.move_to(channel=None)
        return await ctx.success(
            f"{member.mention} got kicked from <#{ctx.author.voice.channel.id}>"
        )

    @voice.command(help="config")
    async def claim(self, ctx: AkariContext):
        """
        Claim the voice channel ownership
        """

        if not ctx.author.voice:
            return await ctx.warning("You are **not** in a voice channel")

        check = await self.bot.db.fetchrow(
            "SELECT user_id FROM vcs WHERE voice = $1", ctx.author.voice.channel.id
        )

        if not check:
            return await ctx.warning(
                "You are **not** in a voice channel made by the bot"
            )

        if ctx.author.id == check[0]:
            return await ctx.warning("You are the **owner** of this voice channel")

        if check[0] in [m.id for m in ctx.author.voice.channel.members]:
            return await ctx.warning("The owner is still in the voice channel")

        await self.bot.db.execute(
            "UPDATE vcs SET user_id = $1 WHERE voice = $2",
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        return await ctx.success("**You** are the new owner of this voice channel")

    @voice.command(brief="vc owner")
    @check_vc_owner()
    async def transfer(self, ctx: AkariContext, *, member: Member):
        """
        Transfer the voice channel ownership to another member
        """

        if not member in ctx.author.voice.channel.members:
            return await ctx.warning(f"{member.mention} is not in your voice channel")

        if member == ctx.author:
            return await ctx.warning(
                "You are already the **owner** of this **voice channel**"
            )

        await self.bot.db.execute(
            "UPDATE vcs SET user_id = $1 WHERE voice = $2",
            member.id,
            ctx.author.voice.channel.id,
        )
        return await ctx.success(f"Transfered the voice ownership to {member.mention}")

    @voice.command(name="status", brief="vc owner")
    @check_vc_owner()
    async def voice_status(self, ctx: AkariContext, *, status: str):
        """
        set your voice channel status
        """

        if len(status) > 500:
            return await ctx.warning(f"Status can't be over **500 characters**")

        await ctx.author.voice.channel.edit(status=status)
        await ctx.message.add_reaction("✅")


async def setup(bot) -> None:
    await bot.add_cog(Voicemaster(bot))
