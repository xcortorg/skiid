from ..worker import offloaded


@offloaded
def remove_background(image: bytes):
    from rembg import remove

    return remove(image, force_return_bytes=True)
