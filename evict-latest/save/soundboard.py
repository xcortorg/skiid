# import logging
# from discord.state import ConnectionState

# log = logging.getLogger(__name__)
# old_parse_guild_soundboard = ConnectionState.parse_guild_soundboard_sounds_update

# def parse_guild_soundboard_sounds_update(self, data):
#   try:
#     guild_id = int(data['guild_id'])
#     guild = self._get_guild(guild_id)
#     if guild is None:
#       log.debug(f"GUILD_SOUNDBOARD_SOUNDS_UPDATE referencing unknown guild ID: {guild_id}")
#       return

#     for raw_sound in data.get('soundboard_sounds', []):
#       try:
#         if isinstance(raw_sound, dict):
#           sound_id = int(raw_sound.get('sound_id', 0))
#           sound = guild.get_soundboard_sound(sound_id)
#           if sound is not None:
#             self._update_and_dispatch_sound_update(sound, raw_sound)
#           else:
#             log.debug(f"Unknown sound ID: {sound_id} for guild {guild_id}")
#         else:
#           log.debug(f"Malformed sound data (not a dictionary): {raw_sound}")
#       except (KeyError, TypeError, ValueError) as e:
#         log.debug(f"Error processing sound data: {e}")
#         continue

#   except (KeyError, TypeError, ValueError) as e:
#     log.debug(f"Received malformed soundboard update: {data}, error: {e}")
#     pass

# ConnectionState.parse_guild_soundboard_sounds_update = parse_guild_soundboard_sounds_update