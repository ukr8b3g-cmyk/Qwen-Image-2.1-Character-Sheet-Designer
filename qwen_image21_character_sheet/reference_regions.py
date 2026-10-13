"""Optional normalized image crops selected from the output's view IDs."""
import math

from .common.state import StateValidationError, decode_json
from .multi_reference_compiler import MULTI_VIEW_IDS
from .reference_plan import EXTRA_INPUTS

REGION_SOURCES = ('character_image', *EXTRA_INPUTS)


def parse_reference_regions(raw):
    regions = decode_json(raw)
    if type(regions) is not dict or regions.keys() - set(REGION_SOURCES):
        raise StateValidationError('Reference regions must name character_image or reference_image_1/2/3.', 'invalid_reference_regions')
    for source, views in regions.items():
        if type(views) is not dict or views.keys() - {'*', *MULTI_VIEW_IDS}:
            raise StateValidationError('Reference regions must use view IDs or *.', 'invalid_reference_regions')
        for rect in views.values():
            if (type(rect) is not list or len(rect) != 4
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in rect)
                    or rect[2] <= 0 or rect[3] <= 0):
                raise StateValidationError('A reference region is [left, top, width, height] with positive size.', 'invalid_reference_regions')
    return regions


def crop_reference(image, source, view_ids, regions):
    rules = regions.get(source, {})
    rects = [rules.get(view, rules.get('*')) for view in view_ids]
    if not rects or any(rect is None for rect in rects):
        return image
    height, width = image.shape[1:3]
    left = math.floor(math.nextafter(max(0, min(1, min(r[0] for r in rects))) * width, math.inf))
    top = math.floor(math.nextafter(max(0, min(1, min(r[1] for r in rects))) * height, math.inf))
    right = math.ceil(math.nextafter(max(0, min(1, max(r[0] + r[2] for r in rects))) * width, -math.inf))
    bottom = math.ceil(math.nextafter(max(0, min(1, max(r[1] + r[3] for r in rects))) * height, -math.inf))
    if right <= left or bottom <= top:
        raise StateValidationError('Reference region contains no pixels: ' + source, 'empty_reference_region')
    if (left, top, right, bottom) == (0, 0, width, height):
        return image
    return image[:, top:bottom, left:right, :].clone()
