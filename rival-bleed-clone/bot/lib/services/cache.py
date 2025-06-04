from cashews import cache
from ..worker import offloaded

cache.setup("mem://")

@offloaded
def remove_youtube_files():
    import subprocess
    for ext in ["mkv", "webm", "mp4"]:
        subprocess.run(f"rm -rf *.{ext}", shell=True, check=True)
        subprocess.run(f"rm -rf *.{ext}.part", shell=True, check=True)
    return True