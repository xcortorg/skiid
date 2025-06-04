import discord
import aiohttp
import json
import config

from datetime import datetime
from typing import Optional
from discord import Member, TextChannel, Embed
from discord.ext.commands import group, has_permissions

from tools import CompositeMetaClass, MixinMeta
from core.client.context import Context

class Lovense(MixinMeta, metaclass=CompositeMetaClass):
    """
    Lovense device integration and control.
    """
    def __init__(self, bot):
        self.bot = bot

    def _generate_user_token(self, guild_id: int, user_id: int) -> str:
        """Generate a unique token for user connection"""
        import secrets
        import base64
        
        unique = secrets.token_hex(16)
        data = f"{guild_id}-{user_id}-{unique}"
        return base64.urlsafe_b64encode(data.encode()).decode()

    async def _is_enabled(self, guild_id: int) -> bool:
        """Check if Lovense integration is enabled for the guild"""
        return await self.bot.db.fetchval(
            """
            SELECT is_enabled 
            FROM lovense_config 
            WHERE guild_id = $1
            """,
            guild_id
        ) or False

    @group(name="lovense", aliases=["lv"], invoke_without_command=True)
    async def lovense(self, ctx: Context, member: Optional[Member] = None):
        """
        View Lovense device status for yourself or another member.
        """
        target = member or ctx.author

        data = await self.bot.db.fetchrow(
            """
            SELECT device_id, device_type, last_active
            FROM lovense_devices 
            WHERE guild_id = $1 AND user_id = $2
            """,
            ctx.guild.id, target.id
        )

        if not data:
            return await ctx.warn(f"No Lovense device linked to {target.mention}")

        embed = Embed(
            title=f"Lovense Status for {target.name}",
            color=ctx.color,
            timestamp=datetime.now()
        )
        embed.add_field(name="Device Type", value=data['device_type'])
        embed.add_field(name="Last Active", value=f"<t:{int(data['last_active'].timestamp())}:R>")
        
        return await ctx.send(embed=embed)

    @lovense.command(name="enable")
    @has_permissions(administrator=True)
    async def lovense_enable(self, ctx: Context):
        """Enable Lovense integration for the server."""
        await self.bot.db.execute(
            """
            INSERT INTO lovense_config (guild_id, is_enabled)
            VALUES ($1, true)
            ON CONFLICT (guild_id)
            DO UPDATE SET is_enabled = true
            """,
            ctx.guild.id
        )
        return await ctx.approve("Lovense integration has been enabled")

    @lovense.command(name="disable")
    @has_permissions(administrator=True)
    async def lovense_disable(self, ctx: Context):
        """Disable Lovense integration for the server."""
        await self.bot.db.execute(
            """
            INSERT INTO lovense_config (guild_id, is_enabled)
            VALUES ($1, false)
            ON CONFLICT (guild_id)
            DO UPDATE SET is_enabled = false
            """,
            ctx.guild.id
        )
        return await ctx.approve("Lovense integration has been disabled")

    @lovense.command(name="link")
    async def lovense_link(self, ctx: Context, device_id: str):
        """Link your Lovense device"""
        if not await self._is_enabled(ctx.guild.id):
            return await ctx.warn("Lovense integration is not enabled on this server")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.lovense-api.com/api/lan/v2/getToys",
                headers={"Content-Type": "application/json"},
                json={
                    "token": config.AUTHORIZATION.LOVENSE,
                    "uid": str(ctx.author.id),
                    "apiVer": 1
                }
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to validate device")
                
                data = await resp.json()
                if data.get("code") != 200:
                    return await ctx.warn(f"Error: {data.get('message', 'Unknown error')}")
                
                toys = data.get("data", {}).get("toys", [])
                if not toys:
                    return await ctx.warn("No devices found. Make sure your device is connected to Lovense Connect app")
                
                device = next((toy for toy in toys if toy.get("id") == device_id), None)
                if not device:
                    return await ctx.warn(
                        "Invalid device ID. Your available devices:\n" +
                        "\n".join([f"`{t['id']}` - {t.get('name', 'Unknown')}" for t in toys])
                    )

        await self.bot.db.execute(
            """
            INSERT INTO lovense_devices 
            (guild_id, user_id, device_id, device_type, last_active)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id, user_id) 
            DO UPDATE SET 
                device_id = $3,
                device_type = $4,
                last_active = CURRENT_TIMESTAMP
            """,
            ctx.guild.id, 
            ctx.author.id, 
            device_id,
            device.get("name", "Unknown")
        )

        return await ctx.approve(f"Successfully linked your {device.get('name', 'device')}")

    @lovense.command(name="unlink")
    async def lovense_unlink(self, ctx: Context):
        """Unlink your Lovense device"""
        result = await self.bot.db.execute(
            """
            DELETE FROM lovense_devices
            WHERE guild_id = $1 AND user_id = $2
            """,
            ctx.guild.id, ctx.author.id
        )

        if result == "DELETE 0":
            return await ctx.warn("You don't have any linked devices")

        return await ctx.approve("Unlinked your Lovense device")

    @lovense.command(name="logs")
    @has_permissions(administrator=True)
    async def lovense_logs(self, ctx: Context, channel: TextChannel):
        """Set the channel for Lovense activity logs."""
        await self.bot.db.execute(
            """
            INSERT INTO lovense_config (guild_id, log_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET log_channel_id = $2
            """,
            ctx.guild.id, channel.id
        )
        return await ctx.approve(f"Lovense logs will be sent to {channel.mention}")

    @lovense.command(name="settings")
    async def lovense_settings(self, ctx: Context):
        """View Lovense integration settings"""
        settings = await self.bot.db.fetchrow(
            """
            SELECT is_enabled
            FROM lovense_config
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        if not settings:
            return await ctx.warn("No Lovense settings configured")

        embed = Embed(
            title=f"{config.EMOJIS.LOVENSE.LOVENSE} Lovense Settings",
            color=ctx.color,
            timestamp=datetime.now()
        )

        status = "✅ Enabled" if settings['is_enabled'] else "❌ Disabled"
        embed.add_field(name="Status", value=status, inline=True)

        devices = await self.bot.db.fetch(
            """
            SELECT user_id, device_type, last_active
            FROM lovense_devices
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        if devices:
            device_text = []
            for device in devices:
                member = ctx.guild.get_member(device['user_id'])
                if member:
                    device_text.append(f"{member.mention}: {device['device_type']}")
            
            if device_text:
                embed.add_field(
                    name="Linked Devices",
                    value="\n".join(device_text),
                    inline=False
                )

        embed.set_footer(text=f"Use {ctx.prefix}lovense help for detailed commands • Server ID: {ctx.guild.id}")
        
        return await ctx.send(embed=embed)

    @lovense.command(name="connect")
    async def lovense_connect(self, ctx: Context):
        """Connect your Lovense device via QR code."""
        if not await self._is_enabled(ctx.guild.id):
            return await ctx.warn("Lovense integration is not enabled on this server")

        existing = await self.bot.db.fetchrow(
            """
            SELECT device_id 
            FROM lovense_devices 
            WHERE guild_id = $1 AND user_id = $2
            """,
            ctx.guild.id, ctx.author.id
        )
        
        if existing:
            return await ctx.warn("You already have a device connected! Use `lovense disconnect` first.")

        loading_embed = Embed(
            title=f"{config.EMOJIS.LOVENSE.LOVENSE} Lovense Connection",
            description="Generating QR code...",
            color=ctx.color
        )
        loading_msg = await ctx.send(embed=loading_embed)

        try:
            user_token = self._generate_user_token(ctx.guild.id, ctx.author.id)
            
            await self.bot.db.execute(
                """
                INSERT INTO lovense_connections (token, guild_id, user_id, created_at)
                VALUES ($1, $2, $3, NOW())
                """,
                user_token, ctx.guild.id, ctx.author.id
            )

            from PIL import Image
            import zxing
            import qrcode
            from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
            from qrcode.image.styledpil import StyledPilImage
            from io import BytesIO
            import aiohttp
            import tempfile
            import os

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.lovense-api.com/api/lan/getQrCode",
                    headers={
                        "Content-Type": "application/json"
                    },
                    json={
                        "token": f"{config.AUTHORIZATION.LOVENSE}",
                        "uid": str(ctx.author.id),
                        "uname": str(ctx.author),
                        "utoken": user_token,
                        "v": "1"
                    }
                ) as resp:
                    if resp.status != 200:
                        return await ctx.warn("Failed to generate QR code")
                    
                    data = await resp.json()
                    qr_image_url = data.get("message")

                    if not qr_image_url:
                        return await ctx.warn("Failed to get QR code")

                    async with session.get(qr_image_url) as img_resp:
                        if img_resp.status != 200:
                            return await ctx.warn("Failed to download QR code")
                        
                        img_data = await img_resp.read()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(img_data)
                tmp_path = tmp_file.name

            try:
                reader = zxing.BarCodeReader()
                decoded = reader.decode(tmp_path)
                
                if not decoded:
                    return await ctx.warn("Failed to decode QR code")

                qr_data = decoded.raw
                json.loads(qr_data)

                async with aiohttp.ClientSession() as session:
                    async with session.get("https://r2.evict.bot/evict-new.png") as resp:
                        if resp.status == 200:
                            logo_data = await resp.read()
                            logo = Image.open(BytesIO(logo_data))
                            basewidth = 100
                            wpercent = (basewidth/float(logo.size[0]))
                            hsize = int((float(logo.size[1])*float(wpercent)))
                            logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)

                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=10,
                    border=2
                )
                qr.add_data(qr_data)
                qr.make(fit=True)

                img = qr.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=RoundedModuleDrawer(),
                    color_mask=qrcode.image.styles.colormasks.RadialGradiantColorMask(
                        back_color=(255, 255, 255),
                        center_color=(108, 117, 125),
                        edge_color=(52, 58, 64)
                    ),
                    embeded_image=logo
                )

                buffer = BytesIO()
                img.save(buffer, 'PNG')
                buffer.seek(0)

                file = discord.File(buffer, filename="evict-lovense-qr.png")

                embed = Embed(
                    title="Connect Your Lovense Device",
                    description=(
                        "1. Open Lovense Remote app\n"
                        "2. Go to Settings → Game Center\n"
                        "3. Scan this QR code\n"
                        "4. Authorize the connection\n\n"
                        "This QR code will expire in 10 minutes."
                    ),
                    color=ctx.color
                )
                embed.set_image(url="attachment://qr.png")

                try:
                    await ctx.author.send(file=file, embed=embed)
                    success_embed = Embed(
                        title=f"{config.EMOJIS.LOVENSE.LOVENSE} Lovense Connection",
                        description="✅ QR code has been sent to your DMs!",
                        color=ctx.color
                    )
                    await loading_msg.edit(embed=success_embed)
                except discord.Forbidden:
                    error_embed = Embed(
                        title="Lovense Connection",
                        description="❌ I couldn't DM you! Please enable DMs from server members.",
                        color=discord.Color.red()
                    )
                    await loading_msg.edit(embed=error_embed)

            finally:
                os.unlink(tmp_path)

        except Exception as e:
            error_embed = Embed(
                title="Lovense Connection",
                description="❌ An error occurred while generating the QR code.",
                color=discord.Color.red()
            )
            await loading_msg.edit(embed=error_embed)
            raise e  

    async def _get_device(self, guild_id: int, user_id: int):
        """Get user's device info if they own one"""
        return await self.bot.db.fetchrow(
            """
            SELECT device_id, device_type, access_token
            FROM lovense_devices
            WHERE guild_id = $1 AND user_id = $2
            """,
            guild_id, user_id
        )

    @lovense.group(name="toy", invoke_without_command=True)
    async def lovense_toy(self, ctx: Context):
        """Control your Lovense toy"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @lovense_toy.command(name="vibrate")
    async def toy_vibrate(self, ctx: Context, strength: int, time: int = 0, device_id: str = None):
        """
        Vibrate a toy
        Strength: 0-20
        Time: Seconds (0 for indefinite)
        Device ID: Optional specific device
        """
        owned = await self._get_devices(ctx.guild.id, ctx.author.id)
        shared = await self._get_shared_devices(ctx.guild.id, ctx.author.id)
        all_devices = owned + shared

        if not all_devices:
            return await ctx.warn("You don't have access to any Lovense devices!")

        device, error = await self._select_device(ctx, all_devices, device_id)
        if error:
            return await ctx.warn(error)

        if not 0 <= strength <= 20:
            return await ctx.warn("Vibrate strength must be between 0 and 20")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.lovense-api.com/api/lan/v2/command",
                headers={"Content-Type": "application/json"},
                json={
                    "token": config.AUTHORIZATION.LOVENSE,
                    "uid": str(ctx.author.id),
                    "command": "Function",
                    "action": f"Vibrate:{strength}",
                    "timeSec": time,
                    "toy": device['device_id'],
                    "apiVer": 1
                }
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to control device")
                
                data = await resp.json()
                if data.get("code") != 200:
                    return await ctx.warn(f"Error: {data.get('message', 'Unknown error')}")

        await ctx.approve(
            f"Vibrating {device['device_type']} at {strength}% strength" + 
            (f" for {time}s" if time > 0 else "")
        )

    @lovense_toy.command(name="pump")
    async def toy_pump(self, ctx: Context, strength: int, time: int = 0, device_id: str = None):
        """
        Pump action for compatible toys
        Strength: 0-3
        Time: Seconds (0 for indefinite)
        Device ID: Optional specific device
        """
        owned = await self._get_devices(ctx.guild.id, ctx.author.id)
        shared = await self._get_shared_devices(ctx.guild.id, ctx.author.id)
        all_devices = owned + shared

        if not all_devices:
            return await ctx.warn("You don't have access to any Lovense devices!")

        device, error = await self._select_device(ctx, all_devices, device_id)
        if error:
            return await ctx.warn(error)

        if not 0 <= strength <= 3:
            return await ctx.warn("Pump strength must be between 0 and 3")
        
        if time < 0:
            return await ctx.warn("Time cannot be negative")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.lovense-api.com/api/lan/v2/command",
                headers={"Content-Type": "application/json"},
                json={
                    "token": config.AUTHORIZATION.LOVENSE,
                    "uid": str(ctx.author.id),
                    "command": "Function",
                    "action": f"Pump:{strength}",
                    "timeSec": time,
                    "toy": device['device_id'],
                    "apiVer": 1
                }
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to control device")
                
                data = await resp.json()
                if data.get("code") != 200:
                    return await ctx.warn(f"Error: {data.get('message', 'Unknown error')}")

        await ctx.approve(
            f"Pumping at {strength}/3 strength" + 
            (f" for {time}s" if time > 0 else "")
        )

    @lovense_toy.command(name="finger")
    async def toy_finger(self, ctx: Context, strength: int, time: int = 0, loop_run: int = 0, loop_pause: int = 0, device_id: str = None):
        """
        Fingering action for compatible toys
        Strength: 0-20
        Time: Seconds (0 for indefinite)
        Loop Run: Seconds to run in loop
        Loop Pause: Seconds to pause between loops
        Device ID: Optional specific device
        """
        owned = await self._get_devices(ctx.guild.id, ctx.author.id)
        shared = await self._get_shared_devices(ctx.guild.id, ctx.author.id)
        all_devices = owned + shared

        if not all_devices:
            return await ctx.warn("You don't have access to any Lovense devices!")

        device, error = await self._select_device(ctx, all_devices, device_id)
        if error:
            return await ctx.warn(error)

        if not 0 <= strength <= 20:
            return await ctx.warn("Fingering strength must be between 0 and 20")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.lovense-api.com/api/lan/v2/command",
                headers={"Content-Type": "application/json"},
                json={
                    "token": config.AUTHORIZATION.LOVENSE,
                    "uid": str(ctx.author.id),
                    "command": "Function",
                    "action": f"Fingering:{strength}",
                    "timeSec": time,
                    "loopRunningSec": loop_run if loop_run > 0 else None,
                    "loopPauseSec": loop_pause if loop_pause > 0 else None,
                    "toy": device['device_id'],
                    "apiVer": 1
                }
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to control device")
                
                data = await resp.json()
                if data.get("code") != 200:
                    return await ctx.warn(f"Error: {data.get('message', 'Unknown error')}")

        await ctx.approve(
            f"Fingering at {strength}/20 strength" + 
            (f" for {time}s" if time > 0 else "")
        )

    @lovense_toy.command(name="suction")
    async def toy_suction(self, ctx: Context, strength: int, time: int = 0, loop_run: int = 0, loop_pause: int = 0, device_id: str = None):
        """
        Suction action for compatible toys
        Strength: 0-20
        Time: Seconds (0 for indefinite)
        Loop Run: Seconds to run in loop
        Loop Pause: Seconds to pause between loops
        Device ID: Optional specific device
        """
        owned = await self._get_devices(ctx.guild.id, ctx.author.id)
        shared = await self._get_shared_devices(ctx.guild.id, ctx.author.id)
        all_devices = owned + shared

        if not all_devices:
            return await ctx.warn("You don't have access to any Lovense devices!")

        device, error = await self._select_device(ctx, all_devices, device_id)
        if error:
            return await ctx.warn(error)

        if not 0 <= strength <= 20:
            return await ctx.warn("Suction strength must be between 0 and 20")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.lovense-api.com/api/lan/v2/command",
                headers={"Content-Type": "application/json"},
                json={
                    "token": config.AUTHORIZATION.LOVENSE,
                    "uid": str(ctx.author.id),
                    "command": "Function",
                    "action": f"Suction:{strength}",
                    "timeSec": time,
                    "loopRunningSec": loop_run if loop_run > 0 else None,
                    "loopPauseSec": loop_pause if loop_pause > 0 else None,
                    "toy": device['device_id'],
                    "apiVer": 1
                }
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to control device")
                
                data = await resp.json()
                if data.get("code") != 200:
                    return await ctx.warn(f"Error: {data.get('message', 'Unknown error')}")

        await ctx.approve(
            f"Suctioning at {strength}/20 strength" + 
            (f" for {time}s" if time > 0 else "")
        )

    @lovense_toy.command(name="stop")
    async def toy_stop(self, ctx: Context, device_id: str = None):
        """Stop all toy actions"""
        owned = await self._get_devices(ctx.guild.id, ctx.author.id)
        shared = await self._get_shared_devices(ctx.guild.id, ctx.author.id)
        all_devices = owned + shared

        if not all_devices:
            return await ctx.warn("You don't have access to any Lovense devices!")

        if device_id:
            device = discord.utils.get(all_devices, device_id=device_id)
            if not device:
                return await ctx.warn("You don't have access to this device!")
            devices = [device]
        else:
            devices = all_devices

        for device in devices:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.lovense-api.com/api/lan/v2/command",
                    headers={"Content-Type": "application/json"},
                    json={
                        "token": config.AUTHORIZATION.LOVENSE,
                        "uid": str(ctx.author.id),
                        "command": "Function",
                        "action": "Stop",
                        "toy": device['device_id'],
                        "apiVer": 1
                    }
                ) as resp:
                    if resp.status != 200:
                        return await ctx.warn(f"Failed to stop {device['device_type']}")
                    
                    data = await resp.json()
                    if data.get("code") != 200:
                        return await ctx.warn(f"Error stopping {device['device_type']}: {data.get('message', 'Unknown error')}")

        await ctx.approve(
            "Stopped " + 
            (f"{device_id}" if device_id else "all toys")
        )

    async def _check_consent(self, user_id: int) -> bool:
        """Check if user has agreed to terms"""
        data = await self.bot.db.fetchrow(
            """
            SELECT agreed, locked
            FROM lovense_consent
            WHERE user_id = $1
            """,
            user_id
        )
        if not data:
            return False
        return data['agreed'] and not data['locked']

    @lovense_toy.command(name="share")
    async def toy_share(self, ctx: Context, target: discord.Member, device_id: str = None):
        """Share your toy control with another user"""
        devices = await self._get_devices(ctx.guild.id, ctx.author.id)
        if not devices:
            return await ctx.warn("You don't have any Lovense devices connected!")

        if not device_id and len(devices) > 1:
            options = [
                discord.SelectOption(
                    label=f"{d['device_type']} ({d['device_id']})",
                    value=d['device_id']
                ) for d in devices
            ]

            class DeviceSelect(discord.ui.Select):
                def __init__(self):
                    super().__init__(
                        placeholder="Choose a device to share",
                        options=options
                    )

                async def callback(self, interaction: discord.Interaction):
                    if interaction.user.id != ctx.author.id:
                        return await interaction.response.send_message(
                            "This selection is not for you",
                            ephemeral=True
                        )
                    self.view.device_id = self.values[0]
                    self.view.stop()

            class DeviceView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)
                    self.device_id = None
                    self.add_item(DeviceSelect())

            view = DeviceView()
            await ctx.send(f"{config.EMOJIS.LOVENSE.LOVENSE} Which device would you like to share?", view=view)
            await view.wait()

            if not view.device_id:
                return await ctx.warn("Selection timed out")
            
            device_id = view.device_id

        if not device_id:
            device_id = devices[0]['device_id']

        device = discord.utils.get(devices, device_id=device_id)
        if not device:
            return await ctx.warn("You don't own this device!")

        await self.bot.db.execute(
            """
            INSERT INTO lovense_shares (guild_id, owner_id, target_id, device_id)
            VALUES ($1, $2, $3, $4)
            """,
            ctx.guild.id, ctx.author.id, target.id, device_id
        )

    @lovense_toy.command(name="unshare")
    async def toy_unshare(self, ctx: Context, target: discord.Member, device_id: str = None):
        """Stop sharing your toy with someone"""
        if device_id:
            result = await self.bot.db.execute(
                """
                DELETE FROM lovense_shares
                WHERE guild_id = $1 AND owner_id = $2 AND target_id = $3 AND device_id = $4
                """,
                ctx.guild.id, ctx.author.id, target.id, device_id
            )
        else:
            result = await self.bot.db.execute(
                """
                DELETE FROM lovense_shares
                WHERE guild_id = $1 AND owner_id = $2 AND target_id = $3
                """,
                ctx.guild.id, ctx.author.id, target.id
            )

        if result == "DELETE 0":
            return await ctx.warn(f"No devices shared with {target.mention}")

        await ctx.approve(f"Stopped sharing with {target.mention}")

    @lovense_toy.command(name="list")
    async def toy_list(self, ctx: Context):
        """List your toys and toys shared with you"""
        owned_devices = await self._get_devices(ctx.guild.id, ctx.author.id)
        shared_devices = await self._get_shared_devices(ctx.guild.id, ctx.author.id)

        embed = Embed(
            title=f"{config.EMOJIS.LOVENSE.LOVENSE} Your Lovense Devices",
            color=ctx.color
        )

        if owned_devices:
            owned_text = []
            for device in owned_devices:
                status = "🟢" if (datetime.now() - device['last_active']).total_seconds() < 300 else "🔴"
                owned_text.append(
                    f"{status} `{device['device_id']}` - {device['device_type']}\n"
                    f"Last active: <t:{int(device['last_active'].timestamp())}:R>"
                )
            embed.add_field(
                name="Your Devices",
                value="\n\n".join(owned_text) if owned_text else "No devices",
                inline=False
            )

        if shared_devices:
            shared_text = []
            for device in shared_devices:
                owner = ctx.guild.get_member(device['owner_id'])
                owner_name = owner.name if owner else "Unknown"
                status = "🟢" if (datetime.now() - device['last_active']).total_seconds() < 300 else "🔴"
                shared_text.append(
                    f"{status} `{device['device_id']}` - {device['device_type']}\n"
                    f"Owner: {owner_name}\n"
                    f"Last active: <t:{int(device['last_active'].timestamp())}:R>"
                )
            embed.add_field(
                name="Shared With You",
                value="\n\n".join(shared_text) if shared_text else "No shared devices",
                inline=False
            )

        if not owned_devices and not shared_devices:
            embed.description = "You don't have any devices connected or shared with you"

        await ctx.send(embed=embed)

    async def _get_devices(self, guild_id: int, user_id: int):
        """Get all user's devices"""
        return await self.bot.db.fetch(
            """
            SELECT device_id, device_type, last_active
            FROM lovense_devices 
            WHERE guild_id = $1 AND user_id = $2
            """,
            guild_id, user_id
        )

    async def _get_shared_devices(self, guild_id: int, user_id: int):
        """Get devices shared with user"""
        return await self.bot.db.fetch(
            """
            SELECT d.device_id, d.device_type, d.last_active, d.user_id as owner_id
            FROM lovense_devices d
            JOIN lovense_shares s ON d.device_id = s.device_id
            WHERE s.guild_id = $1 AND s.target_id = $2
            """,
            guild_id, user_id
        )  