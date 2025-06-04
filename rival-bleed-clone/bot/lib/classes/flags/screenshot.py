from discord.ext.commands import FlagConverter, flag
from typing import Optional, Literal

class ScreenshotFlags(FlagConverter, delimiter=" "):
	wait: Optional[int] = flag(default=None, description="An optional wait time in seconds.")
	wait_for: Optional[Literal["domcontentloaded", "networkidle", "load", "commit"]] = flag(
		name = "wait-until", 
		aliases = ["wu"],
		default="domcontentloaded", 
		description="Specify the wait condition. One of 'domcontentloaded', 'networkidle', 'load', or 'commit'."
	)
	full_page: bool = flag(
		name = "full-page",
		aliases = ["full", "fp"],
		default = False, 
		description = "screenshot the entire page in one image"
	)