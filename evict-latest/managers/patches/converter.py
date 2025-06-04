import discord.ext.commands as commands

original_bad_argument_str = commands.BadArgument.__str__

def custom_bad_argument_str(self):
    msg = str(self)
    
    if "Converting to" in msg:
        if "int" in msg:
            return "Please provide a valid number"
        elif "Member" in msg:
            return "I couldn't find that member in the server"
        elif "Role" in msg:
            return "I couldn't find that role in the server"
        elif "TextChannel" in msg:
            return "I couldn't find that channel in the server"
        elif "Emoji" in msg:
            return "I couldn't find that emoji"
        elif "User" in msg:
            return "I couldn't find that user"
    
    return original_bad_argument_str(self)

commands.BadArgument.__str__ = custom_bad_argument_str