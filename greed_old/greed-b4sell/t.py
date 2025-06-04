from pathlib import Path

emojis = [str(s) for s in Path("assets/").glob("*")]

emojis = {e.split("/")[-1].split(".")[0]: "" for e in emojis}
logger.info(emojis)
