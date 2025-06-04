import asyncio
import aiohttp
import discord
from discord.ext import commands
import json
import os
from pathlib import Path
import tempfile
import shutil
from loguru import logger
import time
from os.path import splitext
from PIL import Image
from .download import async_dl

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


def setup(bot):
    # This module isn't actually a cog
    return


# A helper module for images.


def get_ext(url):
    """Return the filename extension from url, or ''."""
    parsed = urlparse(url)
    root, ext = splitext(parsed.path)
    return ext[1:]  # or ext if you want the leading '.'


def canDisplay(firstTime, threshold):
    # Check if enough time has passed since the last picture to display another
    currentTime = int(time.time())
    if currentTime > (int(firstTime) + int(threshold)):
        return True
    else:
        return False


async def download(url, ext: str = "jpg", sizeLimit: int = 8000000, ua: str = "Rival"):
    """Download the passed URL and return the file path."""
    url = str(url).strip("<>")
    # Set up a temp directory
    try:
        Path("/var/tmp").mkdir(parents=True, exist_ok=True)
    except:
        logger.info("Failed /var/tmp Creation")
    try:
        Path("//tmp").mkdir(parents=True, exist_ok=True)
    except:
        logger.info("Failed /tmp Creation")
    dirpath = tempfile.mkdtemp()
    tempFileName = url.rsplit("/", 1)[-1]
    # Strip question mark
    tempFileName = tempFileName.split("?")[0]
    imagePath = dirpath + "/" + tempFileName
    rImage = None

    try:
        rImage, ext = await async_dl(url, headers={"user-agent": ua})
        # logger.info("Got {} bytes".format(len(rImage)))
    except Exception as e:
        logger.info(f"Failed to download the image with error : {str(e)}")
    if not rImage:
        logger.info("'{}'\n - Returned no data.".format(url))
        remove(dirpath)
        return None

    with open(imagePath, "wb") as f:
        f.write(rImage)

    # Check if the file exists
    if not os.path.exists(imagePath):
        # logger.info("'{}'\n - Doesn't exist.".format(imagePath))
        remove(dirpath)
        logger.info("os not exists")
        return None

    # try:
    #     # Try to get the extension
    #     img = Image.open(imagePath)
    #     ext = img.format
    #     img.close()
    # except Exception as e:
    #     # Not something we understand - error out
    #     # logger.info("'{}'\n - Couldn't get extension.".format(imagePath))
    #     try:
    #         Path("/tmp").mkdir(parents=True, exist_ok=True)
    #     except:
    #         pass
    #     try:
    #         Path("/var/tmp").mkdir(parents=True, exist_ok=True)
    #     except:
    #         pass
    #     logger.info(f"Except Exception | {e}")
    #     return None

    if ext and not imagePath.lower().endswith("." + ext.lower()):
        os.rename(imagePath, "{}.{}".format(imagePath, ext))
        return "{}.{}".format(imagePath, ext)
    else:
        return imagePath


# async def upload(ctx, file_path, title = None):
# 	return await Message.Embed(title=title, file=file_path, color=ctx.author)


def addExt(path):
    img = Image.open(path)
    os.rename(path, "{}.{}".format(path, img.format))
    path = "{}.{}".format(path, img.format)
    return path


def remove(path):
    """Removed the passed file's containing directory."""
    if not path == None and os.path.exists(path):
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)
