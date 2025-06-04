from typing import List, Optional, cast

from aiohttp import ClientSession
from bs4 import BeautifulSoup, Tag
from discord.ext.commands import CommandError
from pydantic import BaseModel, Field
from typing_extensions import Self
from yarl import URL
