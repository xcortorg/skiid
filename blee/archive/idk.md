// ... existing code ...

    async def compile(self, **kwargs):
        """Attempt to compile the script into an object"""
        await self.resolve_variables(**kwargs)
        await self.resolve_objects(**kwargs)
        try:
            self.script = await self.parser.parse(self.script)
            for script in self.script.split("{embed}"):
                if script := script.strip():
                    self.objects["embed"] = Embed()
                    await self.embed_parser.parse(script)
                    if embed := self.objects.pop("embed", None):
                        self.objects["embeds"].append(embed)
            self.objects.pop("embed", None)
        except Exception as error:
            if kwargs.get("validate"):
                if type(error) is TypeError:
                    function = [
                        tag
                        for tag in self.embed_parser.tags
                        if tag.callback.__name__ == error.args[0].split("(")[0]
                    ][0].name
                    parameters = str(error).split("'")[1].split(", ")
                    raise CommandError(
                        f"The **{function}** method requires the `{parameters[0]}` parameter"
                    ) from error
                raise error

        validation = any(self.objects.values())
        if not validation or not self.objects.get("embeds"):
            if kwargs.get("validate"):
                raise CommandError("You must include an embed in your message")
            self.objects["content"] = self.script
        if kwargs.get("validate"):
            if self.objects.get("embeds"):
                self._type = "embed"
            self.objects: dict = dict(content=None, embeds=[], stickers=[])
            self.script = self._script
        return validation

// ... existing code ...






loti music cog 


def format_duration(time_input: Union[int, float], is_milliseconds: bool = True) -> str:
    """
    Convert a given duration (in seconds or milliseconds) into a formatted duration string.

    Args:
        time_input (Union[int, float]): The total duration, either in seconds or milliseconds.
        is_milliseconds (bool): Specifies if the input is in milliseconds (default is True).

    Returns:
        str: The formatted duration in hours, minutes, seconds, and milliseconds.
    """
    if is_milliseconds:
        total_seconds = time_input / 1000
    else:
        total_seconds = time_input

    seconds = int(total_seconds)

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"

def pluralize(text: str, count: int) -> str:
    """
    Pluralize a string based on the count.

    Args:
        text (str): The string to pluralize.
        count (int): The count to determine if the string should be pluralized.

    Returns:
        str: The pluralized string.
    """
    return text + ("s" if count != 1 else "")






class CogMeta(Cog):
    bot: "Felony"

    def __init__(self, bot: "Felony") -> None:
        self.bot = bot
        super().__init__()








    @command()
    async def emojiinfo(
        self, ctx: Context, potential_emoji: Union[Message, PartialEmoji]
    ) -> Message:
        """
        Display information about an emoji.
        """
        _CUSTOM_EMOJI_RE = re.compile(
            r"<?(?:(?P<animated>a)?:)?(?P<name>[A-Za-z0-9\_]+):(?P<id>[0-9]{13,20})>?"
        )

        if isinstance(potential_emoji, Message) and (
            match := _CUSTOM_EMOJI_RE.match(potential_emoji.content)
        ):
            emoji = PartialEmoji.from_dict(match.groupdict())
        elif isinstance(potential_emoji, PartialEmoji):
            emoji = potential_emoji
        else:
            return await ctx.warn(
                "There were **no** emojis in the **requested message**."
            )

        assert emoji.id, "Emoji must have an ID"
        guild = (guild := self.bot.get_emoji(emoji.id)) and guild.guild

        return await ctx.embed(
            title=emoji.name,
            image=emoji.url + "?size=1024",
            fields=[
                {"name": "Emoji ID", "value": f"`{emoji.id}`", "inline": True},
                {
                    "name": "Guild",
                    "value": f'`{guild and guild.name or "Unknown"}`',
                    "inline": True,
                },
                {
                    "name": "Image URL",
                    "value": f"[**Click here to open the image**]({emoji.url})",
                    "inline": False,
                },
            ],
        )




    @command(aliases=("char",))
    async def charinfo(self, ctx: Context, *, characters: str) -> Message:
        """View information about unicode characters."""

        def to_string(char: str):
            digit = f"{ord(char):x}"
            name = unicodedata.name(char, "Name not found.")

            return f"[`\\U{digit:>08}`](http://www.fileformat.info/info/unicode/char/{digit}): {name}"

        unicode = list(map(to_string, characters))
        embed = Embed(title="Character Information")

        paginator = Paginator(ctx, unicode, embed, per_page=5, counter=False)
        return await paginator.start()