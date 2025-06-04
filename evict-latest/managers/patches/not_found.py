import discord.errors

original_str = discord.errors.NotFound.__str__

def custom_not_found_str(self):
    if not hasattr(self, 'response'):
        return original_str(self)
    
    path = self.response.url.path
    if '/messages/' in path:
        return "That message no longer exists or was deleted"
    elif '/members/' in path:
        return "That user is not in the server"
    elif '/channels/' in path:
        return "That channel no longer exists or was deleted"
    elif '/webhooks/' in path:
        return "That webhook no longer exists or was deleted"
    elif '/users/' in path:
        return "That user does not exist"
    elif '/roles/' in path:
        return "That role no longer exists"
    elif '/emojis/' in path:
        return "That emoji no longer exists"
    
    return original_str(self)

discord.errors.NotFound.__str__ = custom_not_found_str