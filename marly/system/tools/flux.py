from typing import Literal, TYPE_CHECKING
from system.tools.converters import PartialAttachment
from discord import File
from discord.ext.commands import Context, CommandError
from io import BytesIO
import asyncio
import tempfile
import os
from xxhash import xxh64_hexdigest


async def flux(
    ctx: Context,
    operation: Literal[
        # Original operations
        "caption",
        "speech-bubble",
        "flag2",
        "april-fools",
        "back-tattoo",
        "billboard-cityscape",
        "book",
        "circuitboard",
        "flag",
        "fortune-cookie",
        "heart-locket",
        "rubiks",
        "toaster",
        "valentine",
        # Additional operations
        "ah-shit",
        "bloom",
        "blur",
        "deepfry",
        "fisheye",
        "flip-flop",
        "frame-shift",
        "frames",
        "ghost",
        "gif",
        "globe",
        "grayscale",
        "info",
        "invert",
        "jpeg",
        "magik",
        "meme",
        "motivate",
        "neon",
        "overlay",
        "paint",
        "ping-pong",
        "pixelate",
        "posterize",
        "rainbow",
        "resize",
        "reverse",
        "rotate",
        "scramble",
        "set-loop",
        "speed",
        "spin",
        "spread",
        "swirl",
        "uncaption",
        "wormhole",
        "zoom",
        "zoom-blur",
    ],
    attachment: PartialAttachment,
    **payload,
) -> File:
    if not attachment or not attachment.buffer:
        raise CommandError("No valid attachment provided")

    flux_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "flux"
    )

    video_operations = {"april-fools", "ah-shit"}

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input")
        if attachment.format == "gif":
            input_path += ".gif"
        elif attachment.format == "image":
            input_path += ".png"

        buffer_data = attachment.buffer
        if buffer_data is None:
            raise CommandError("Attachment buffer is empty")

        if hasattr(buffer_data, "getvalue"):
            data_to_write = buffer_data.getvalue()
        else:
            data_to_write = buffer_data

        try:
            with open(input_path, "wb") as f:
                f.write(data_to_write)
        except Exception as e:
            raise CommandError(f"Failed to write input file: {e}")

        output_path = os.path.join(temp_dir, "output")
        if operation in video_operations:
            output_path += ".mp4"
        else:
            output_path += ".gif"

        cmd = ["flux", "-i", input_path]

        operation_mapping = {
            # Original operations
            "speech-bubble": "speech-bubble",
            "flag2": "flag2",
            "flag": "flag",
            "caption": "caption",
            "back-tattoo": "back-tattoo",
            "billboard-cityscape": "billboard-cityscape",
            "book": "book",
            "circuitboard": "circuitboard",
            "fortune-cookie": "fortune-cookie",
            "heart-locket": "heart-locket",
            "rubiks": "rubiks",
            "toaster": "toaster",
            "valentine": "valentine",
            "april-fools": "april-fools",
            # Additional operations
            "ah-shit": "ah-shit",
            "bloom": "bloom",
            "blur": "blur",
            "deepfry": "deepfry",
            "fisheye": "fisheye",
            "flip-flop": "flip-flop",
            "frame-shift": "frame-shift",
            "frames": "frames",
            "ghost": "ghost",
            "gif": "gif",
            "globe": "globe",
            "grayscale": "grayscale",
            "info": "info",
            "invert": "invert",
            "jpeg": "jpeg",
            "magik": "magik",
            "meme": "meme",
            "motivate": "motivate",
            "neon": "neon",
            "overlay": "overlay",
            "paint": "paint",
            "ping-pong": "ping-pong",
            "pixelate": "pixelate",
            "posterize": "posterize",
            "rainbow": "rainbow",
            "resize": "resize",
            "reverse": "reverse",
            "rotate": "rotate",
            "scramble": "scramble",
            "set-loop": "set-loop",
            "speed": "speed",
            "spin": "spin",
            "spread": "spread",
            "swirl": "swirl",
            "uncaption": "uncaption",
            "wormhole": "wormhole",
            "zoom": "zoom",
            "zoom-blur": "zoom-blur",
        }

        operation_str = operation_mapping.get(operation)
        if operation_str is None:
            raise CommandError(f"Unknown operation: {operation}")

        # Handle operations with parameters
        if operation == "caption" and "text" in payload:
            operation_str = f"caption[text={payload['text']}]"
        elif operation in ["flag", "flag2"] and "flag" in payload:
            operation_str = f"{operation}[flag={payload['flag']}]"
        elif operation == "ghost" and "depth" in payload:
            operation_str = f"ghost[depth={payload['depth']}]"
        elif operation == "blur" and "radius" in payload:
            operation_str = f"blur[radius={payload['radius']}]"
        elif operation == "rotate" and "angle" in payload:
            operation_str = f"rotate[angle={payload['angle']}]"
        elif operation == "speed" and "factor" in payload:
            operation_str = f"speed[factor={payload['factor']}]"
        elif operation == "resize" and all(k in payload for k in ["width", "height"]):
            operation_str = (
                f"resize[width={payload['width']},height={payload['height']}]"
            )
        elif operation == "heart-locket" and "text" in payload:
            operation_str = f"heart-locket[text={payload['text']}]"

        cmd.extend(["-o", operation_str, output_path])

        try:
            # Create and run the subprocess asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=flux_dir,
            )

            # Wait for the process to complete and get output
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise CommandError(f"Flux processing failed: {stderr.decode()}")

        except Exception as e:
            raise CommandError(f"Flux processing failed: {str(e)}")

        # Check output file exists
        if not os.path.exists(output_path):
            raise CommandError("Flux failed to generate output file")

        # Read output file
        try:
            with open(output_path, "rb") as f:
                buffer = BytesIO(f.read())
        except Exception as e:
            raise CommandError(f"Failed to read output file: {e}")

        # Generate filename
        try:
            name = xxh64_hexdigest(buffer.getvalue())
            extension = "mp4" if operation in video_operations else "gif"

            return File(buffer, filename=f"{operation.upper()}{name}FLUX.{extension}")
        except Exception as e:
            raise CommandError(f"Failed to create output file: {e}")
