from ..worker import offloaded

@offloaded
def _make_bar(percentage_1, color_1, percentage_2, color_2, bar_width: int = 10, height: int = 1, corner_radius: int = 0.2) -> bytes:
    """
    Generate a bar with two colors representing two different percentages,
    with a rounded left corner on the first segment and a rounded right corner
    on the second segment.

    :param percentage_1: The percentage for the first color (0-100)
    :param color_1: The color for the first segment
    :param percentage_2: The percentage for the second color (0-100)
    :param color_2: The color for the second segment
    :param bar_width: The width of the bar (default is 10 units)
    :param height: The height of the bar (default is 1 unit)
    :param corner_radius: The radius of the rounded corners (default is 0.2 units)
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch, Path
    from matplotlib.path import Path
    from PIL import Image
    import matplotlib
    from io import BytesIO
    matplotlib.use("agg")
    plt.switch_backend("agg")
    if not (0 <= percentage_1 <= 100 and 0 <= percentage_2 <= 100):
        raise ValueError("Percentages must be between 0 and 100.")

    if percentage_1 + percentage_2 > 100:
        raise ValueError("The sum of percentages cannot exceed 100.")

    fig, ax = plt.subplots(figsize=(10, 2))
    
    # Calculate the width of each segment
    width_1 = (percentage_1 / 100) * bar_width
    width_2 = (percentage_2 / 100) * bar_width

    # Define the rounded rectangle path for the first segment (left side rounded)
    if width_1 > 0:
        path_data = [
            (Path.MOVETO, [corner_radius, 0]),
            (Path.LINETO, [width_1, 0]),
            (Path.LINETO, [width_1, height]),
            (Path.LINETO, [corner_radius, height]),
            (Path.CURVE3, [0, height]),
            (Path.CURVE3, [0, height - corner_radius]),
            (Path.LINETO, [0, corner_radius]),
            (Path.CURVE3, [0, 0]),
            (Path.CURVE3, [corner_radius, 0])
        ]
        codes, verts = zip(*path_data)
        path = Path(verts, codes)
        patch = PathPatch(path, facecolor=color_1, edgecolor='none')
        ax.add_patch(patch)

    # Define the rounded rectangle path for the second segment (right side rounded)
    if width_2 > 0:
        path_data = [
            (Path.MOVETO, [width_1, 0]),
            (Path.LINETO, [width_1 + width_2 - corner_radius, 0]),
            (Path.CURVE3, [width_1 + width_2, 0]),
            (Path.CURVE3, [width_1 + width_2, corner_radius]),
            (Path.LINETO, [width_1 + width_2, height - corner_radius]),
            (Path.CURVE3, [width_1 + width_2, height]),
            (Path.CURVE3, [width_1 + width_2 - corner_radius, height]),
            (Path.LINETO, [width_1, height]),
            (Path.LINETO, [width_1, 0])
        ]
        codes, verts = zip(*path_data)
        path = Path(verts, codes)
        patch = PathPatch(path, facecolor=color_2, edgecolor='none')
        ax.add_patch(patch)

    # Set limits and remove axes
    ax.set_xlim(0, bar_width)
    ax.set_ylim(0, height)
    ax.axis('off')
    buffer = BytesIO()
    plt.savefig(buffer, transparent=True)
    buffer.seek(0)
    image = Image.open(buffer).convert("RGBA")

    # Get the bounding box of the non-transparent areas
    bbox = image.getbbox()
    output_path = BytesIO()

    if bbox:
        # Crop the image to the bounding box
        image_cropped = image.crop(bbox)
        image_cropped.save(output_path, format="png")
    return output_path.getvalue()