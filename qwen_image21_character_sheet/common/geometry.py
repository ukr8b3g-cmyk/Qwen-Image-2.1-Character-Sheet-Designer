"""Pure rational geometry, extracted from the byte-verified H3 compiler.

No model text, generation, network, filesystem or ComfyUI imports.
"""
from __future__ import annotations
from fractions import Fraction
from typing import Any
from .state import AUXILIARY_IDS, PORTRAIT_IDS, BODY_IDS, DEFAULT_MAX_RESOLUTION, _size_value

def _ceil_32(value: Fraction) -> int:
    return ((value.numerator + 32 * value.denominator - 1) // (32 * value.denominator)) * 32


def _round_coordinate(value: Fraction) -> float:
    # Integer arithmetic gives exact round-half-up, independent of decimal context.
    numerator = value.numerator * 1_000_000
    rounded = (2 * numerator + value.denominator) // (2 * value.denominator)
    return rounded / 1_000_000 if rounded else 0.0


def _ideal_layout(views: list[str], h: int) -> tuple[Fraction, Fraction, dict[str, tuple[Fraction, ...]], Fraction | None]:
    height = Fraction(h)
    margin, gap, body_width, aux_width = height / 14, height / 25, 2 * height / 5, height / 2
    auxiliaries = [view for view in AUXILIARY_IDS if view in views]
    portraits = [view for view in PORTRAIT_IDS if view in views]
    details = [view for view in ("hands", "feet") if view in views]
    bodies = [view for view in BODY_IDS if view in views]
    # Each portrait has its own column. Existing selections without face_left
    # retain the exact original geometry, including the six-view detail layout.
    aux_columns = len(portraits) or bool(details)
    columns = len(bodies) + aux_columns
    width = len(bodies) * body_width + aux_columns * aux_width + (columns - 1) * gap + 2 * margin
    canvas_height = height + 2 * margin
    rects: dict[str, tuple[Fraction, ...]] = {}
    x, y = margin, margin
    if auxiliaries:
        group_width = aux_columns * aux_width + (aux_columns - 1) * gap
        if portraits:
            portrait_height = 31 * height / 50 if details else height
            for index, view in enumerate(portraits):
                rects[view] = (x + index * (aux_width + gap), y, aux_width, portrait_height)
            detail_y = y + portrait_height + gap
            detail_height = height - portrait_height - gap
            detail_width = (group_width - gap) / 2 if len(details) == 2 else group_width
            for index, view in enumerate(details):
                rects[view] = (x + index * (detail_width + gap), detail_y, detail_width, detail_height)
        elif len(auxiliaries) == 2:  # hands + feet, without portrait
            detail_height = (height - gap) / 2
            for index, view in enumerate(auxiliaries):
                rects[view] = (x, y + index * (detail_height + gap), aux_width, detail_height)
        else:
            rects[auxiliaries[0]] = (x, y, aux_width, height)
        x += group_width + gap
    for view in bodies:
        rects[view] = (x, y, body_width, height)
        x += body_width + gap
    return width, canvas_height, rects, margin + height if bodies else None


def compute_geometry(state: dict[str, Any], *, max_resolution: int = DEFAULT_MAX_RESOLUTION) -> dict[str, Any]:
    """Lay out a validated state; inputs must come from parse_state."""
    size = state["size"]
    ideal_width, ideal_height, raw_rects, feet_y = _ideal_layout(state["views"], size["body_height"])
    if size["mode"] == "auto":
        width, height = _ceil_32(ideal_width), _ceil_32(ideal_height)
        scale = Fraction(1)
    else:
        width, height = size["manual_width"], size["manual_height"]
        scale = min(Fraction(width) / ideal_width, Fraction(height) / ideal_height)
    for axis, value in (("output width", width), ("output height", height)):
        _size_value(value, axis, max_resolution)
    offset_x, offset_y = (width - ideal_width * scale) / 2, (height - ideal_height * scale) / 2
    panels = []
    for view in state["views"]:
        left, top, panel_width, panel_height = raw_rects[view]
        rect = [
            _round_coordinate((left * scale + offset_x) / width),
            _round_coordinate((top * scale + offset_y) / height),
            _round_coordinate(panel_width * scale / width),
            _round_coordinate(panel_height * scale / height),
        ]
        panels.append({"id": view, "rect": rect})
    baseline = None if feet_y is None else _round_coordinate((feet_y * scale + offset_y) / height)
    return {"canvas": [width, height], "panels": panels, "feet_y": baseline}

