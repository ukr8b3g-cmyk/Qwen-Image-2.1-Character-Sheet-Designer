"""H3-compatible character-sheet semantic state; vendored from bf792c65.

All layout arithmetic is rational. Only the final normalized coordinates are
rounded, using round-half-up to six places. This module has no ComfyUI imports,
network requests, model execution, or filesystem side effects.
"""

from __future__ import annotations

import json
from fractions import Fraction
from typing import Any

STATE_MAX_BYTES = 64 * 1024
PART_PROMPT_MAX_UNITS = 1000
DEFAULT_MAX_RESOLUTION = 16384  # Standalone compiler default; node uses Core at runtime.
EXPERIMENTAL_PIXEL_THRESHOLD = 1_032_192
VIEW_IDS = ("face_front", "face_left", "body_front", "body_left", "body_back", "hands", "feet")
PORTRAIT_IDS = ("face_front", "face_left")
BODY_IDS = ("body_front", "body_left", "body_back")
AUXILIARY_IDS = (*PORTRAIT_IDS, "hands", "feet")
PART_IDS = ("head_hair", "face", "upper_clothing", "back_clothing", "lower_body", "hands", "footwear", "other")
# These rules are the single source of truth for panel JSON and panel prose.
# Visibility is a camera/anatomy constraint, never inferred from free-form text.
PART_RULES = {
    "head_hair": {
        "label": "head, hair, and headwear",
        "views": (*PORTRAIT_IDS, *BODY_IDS),
        "scope": "Apply only to the head, hair, and headwear where visible from this panel's assigned camera angle.",
    },
    "face": {
        "label": "face",
        "views": (*PORTRAIT_IDS, *BODY_IDS),
        "scope": "Apply only to facial areas actually visible from this panel's assigned camera angle; do not turn the head or reveal the face in a rear view.",
    },
    "upper_clothing": {
        "label": "upper clothing",
        "views": (*PORTRAIT_IDS, *BODY_IDS),
        "scope": "Apply only to visible upper clothing. A back_clothing directive is more specific on the rear clothing surface.",
    },
    "back_clothing": {
        "label": "rear clothing surface",
        "views": ("body_left", "body_back"),
        "scope": "Apply only to the rear clothing surface: in body_left only where that rear surface is visible from the fixed left-profile camera, and in body_back. Never move this rear-surface design onto the front, side surface, or portraits; do not turn the subject to reveal it.",
    },
    "lower_body": {
        "label": "lower body and lower clothing",
        "views": BODY_IDS,
        "scope": "Apply only to the visible lower body and lower clothing, excluding the separate footwear part.",
    },
    "hands": {
        "label": "hands, gloves, and hand accessories",
        "views": (*BODY_IDS, "hands"),
        "scope": "Apply only to hands, gloves, and hand accessories where visible from this panel's assigned camera angle.",
    },
    "footwear": {
        "label": "feet and footwear",
        "views": (*BODY_IDS, "feet"),
        "scope": "Apply only to feet and footwear wherever visible, including full-body views independently of whether a separate feet detail panel is selected.",
    },
    "other": {
        "label": "other appearance details",
        "views": VIEW_IDS,
        "scope": "Apply across the selected views wherever the described appearance details are anatomically visible. More specific named-part directives take precedence for their parts. Preserve the assigned views, framing, layout, single identity, and static-sheet requirements.",
    },
}
# ECMAScript String.trim whitespace, for exact Python/browser normalization parity.
_BLANK_CHARACTERS = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
PRESETS = {
    "five": ("face_front", "face_left", "body_front", "body_left", "body_back"),
    "basic": ("face_front", "body_front", "body_left", "body_back"),
    "detail": VIEW_IDS,
    "turnaround": BODY_IDS,
    "single": ("body_front",),
}
DEFAULT_STATE = {
    "schema_version": 1,
    "views": list(PRESETS["five"]),
    "size": {
        "mode": "auto",
        "body_height": 1120,
        "manual_width": 2208,
        "manual_height": 1280,
    },
}
DEFAULT_STATE_JSON = json.dumps(DEFAULT_STATE, separators=(",", ":"))


class StateValidationError(ValueError):
    """An invalid saved state; callers must retain the original input unchanged."""

    def __init__(self, message: str, code: str = "invalid_state") -> None:
        super().__init__(message)
        self.code = code


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StateValidationError(f"Duplicate JSON key: {key}.", "duplicate_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StateValidationError(f"Non-finite JSON number is not allowed: {value}.", "non_finite")


def decode_json(text: str, *, byte_limit: int = STATE_MAX_BYTES) -> Any:
    """Parse bounded strict JSON, rejecting duplicate keys and non-finite numbers."""
    if not isinstance(text, str):
        raise StateValidationError("state_json must be a JSON string.", "invalid_type")
    if len(text) > byte_limit:
        raise StateValidationError(f"JSON exceeds the {byte_limit}-byte limit.", "state_too_large")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise StateValidationError("JSON must be valid UTF-8.", "invalid_utf8") from exc
    if size > byte_limit:
        raise StateValidationError(f"JSON exceeds the {byte_limit}-byte limit.", "state_too_large")
    try:
        result = json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
        _validate_unicode(result)
        return result
    except StateValidationError:
        raise
    except (ValueError, RecursionError) as exc:
        raise StateValidationError("Invalid JSON: a valid finite JSON document is required.", "invalid_json") from exc


def _validate_unicode(value: Any) -> None:
    """Reject unpaired surrogate escapes as well as invalid literal UTF-8."""
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise StateValidationError("JSON strings must contain valid Unicode.", "invalid_utf8") from exc
    elif isinstance(value, dict):
        for key, item in value.items():
            _validate_unicode(key)
            _validate_unicode(item)
    elif isinstance(value, list):
        for item in value:
            _validate_unicode(item)


def _exact_keys(value: Any, keys: tuple[str, ...], path: str) -> None:
    if type(value) is not dict:
        raise StateValidationError(f"{path} must be an object.", "invalid_type")
    missing = set(keys) - value.keys()
    unknown = value.keys() - set(keys)
    if missing:
        raise StateValidationError(f"{path} is missing required keys: {', '.join(sorted(missing))}.", "missing_key")
    if unknown:
        raise StateValidationError(f"{path} contains unknown keys: {', '.join(sorted(unknown))}.", "unknown_key")


def _check_max_resolution(max_resolution: int) -> None:
    if type(max_resolution) is not int or max_resolution < 32:
        raise ValueError("max_resolution must be an integer of at least 32.")


def _size_value(value: Any, field: str, max_resolution: int) -> int:
    if type(value) is not int:
        raise StateValidationError(f"{field} must be an integer (not a boolean, decimal, or numeric string).", "invalid_integer")
    if value < 32 or value % 32 != 0:
        raise StateValidationError(f"{field} must be at least 32 and a multiple of 32.", "invalid_size")
    if value > max_resolution:
        raise StateValidationError(f"{field} exceeds Core MAX_RESOLUTION ({max_resolution}).", "size_limit")
    return value


def parse_state(state_json: str, *, max_resolution: int = DEFAULT_MAX_RESOLUTION) -> dict[str, Any]:
    """Validate all fields and return a fresh, canonically ordered semantic state."""
    _check_max_resolution(max_resolution)
    state = decode_json(state_json)
    if type(state) is not dict:
        raise StateValidationError("state must be an object.", "invalid_type")
    if "schema_version" not in state:
        raise StateValidationError("state is missing required keys: schema_version.", "missing_key")
    version = state["schema_version"]
    if type(version) is not int or version not in (1, 2):
        raise StateValidationError("schema_version must be the integer 1 or 2; no automatic migration is performed.", "unsupported_schema")
    keys = ("schema_version", "views", "size") + (("part_prompts",) if version == 2 else ())
    _exact_keys(state, keys, "state")
    views = state["views"]
    if type(views) is not list or any(type(view) is not str for view in views):
        raise StateValidationError("views must be an array of view-ID strings.", "invalid_type")
    if not views:
        raise StateValidationError("Select at least one view.", "empty_views")
    unknown = set(views) - set(VIEW_IDS)
    if unknown:
        raise StateValidationError(f"Unknown view IDs: {', '.join(sorted(unknown))}.", "unknown_view")
    size = state["size"]
    _exact_keys(size, ("mode", "body_height", "manual_width", "manual_height"), "size")
    if type(size["mode"]) is not str or size["mode"] not in ("auto", "manual"):
        raise StateValidationError("size.mode must be auto or manual.", "invalid_mode")
    normalized_size = {"mode": size["mode"]}
    for key in ("body_height", "manual_width", "manual_height"):
        normalized_size[key] = _size_value(size[key], f"size.{key}", max_resolution)
    normalized = {"schema_version": version, "views": [view for view in VIEW_IDS if view in views], "size": normalized_size}
    if version == 2:
        prompts = state["part_prompts"]
        if type(prompts) is not dict:
            raise StateValidationError("part_prompts must be an object.", "invalid_type")
        unknown = prompts.keys() - set(PART_IDS)
        if unknown:
            raise StateValidationError(f"Unknown part IDs: {', '.join(sorted(unknown))}.", "unknown_part")
        normalized_prompts = {}
        for part in PART_IDS:
            if part not in prompts:
                continue
            text = prompts[part]
            if type(text) is not str:
                raise StateValidationError(f"part_prompts.{part} must be a string.", "invalid_type")
            if len(text.encode("utf-16-le")) // 2 > PART_PROMPT_MAX_UNITS:
                raise StateValidationError(f"part_prompts.{part} exceeds the {PART_PROMPT_MAX_UNITS} UTF-16 code-unit limit.", "part_prompt_too_long")
            if text.strip(_BLANK_CHARACTERS):
                normalized_prompts[part] = text
        normalized["part_prompts"] = normalized_prompts
    return normalized


def serialize_state(state: dict[str, Any]) -> str:
    """Serialize a state already returned by parse_state in the schema key order."""
    return json.dumps(state, ensure_ascii=True, separators=(",", ":"), allow_nan=False)

