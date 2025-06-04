from os import environ

from dotenv import load_dotenv
from system.myth import Myth

load_dotenv()
Myth(token=environ["TOKEN"])
