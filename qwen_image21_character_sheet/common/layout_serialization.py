"""Stable coordinate serialization, shared with the H3 baseline."""
import json
from typing import Any

def _coordinate_text(value: float) -> str:
    return f"{value:.6f}"  # Fixed six-place notation, never scientific notation.


def layout_json(layout: dict[str, Any]) -> str:
    """Stable compact JSON with fixed six-decimal normalized coordinate tokens."""
    panels = []
    for panel in layout["panels"]:
        panels.append(
            '{"id":' + json.dumps(panel["id"])
            + ',"rect":[' + ",".join(_coordinate_text(value) for value in panel["rect"]) + "]"
            + ',"view":' + json.dumps(panel["view"], ensure_ascii=True)
            + ',"content":' + json.dumps(panel["content"], ensure_ascii=True) + "}"
        )
    baseline = "null" if layout["feet_y"] is None else _coordinate_text(layout["feet_y"])
    return '{"canvas":[' + ",".join(str(value) for value in layout["canvas"]) + '],"panels":[' + ",".join(panels) + '],"feet_y":' + baseline + "}"

