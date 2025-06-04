// ... existing imports ...

class Servers(Cog):
    // ... existing code ...

    @Cog.listener("on_user_message")
    async def sticky_message_dispatcher(self, ctx: Context, message: Message):
        """Dispatch the sticky message event while waiting for the activity scheduler"""
        settings = await Settings.fetch(self.bot, message.guild)
        data = await settings.get_sticky_message(message.channel)
        
        if not data or data["message_id"] == message.id:
            return

        key = hash(f"{message.guild.id}:{message.channel.id}")
        if not self.bot.sticky_locks.get(key):
            self.bot.sticky_locks[key] = Lock()
        bucket = self.bot.sticky_locks.get(key)

        async with bucket:
            try:
                await self.bot.wait_for(
                    "message",
                    check=lambda m: m.channel == message.channel,
                    timeout=data.get("schedule") or 0,
                )
            except TimeoutError:
                pass
            else:
                return

            with suppress(HTTPException):
                await message.channel.get_partial_message(data["message_id"]).delete()

            new_message = await ensure_future(
                EmbedScript(data["message"]).send(
                    message.channel,
                    bot=self.bot,
                    guild=message.guild,
                    channel=message.channel,
                    user=message.author,
                )
            )
            await settings.update_sticky_message_id(message.channel, new_message.id)

    @Cog.listener("on_member_join")
    async def welcome_message(self: "Servers", member: Member):
        """Send a welcome message for a member which joins the server"""
        settings = await Settings.fetch(self.bot, member.guild)
        welcome_messages = await settings.get_welcome_messages()

        for data in welcome_messages:
            channel: TextChannel
            if not (channel := member.guild.get_channel(data["channel_id"])):
                continue

            await ensure_future(
                EmbedScript(data["message"]).send(
                    channel,
                    bot=self.bot,
                    guild=member.guild,
                    channel=channel,
                    user=member,
                    allowed_mentions=AllowedMentions(
                        everyone=True,
                        users=True,
                        roles=True,
                        replied_user=False,
                    ),
                    delete_after=data.get("self_destruct"),
                )
            )

    @group(
        name="welcome",
        usage="(subcommand) <args>",
        example="add #hi Hi {user.mention}! --self_destruct 10",
        aliases=["welc"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def welcome(self: "Servers", ctx: Context):
        """Set up welcome messages in one or multiple channels"""
        await ctx.send_help()

    @welcome.command(
        name="add",
        usage="(channel) (message)",
        example="#chat Hi {user.mention} <3",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        message: str,
    ):
        """Add a welcome message for a channel"""
        # Parse self_destruct from message if present
        self_destruct = None
        message_content = message
        
        if '--self_destruct' in message:
            try:
                parts = message.split('--self_destruct')
                message_content = parts[0].strip()
                self_destruct = int(parts[1].strip())
                
                if self_destruct < 6 or self_destruct > 120:
                    return await ctx.warn(
                        "The **self destruct** time must be between **6** and **120** seconds"
                    )
            except (IndexError, ValueError):
                return await ctx.warn("Invalid self_destruct format. Example: --self_destruct 10")

        # Convert message content to EmbedScript
        try:
            embed_message = await EmbedScriptValidator().convert(ctx, message_content)
        except Exception as e:
            return await ctx.warn(f"Invalid message format: {str(e)}")

        settings = await Settings.fetch(self.bot, ctx.guild)
        try:
            await settings.add_welcome_message(channel, str(embed_message), self_destruct)
        except Exception:
            return await ctx.warn(f"There is already a **welcome message** for {channel.mention}")

        await ctx.approve(
            f"Created {embed_message.type(bold=False)} **welcome message** for {channel.mention}"
            + (f"\n> Which will self destruct after **{Plural(self_destruct):second}**" if self_destruct else "")
        )

    @welcome.command(
        name="remove",
        usage="(channel)",
        example="#general",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_remove(self, ctx: Context, channel: TextChannel | Thread):
        """Remove a welcome message for a channel"""
        settings = await Settings.fetch(self.bot, ctx.guild)
        if not await settings.remove_welcome_message(channel):
            return await ctx.warn(f"There isn't a **welcome message** for {channel.mention}")

        return await ctx.approve(f"Removed the **welcome message** for {channel.mention}")

    @welcome.command(
        name="view",
        usage="(channel)",
        example="#chat",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_view(self, ctx: Context, channel: TextChannel | Thread):
        """View a welcome message for a channel"""
        settings = await Settings.fetch(self.bot, ctx.guild)
        data = await settings.get_welcome_message(channel)
        
        if not data:
            return await ctx.warn(f"There isn't a **welcome message** for {channel.mention}")

        await EmbedScript(data["message"]).send(
            ctx.channel,
            bot=self.bot,
            guild=ctx.guild,
            channel=ctx.channel,
            user=ctx.author,
            delete_after=data.get("self_destruct"),
        )

    @welcome.command(name="reset", aliases=["clear"])
    @has_permissions(manage_guild=True)
    async def welcome_reset(self, ctx: Context):
        """Reset all welcome channels"""
        await ctx.prompt("Are you sure you want to remove all **welcome channels**?")
        
        settings = await Settings.fetch(self.bot, ctx.guild)
        await settings.reset_welcome_messages()
        return await ctx.approve("Removed all **welcome channels**")

    @welcome.command(name="list")
    @has_permissions(manage_guild=True)
    async def welcome_list(self, ctx: Context):
        """View all welcome channels"""
        settings = await Settings.fetch(self.bot, ctx.guild)
        welcome_messages = await settings.get_welcome_messages()
        
        channels = [
            self.bot.get_channel(row["channel_id"]).mention
            for row in welcome_messages
            if self.bot.get_channel(row["channel_id"])
        ]

        if not channels:
            return await ctx.warn("No **welcome channels** have been set up")

        await ctx.paginate(
            Embed(title="Welcome Channels", description="\n".join(channels))
        )

    @group(
        usage="(subcommand) <args>",
        example="#channel hello",
        aliases=["sticky", "sm"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def stickymessage(self, ctx: Context):
        """Set up sticky messages in one or multiple channels"""
        await ctx.send_help()

    @stickymessage.command(
        name="add",
        usage="(channel) (message)",
        example="#general Hi --schedule 30s",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        message: str,
    ):
        """Add a sticky message for a channel"""
        # Parse schedule and message content
        schedule = None
        message_content = message
        
        if '--schedule' in message:
            try:
                parts = message.split('--schedule')
                message_content = parts[0].strip()
                schedule_str = parts[1].strip().split()[0]
                
                schedule = await TimeConverter().convert(ctx, schedule_str)
                if schedule.seconds < 30 or schedule.seconds > 3600:
                    return await ctx.warn(
                        "The **activity schedule** must be between **30 seconds** and **1 hour**"
                    )
            except (IndexError, ValueError):
                return await ctx.warn("Invalid schedule format. Example: --schedule 30s")

        # Convert message content to EmbedScript
        try:
            embed_message = await EmbedScriptValidator().convert(ctx, message_content)
        except Exception as e:
            return await ctx.warn(f"Invalid message format: {str(e)}")

        settings = await Settings.fetch(self.bot, ctx.guild)
        
        # Send initial message
        sticky_message = await embed_message.send(
            channel,
            bot=self.bot,
            guild=ctx.guild,
            channel=channel,
            user=ctx.author,
        )

        try:
            await settings.add_sticky_message(
                channel, 
                str(embed_message), 
                sticky_message.id,
                schedule.seconds if schedule else None
            )
        except Exception:
            return await ctx.warn(f"There is already a **sticky message** for {channel.mention}")

        await ctx.approve(
            f"Created {embed_message.type(bold=False)} [**sticky message**]({sticky_message.jump_url}) for {channel.mention}"
            + (f" with an **activity schedule** of **{schedule}**" if schedule else "")
        )

    @stickymessage.command(
        name="remove",
        usage="(channel)",
        example="#general",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_remove(self, ctx: Context, channel: TextChannel | Thread):
        """Remove a sticky message for a channel"""
        settings = await Settings.fetch(self.bot, ctx.guild)
        if not await settings.remove_sticky_message(channel):
            return await ctx.warn(f"No **sticky message** exists for {channel.mention}")

        await ctx.approve(f"Removed the **sticky message** for {channel.mention}")

    @stickymessage.command(
        name="view",
        usage="(channel)",
        example="#general",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_view(self, ctx: Context, channel: TextChannel | Thread):
        """View a sticky message for a channel"""
        settings = await Settings.fetch(self.bot, ctx.guild)
        data = await settings.get_sticky_message(channel)
        
        if not data:
            return await ctx.warn(f"There isn't a **sticky message** for {channel.mention}")

        await EmbedScript(data["message"]).send(
            ctx.channel,
            bot=self.bot,
            guild=ctx.guild,
            channel=ctx.channel,
            user=ctx.author,
        )

    @stickymessage.command(name="reset", aliases=["clear"])
    @has_permissions(manage_guild=True)
    async def sticky_reset(self, ctx: Context):
        """Reset all sticky messages"""
        settings = await Settings.fetch(self.bot, ctx.guild)
        
        if not await settings.get_sticky_messages():
            return await ctx.warn("No **sticky messages** have been set up")

        await ctx.prompt("Are you sure you want to remove all **sticky messages**?")
        await settings.reset_sticky_messages()
        await ctx.approve("Removed all **sticky messages**")

    @stickymessage.command(name="list", aliases=["show", "all"])
    @has_permissions(manage_guild=True)
    async def sticky_list(self, ctx: Context):
        """View all sticky messages"""
        settings = await Settings.fetch(self.bot, ctx.guild)
        sticky_messages = await settings.get_sticky_messages()
        
        messages = [
            f"{channel.mention} - [`{row['message_id']}`]({channel.get_partial_message(row['message_id']).jump_url})"
            for row in sticky_messages
            if (channel := self.bot.get_channel(row.get("channel_id")))
        ]

        if not messages:
            return await ctx.warn("No **sticky messages** have been set up")

        await ctx.paginate(
            Embed(title="Sticky Messages", description="\n".join(messages))
        )