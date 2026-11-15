"""Render the Designer's existing mannequin atlas using the shared geometry."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from .multi_guide_geometry import BODY_CROPS, MIRRORED_VIEWS, body_artwork_placements

ATLAS_PATH = Path(__file__).resolve().parents[1] / "web/assets/mannequin-atlas.png"
ATLAS_CROPS = {
    "face_front": (0, 75, 470, 560),
    "face_left": (1010, 35, 140, 205),
    "body_front": (495, 20, 350, 625),
    "body_left": (904, 20, 350, 625),
    "body_back": (55, 625, 350, 625),
    "hands": (415, 755, 445, 400),
    "feet": (860, 820, 380, 340),
}
EXTRA_VIEWS = {
    "face_right", "face_3q_left", "face_3q_right", "face_back",
    "clothing_front", "clothing_back",
}


def render_layout_image(layout: dict, *, multi_reference=True, clothing_mode='worn') -> Image.Image:
    width, height = layout["canvas"]
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    frame_width = max(1, (min(width, height) + 128) // 256)
    atlas = None
    soft_placement_mask = None
    body_artwork = body_artwork_placements(layout) if multi_reference else {}
    for panel in layout["panels"]:
        x, y, w, h = panel["rect"]
        left, top = round(x * width), round(y * height)
        right, bottom = round((x + w) * width), round((y + h) * height)
        view = panel["id"]
        if panel.get('blank') or (multi_reference and clothing_mode == 'garment' and view in ('clothing_front', 'clothing_back')):
            fill = panel.get('guide_fill')
            if fill:
                if soft_placement_mask is None:
                    # Fade to white before the bounds so no hard outline enters conditioning.
                    soft_placement_mask = Image.radial_gradient('L').point(lambda value: max(0, 255 - value * 3 // 2))
                mask = soft_placement_mask.resize((right - left, bottom - top), Image.Resampling.BILINEAR)
                canvas.paste(fill, (left, top, right, bottom), mask)
            else:
                draw.rectangle((left, top, right - 1, bottom - 1), outline="black", width=frame_width)
            continue
        if view in EXTRA_VIEWS:
            with Image.open(ATLAS_PATH.parent / "multi_reference" / f"{view}.png") as extra:
                artwork = extra.convert("RGBA")
        else:
            if atlas is None:
                with Image.open(ATLAS_PATH) as source:
                    atlas = source.convert("RGBA")
            if view in body_artwork:
                crop_x, crop_y, crop_w, crop_h = body_artwork[view].get('crop', BODY_CROPS.get(view, (0, 0, 1, 1)))
            else:
                crop_x, crop_y, crop_w, crop_h = ATLAS_CROPS[view]
            artwork = atlas.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
        if multi_reference and view in MIRRORED_VIEWS:
            artwork = ImageOps.mirror(artwork)
        if view in body_artwork:
            x, y, w, h = body_artwork[view]['rect']
            artwork = artwork.resize((w, h), Image.Resampling.LANCZOS)
            position = (x, y)
        else:
            artwork = ImageOps.contain(artwork, (max(1, right - left), max(1, bottom - top)), Image.Resampling.LANCZOS)
            position = (left + (right - left - artwork.width) // 2, top + (bottom - top - artwork.height) // 2)
        canvas.paste(artwork, position, artwork)
        draw.rectangle((left, top, right - 1, bottom - 1), outline="black", width=frame_width)
    return canvas
