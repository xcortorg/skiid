    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        with suppress((HTTPException), (KeyError)):
            # Clear all votes
            self.pause_votes = []
            self.skip_votes = []
            self.resume_votes = []
            self.shuffle_votes = []
            self.stop_votes = []
            
            # Clear queues
            self.queue.clear()
            self.history.clear()
            
            # Remove the player instance from the cog's players dict
            if self.context and hasattr(self.context.cog, 'players'):
                self.context.cog.players.pop(self.context.guild.id, None)
            
            # Delete the controller message and disconnect
            if self.controller:
                await self.controller.delete()
            
            await self.destroy()


This updated teardown method:
Clears all vote lists
Clears both the queue and history
Removes the player instance from the cog's players dictionary
Deletes the controller message
Disconnects and destroys the player
This ensures a complete cleanup when the player is stopped or encounters an error, preventing any memory leaks or ghost instances.






@command(aliases=("p",))
async def play(self, ctx: Context, *, query: str = None) -> Optional[Message]:
    """
    Play the requested song via a query or attachment in your current voice channel.
    You can also reply to a message with an attachment.
    """
    
    assert isinstance(ctx.author, Member), "Author must be a member."

    # Handle attachments from current message or referenced message
    if not query:
        if ctx.message.attachments:
            query = ctx.message.attachments[0].url
        elif hasattr(ctx.message.reference, 'resolved') and ctx.message.reference.resolved:
            referenced_msg = ctx.message.reference.resolved
            if hasattr(referenced_msg, 'attachments') and referenced_msg.attachments:
                query = referenced_msg.attachments[0].url

    if not query:
        return await ctx.warn("Please provide either a **query** or an **attachment**.")

    # Get existing player or create new one
    player = self.players.get(ctx.guild.id)
    if not player:
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.warn(
                "To **play** a song, you must be in a voice channel."
            )

        # Create new player for this guild
        await ctx.author.voice.channel.connect(cls=Player)
        player = cast(Player, ctx.voice_client)
        await player.set_context(ctx)
        self.players[ctx.guild.id] = player

    if player.channel != getattr(ctx.author.voice, "channel", None):
        return await ctx.warn(
            "You must be in the same voice channel as the bot to **play** a song."
        )

    if not (results := await player.get_tracks(query, ctx=ctx)):
        return await ctx.warn(f"Couldn't find any results for **{query}**.")

    tracks = results.tracks if isinstance(results, Playlist) else [results[0]]

    for track in tracks:
        player.queue.put(track)

    await ctx.neutral(
        f"{(isinstance(results, Playlist) and 'Added' or 'Added')} `{(isinstance(results, Playlist) and results.name or results[0].title)}` to `{(isinstance(results, Playlist) and 'queue' or '1st')}` in the queue"
    )

    if not player.is_playing:
        await player.do_next()



Uses the self.players dictionary to store/retrieve guild-specific players
Creates a new player instance if one doesn't exist for the guild
Stores the player in the guild-specific dictionary
Uses the guild's player instance for all operations
This ensures that each guild maintains its own separate queue and player state. Make sure you have the self.players dictionary initialized in the __init__ method of the Music cog as shown in the previous response.