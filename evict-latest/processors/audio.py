# processors/audio.py
from logging import getLogger

log = getLogger("evict/processors")

def process_track_data(track_data: dict) -> dict:
    """
    Process track metadata in a separate process.
    """
    processed = {
        'title': track_data['title'],
        'length': track_data['length'],
        'uri': track_data['uri'],
        'author': track_data['author']
    }

    return processed

def process_playlist_data(playlist_data: list) -> list:
    """
    Process playlist tracks in a separate process.
    """
    processed_tracks = []
    for track in playlist_data:
        processed_tracks.append({
            'title': track['title'],
            'length': track['length'],
            'uri': track['uri'],
            'author': track['author']
        })
    
    return processed_tracks