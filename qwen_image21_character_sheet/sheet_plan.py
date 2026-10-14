"""Whole-sheet pixel geometry, independent from per-output reference plans."""
import hashlib
import json
import math

from .common.state import StateValidationError, decode_json
from .multi_reference_compiler import MULTI_VIEW_IDS, parse_multi_state
from .multi_guide_geometry import panel_bounds
from .output_plan import compile_output_plan

MAX_SHEET_PIXELS = 16_777_216


def plan_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()


def validate_sheet_plan(plan, *, max_resolution=16384):
    if type(plan) is not dict or set(plan) != {'schema_version', 'canvas', 'views', 'plan_hash'}:
        raise StateValidationError('Invalid sheet plan fields.', 'invalid_sheet_plan')
    payload = {key: value for key, value in plan.items() if key != 'plan_hash'}
    if type(plan['schema_version']) is not int or plan['schema_version'] != 1 or plan['plan_hash'] != plan_hash(payload):
        raise StateValidationError('Sheet plan version or hash mismatch.', 'invalid_sheet_plan')
    canvas = plan['canvas']
    if type(canvas) is not list or len(canvas) != 2 or any(type(n) is not int or n < 32 or n > max_resolution or n % 32 for n in canvas):
        raise StateValidationError('Sheet canvas needs supported width and height, in steps of 32.', 'invalid_sheet_canvas')
    width, height = canvas
    if width * height > MAX_SHEET_PIXELS:
        raise StateValidationError('Sheet canvas exceeds 16,777,216 pixels.', 'sheet_pixel_limit')
    views = plan['views']
    if type(views) is not list or not 1 <= len(views) <= len(MULTI_VIEW_IDS):
        raise StateValidationError('Sheet plan needs selected views.', 'invalid_sheet_plan')
    seen = set()
    rectangles = []
    for view in views:
        if type(view) is not dict or set(view) != {'view_id', 'bounds'} or type(view['view_id']) is not str or view['view_id'] not in MULTI_VIEW_IDS or view['view_id'] in seen:
            raise StateValidationError('Unknown or duplicate sheet view.', 'invalid_sheet_view')
        seen.add(view['view_id'])
        box = view['bounds']
        if type(box) is not list or len(box) != 4 or any(type(n) is not int for n in box):
            raise StateValidationError('Sheet bounds need integer endpoints.', 'invalid_sheet_bounds')
        left, top, right, bottom = box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise StateValidationError('Sheet bounds are empty or outside the canvas.', 'invalid_sheet_bounds')
        if any(left < r and right > l and top < b and bottom > t for l, t, r, b in rectangles):
            raise StateValidationError('Sheet panels overlap.', 'invalid_sheet_bounds')
        rectangles.append(box)
    return plan


def make_sheet_plan(state_json, *, sheet_size_mode='auto', sheet_width=1536, sheet_height=864, max_resolution=16384):
    state = parse_multi_state(state_json, max_resolution=max_resolution)
    if sheet_size_mode not in ('auto', 'manual'):
        raise StateValidationError('Sheet canvas mode must be auto or manual.', 'invalid_sheet_canvas')
    state['size'] = {**state['size'], 'mode': sheet_size_mode, 'manual_width': sheet_width, 'manual_height': sheet_height}
    layout = compile_output_plan(json.dumps(state), max_resolution=max_resolution, batch_out=False)['items'][0]['layout']
    payload = {'schema_version': 1, 'canvas': list(layout['canvas']),
               'views': [{'view_id': panel['id'], 'bounds': list(panel_bounds(layout, panel))} for panel in layout['panels']]}
    return validate_sheet_plan({**payload, 'plan_hash': plan_hash(payload)}, max_resolution=max_resolution)


def serialize_sheet_plan(plan):
    return json.dumps(plan, ensure_ascii=False, separators=(',', ':'))


def parse_sheet_plan(raw, *, max_resolution=16384):
    return validate_sheet_plan(decode_json(raw), max_resolution=max_resolution)


def contain_bounds(bounds, width, height):
    left, top, right, bottom = bounds
    scale = min((right - left) / width, (bottom - top) / height)
    target_width = min(right - left, max(1, math.floor(width * scale + 0.5)))
    target_height = min(bottom - top, max(1, math.floor(height * scale + 0.5)))
    x = left + (right - left - target_width) // 2
    y = top + (bottom - top - target_height) // 2
    return [x, y, x + target_width, y + target_height]
