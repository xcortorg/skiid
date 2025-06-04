from lib.worker import offloaded


@offloaded
def make_mp3(data: bytes):
    from moviepy.editor import VideoFileClip
    import tempfile

    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as output:
            temp_file.write(data)
            temp_file.flush()
            video_clip = VideoFileClip(tempfile.name)
            video_clip.audio.write_audiofile(output.name)
            video_clip.close()
            with open(output.name, "rb") as file:
                _ = file.read()
    return _


@offloaded
def song_recognize(filename: str, data: bytes):
    import tempfile
    import subprocess
    import json

    suffix = f".{filename.split('.', 1)[-1]}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as temp_file:
        temp_file.write(data)
        temp_file.flush()
        proc = subprocess.run(
            ["songrec", "audio-file-to-recognized-song", f'"{temp_file.name}'],
            capture_output=True,
        )
        _ = proc.stdout.decode()
    try:
        return json.loads(_)
    except json.JSONDecodeError:
        return False
