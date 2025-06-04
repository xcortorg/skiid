from collections import defaultdict
from io import BytesIO
from itertools import chain
from random import randrange
from typing import Any, Union

import aiohttp
from PIL import Image
from PIL.Image import Image as IMG


class PatPatCreator:
    def __init__(self, image_url: str) -> None:
        self.image_url = image_url
        self.max_frames = 10
        self.resolution = (150, 150)
        self.frames: list[IMG] = []

    async def create_gif(self):
        img_bytes = await self.__get_image_bytes()

        base = Image.open(img_bytes).convert("RGBA").resize(self.resolution)

        for i in range(self.max_frames):
            squeeze = i if i < self.max_frames / 2 else self.max_frames - i
            width = 0.8 + squeeze * 0.02
            height = 0.8 - squeeze * 0.05
            offsetX = (1 - width) * 0.5 + 0.1
            offsetY = (1 - height) - 0.08

            canvas = Image.new("RGBA", size=self.resolution, color=(0, 0, 0, 0))
            canvas.paste(
                base.resize(
                    (
                        round(width * self.resolution[0]),
                        round(height * self.resolution[1]),
                    )
                ),
                (
                    round(offsetX * self.resolution[0]),
                    round(offsetY * self.resolution[1]),
                ),
            )

            # pat_hand = Image.open(f"subclasses/assets/pet{i}.gif").convert('RGBA').resize(self.resolution)
            pat_hand = (
                Image.open(f"tools/important/subclasses/assets/pet{i}.gif")
                .convert("RGBA")
                .resize(self.resolution)
            )

            canvas.paste(pat_hand, mask=pat_hand)
            self.frames.append(canvas)

        gif_image, save_kwargs = await self.__animate_gif(self.frames)

        buffer = BytesIO()
        gif_image.save(buffer, **save_kwargs)
        buffer.seek(0)

        return buffer

    async def __animate_gif(
        self, images: list[IMG], durations: Union[int, list[int]] = 20
    ) -> tuple[IMG, dict[str, Any]]:
        save_kwargs: dict[str, Any] = {}
        new_images: list[IMG] = []

        for frame in images:
            thumbnail = frame.copy()
            thumbnail_rgba = thumbnail.convert(mode="RGBA")
            thumbnail_rgba.thumbnail(size=frame.size, reducing_gap=3.0)
            converter = TransparentAnimatedGifConverter(img_rgba=thumbnail_rgba)
            thumbnail_p = converter.process()
            new_images.append(thumbnail_p)

        output_image = new_images[0]
        save_kwargs.update(
            format="GIF",
            save_all=True,
            optimize=False,
            append_images=new_images[1:],
            duration=durations,
            disposal=2,  # Other disposals don't work
            loop=0,
        )

        return output_image, save_kwargs

    async def __get_image_bytes(self):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url=self.image_url) as res:
                if res.status != 200:
                    raise FileNotFoundError(res.status, res.url)

                return BytesIO(await res.read())


class TransparentAnimatedGifConverter(object):
    _PALETTE_SLOTSET = set(range(256))

    def __init__(self, img_rgba: IMG, alpha_threshold: int = 0):
        self._img_rgba = img_rgba
        self._alpha_threshold = alpha_threshold

    def _process_pixels(self):
        self._transparent_pixels = set(
            idx
            for idx, alpha in enumerate(
                self._img_rgba.getchannel(channel="A").getdata()
            )
            if alpha <= self._alpha_threshold
        )

    def _set_parsed_palette(self):
        palette = self._img_p.getpalette()
        self._img_p_used_palette_idxs = set(
            idx
            for pal_idx, idx in enumerate(self._img_p_data)
            if pal_idx not in self._transparent_pixels
        )
        self._img_p_parsedpalette = dict(
            (idx, tuple(palette[idx * 3 : idx * 3 + 3]))
            for idx in self._img_p_used_palette_idxs
        )  # type: ignore

    def _get_similar_color_idx(self):
        old_color = self._img_p_parsedpalette[0]
        dict_distance = defaultdict(list)
        for idx in range(1, 256):
            color_item = self._img_p_parsedpalette[idx]
            if color_item == old_color:
                return idx
            distance = sum(
                (
                    abs(old_color[0] - color_item[0]),  # Red
                    abs(old_color[1] - color_item[1]),  # Green
                    abs(old_color[2] - color_item[2]),
                )
            )  # Blue
            dict_distance[distance].append(idx)
        return dict_distance[sorted(dict_distance)[0]][0]

    def _remap_palette_idx_zero(self):
        free_slots = self._PALETTE_SLOTSET - self._img_p_used_palette_idxs
        new_idx = free_slots.pop() if free_slots else self._get_similar_color_idx()
        self._img_p_used_palette_idxs.add(new_idx)
        self._palette_replaces["idx_from"].append(0)
        self._palette_replaces["idx_to"].append(new_idx)
        self._img_p_parsedpalette[new_idx] = self._img_p_parsedpalette[0]
        del self._img_p_parsedpalette[0]

    def _get_unused_color(self) -> tuple:
        used_colors = set(self._img_p_parsedpalette.values())
        while True:
            new_color = (randrange(256), randrange(256), randrange(256))
            if new_color not in used_colors:
                return new_color

    def _process_palette(self):
        self._set_parsed_palette()
        if 0 in self._img_p_used_palette_idxs:
            self._remap_palette_idx_zero()
        self._img_p_parsedpalette[0] = self._get_unused_color()

    def _adjust_pixels(self):
        if self._palette_replaces["idx_from"]:
            trans_table = bytearray.maketrans(
                bytes(self._palette_replaces["idx_from"]),
                bytes(self._palette_replaces["idx_to"]),
            )
            self._img_p_data = self._img_p_data.translate(trans_table)
        for idx_pixel in self._transparent_pixels:
            self._img_p_data[idx_pixel] = 0
        self._img_p.frombytes(data=bytes(self._img_p_data))

    def _adjust_palette(self):
        unused_color = self._get_unused_color()
        final_palette = chain.from_iterable(
            self._img_p_parsedpalette.get(x, unused_color) for x in range(256)
        )
        self._img_p.putpalette(data=final_palette)

    def process(self) -> IMG:
        self._img_p = self._img_rgba.convert(mode="P")
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._palette_replaces = dict(idx_from=list(), idx_to=list())
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info["transparency"] = 0
        self._img_p.info["background"] = 0
        return self._img_p
