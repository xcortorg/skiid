import discord.errors
import discord.ext.commands as commands

original_str = discord.errors.Forbidden.__str__

def custom_forbidden_str(self):
    if self.code == 50013:
        if hasattr(self, 'response'):
            path = self.response.url.path.lower()
            
            if '/roles/' in path and '/members/' in path:
                return "I'm missing the `manage_roles` permission!"
            elif '/bans/' in path:
                return "I'm missing the `ban_members` permission!"
            elif '/channels/' in path and 'messages' in path:
                return "I'm missing the `send_messages` permission!"
            elif '/channels/' in path and 'delete' in path:
                return "I'm missing the `manage_messages` permission!"
            elif '/nicknames/' in path or '/nick/' in path:
                return "I'm missing the `manage_nicknames` permission!"
            elif '/kicks/' in path:
                return "I'm missing the `kick_members` permission!"
            elif '/webhooks/' in path:
                return "I'm missing the `manage_webhooks` permission!"
            elif '/emojis/' in path:
                return "I'm missing the `manage_expressions` permission!"
            elif '/pins/' in path:
                return "I'm missing the `manage_messages` permission!"
            elif '/reactions/' in path:
                return "I'm missing the `add_reactions` permission!"
            elif '/invites/' in path:
                return "I'm missing the `create_invite` permission!"
            elif '/threads/' in path:
                return "I'm missing the `manage_threads` permission!"
            
            missing_perms = []
            if hasattr(self, 'text') and 'Missing Permissions' in self.text:
                text_lower = self.text.lower()
                for perm in discord.Permissions.VALID_FLAGS:
                    if perm.lower() in text_lower:
                        missing_perms.append(f"`{perm.lower()}`")
            
            if missing_perms:
                return f"I'm missing the following permission(s): {', '.join(missing_perms)}!"
            
        return "I don't have permission to do that! Please check my role permissions."
    return original_str(self)

discord.errors.Forbidden.__str__ = custom_forbidden_str