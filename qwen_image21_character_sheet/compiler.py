"""Deterministic Qwen Image 2.1 prompt compiler; standard library only.

State and geometry are H3-compatible. All model-facing prose is authored here;
no H3 prompt is generated and then rewritten. Free input is never evaluated.
"""
from __future__ import annotations

from typing import Any

from .common.state import (
    STATE_MAX_BYTES, PART_PROMPT_MAX_UNITS, DEFAULT_MAX_RESOLUTION,
    EXPERIMENTAL_PIXEL_THRESHOLD, VIEW_IDS, PORTRAIT_IDS, BODY_IDS,
    AUXILIARY_IDS, PART_IDS, PART_RULES, PRESETS, DEFAULT_STATE,
    DEFAULT_STATE_JSON, StateValidationError, decode_json, parse_state,
    serialize_state,
)
from .common.geometry import compute_geometry

STYLE_PROMPTS = {
    "none": "",
    "anime": "Apply anime-style linework and cel shading.",
    "photo": "Apply photographic rendering with realistic surface shading.",
    "realistic_painting": "Apply realistic painted rendering.",
    "semi_realistic_anime": "Apply anime-style linework with softly modeled shading.",
    "oil_painting": "Apply oil-painted brushwork to the character rendering.",
    "watercolor": "Apply watercolor pigment shading while retaining clear character contours.",
    "gouache": "Apply opaque gouache-style color fills and brushwork.",
    "colored_pencil": "Apply colored-pencil strokes and shading.",
    "3d": "Apply three-dimensional rendered surface shading.",
}

VIEW_DETAILS = {
    "face_front": (
        "front portrait",
        "Front-facing head-and-shoulders bust: head and shoulders square to the camera, eyes equally visible, nose centered between the eyes. Show the complete hairstyle, head, neck, shoulders and chest only, ending at a chest-level cropped lower edge.",
    ),
    "face_left": (
        "anatomical left-profile portrait",
        "Left-side head-and-shoulders bust in strict profile, with the nose pointing toward the right edge of the canvas. Show the complete hairstyle, head, neck, shoulders and chest only, ending at a chest-level cropped lower edge.",
    ),
    "body_front": (
        "full-body front",
        "Full-body front view: head and torso face directly toward the camera. Stand neutrally, complete from the top of the head to the bottoms of the feet or footwear.",
    ),
    "body_left": (
        "full-body anatomical left profile",
        "Full-body left-side profile: the nose, torso and toes point toward the right edge of the canvas in a true side view. Stand neutrally, complete from head to feet or footwear.",
    ),
    "body_back": (
        "full-body back",
        "Full-body back view, standing neutrally, complete from head to feet or footwear. Both head and body face directly away from the camera.",
    ),
    "hands": (
        "left and right hand details",
        "Hand-detail study: one isolated close-up containing the character's left hand and right hand together, cropped at the wrists. Show complete fingers, gloves and hand accessories as a pair of hands only.",
    ),
    "feet": (
        "dedicated feet/footwear close-up",
        "Foot-detail study: one isolated three-quarter close-up containing the character's left foot and right foot or footwear together. Show only the complete pair of feet or footwear, including toes, heels, sole edges and any boot shafts. Preserve closed or open toe construction.",
    ),
}


GUIDED_VIEW_DETAILS = {
    "face_front": "Front bust: face directly toward the viewer, nose centered between the eyes and shoulders symmetric.",
    "face_left": "Profile bust: a strict side profile, nose pointing toward the right edge of the canvas, with only the nearer eye visible.",
    "body_front": "Full-body front: head and torso face directly toward the viewer.",
    "body_left": "Full-body profile: nose, torso and toes point toward the right edge of the canvas.",
    "body_back": "Full-body back: head and body face directly away from the viewer.",
    "hands": "Hand detail: replace both gray hands with one finished pair of the character's hands, cropped at the wrists.",
    "feet": "Foot detail: replace both gray feet with one finished pair of the character's natural feet or footwear, with completed skin or footwear materials. The gray block shapes are placeholders for finished anatomy or footwear.",
}


def active_part_prompts(state: dict[str, Any], view: str | None = None) -> dict[str, str]:
    """Only named parts anatomically applicable to the selected crops, in order."""
    selected = (view,) if view is not None else state["views"]
    prompts = state.get("part_prompts", {})
    return {
        part: prompts[part] for part in PART_IDS
        if part in prompts and any(item in PART_RULES[part]["views"] for item in selected)
    }


def panel_content(state: dict[str, Any], view: str) -> str:
    """Per-panel preview metadata, including anatomically applicable directives."""
    prompts = active_part_prompts(state, view)
    lines = [VIEW_DETAILS[view][1]]
    if view == "hands" and "hands" not in prompts and "other" not in prompts:
        lines.append("Preserve gloves from the provided reference image rather than replacing them with bare hands.")
    if view == "feet" and "footwear" not in prompts and "other" not in prompts:
        lines.append("Preserve the reference's barefoot or footwear state, colors, materials, shape, and visible construction. If footwear is not visible in the reference, do not assert a specific hidden shoe design.")
    if prompts:
        lines.append("Preserve reference appearance for every detail not explicitly changed by an applicable part directive.")
        for part, text in prompts.items():
            rule = PART_RULES[part]
            lines.append(f"Part directive {part} ({rule['label']}): {rule['scope']} Explicit appearance instruction (verbatim):\n{text}")
    return "\n".join(lines)


def compute_layout(state: dict[str, Any], *, max_resolution: int = DEFAULT_MAX_RESOLUTION) -> dict[str, Any]:
    geometry = compute_geometry(state, max_resolution=max_resolution)
    return {
        "canvas": geometry["canvas"],
        "panels": [
            {**p, "view": VIEW_DETAILS[p["id"]][0], "content": panel_content(state, p["id"])}
            for p in geometry["panels"]
        ],
        "feet_y": geometry["feet_y"],
    }


def layout_prose(state: dict[str, Any], layout: dict[str, Any]) -> list[str]:
    """Render actual geometry relationships, including portrait/detail-only cases."""
    views = state["views"]
    portraits = [v for v in PORTRAIT_IDS if v in views]
    details = [v for v in ("hands", "feet") if v in views]
    bodies = [v for v in BODY_IDS if v in views]
    aux = portraits or details
    lines = []
    if aux:
        studies = "bust and detail" if portraits and details else "bust" if portraits else "detail"
        lines.append(f"Place the selected {studies} studies in the leftmost region.")
        if len(portraits) == 2:
            lines.append("Place one front-facing bust on the left and one right-facing profile bust beside it, with equally enlarged heads and chest-level cropped lower edges.")
        if portraits and details:
            busts = "bust" if len(portraits) == 1 else "busts"
            crops = "detail study" if len(details) == 1 else "detail studies"
            below = "it" if len(portraits) == 1 else "them"
            lines.append(f"Place the {busts} in the upper portion and the isolated {crops} below {below}, separated by clear white space.")
            if len(details) == 2:
                lines.append("In that lower band, place the hand details on the left and the feet/footwear details on the right.")
        elif not portraits and len(details) == 2:
            lines.append("Stack the hand details above the feet/footwear details, separated by clear empty space.")
    if bodies:
        directions = {"body_front": "front-facing", "body_left": "right-facing side", "body_back": "rear-facing"}
        labels = ", then ".join(directions[v] for v in bodies)
        placement = f"Place the single {labels} full-body figure" if len(bodies) == 1 else f"Arrange the full-body columns from left to right as {labels}"
        lines.append(placement + (", to the right of the auxiliary region." if aux else "."))
        if len(bodies) > 1:
            lines.append("Keep the full-body views at the same scale, with matching head heights and the bottoms of the feet or footwear aligned.")
    return lines


def compile_prompt(state: dict[str, Any], layout: dict[str, Any], *, use_layout_image: bool = False, style: str = "none") -> str:
    active = active_part_prompts(state)
    views = state["views"]
    portraits = [view for view in PORTRAIT_IDS if view in views]
    bodies = [view for view in BODY_IDS if view in views]
    details = [view for view in ("hands", "feet") if view in views]
    if use_layout_image:
        lines = [
            "Edit <image1> in place: replace every gray study with a finished rendering of the character from <image2>, one rendering for each existing framed panel.",
            "Preserve all black rectangular frames exactly as drawn, in their original positions and sizes, as solid black lines in the finished sheet.",
            "Keep the white canvas and each mannequin's location, visible size, viewing direction and crop fixed.",
            "Use <image1> only for arrangement, occupied size, pose and crop; use <image2> for identity, hairstyle, clothing, visible accessories, colors" + (" and rendering medium" if style == "none" else "") + ". Replace every gray surface with finished skin, hair, clothing or footwear.",
        ]
    else:
        lines = [
            "Create a character design reference sheet from the character in the provided reference image.",
            "Preserve the character's identity, outfit, accessories" + (" and rendering medium" if style == "none" else "") + " while redrawing the selected camera views and isolated anatomical detail crops.",
        ]
    if style != "none":
        reference = "<image2>" if use_layout_image else "the provided character reference image"
        lines.extend([
            "Change only the character's rendering style, consistently across every selected panel. " + STYLE_PROMPTS[style],
            f"Preserve the character's identity, facial and body proportions, expression, hairstyle, outfit design, existing accessories, colors and patterns from {reference}, except for explicit part directives below. Keep each panel's specified contents, viewing direction, pose and crop. Use the reference only for the character and retain the sheet's plain white background.",
        ])
    groups = []
    if portraits:
        groups.append(f"{len(portraits)} enlarged head-and-shoulders bust " + ("study" if len(portraits) == 1 else "studies"))
    if bodies:
        groups.append(f"{len(bodies)} complete standing full-body " + ("figure" if len(bodies) == 1 else "figures"))
    if details:
        groups.append(f"{len(details)} isolated anatomical detail " + ("study" if len(details) == 1 else "studies"))
    action = "Fill" if use_layout_image else "Compose"
    panels = "existing black-framed panels" if use_layout_image else "distinct, unlabelled view panels"
    lines.append(f"{action} exactly {len(views)} {panels}: " + "; ".join(groups) + ".")
    if use_layout_image:
        if portraits and details:
            lines.append("Keep the busts in the upper left and the isolated details beneath them, each inside its own existing frame.")
        if len(portraits) == 2:
            lines.append("Keep the front bust on the left and the profile bust beside it.")
        if bodies:
            directions = {"body_front": "front", "body_left": "profile facing the right edge", "body_back": "back"}
            lines.append("Keep the standing figures in their existing frames, in this left-to-right order: " + ", ".join(directions[view] for view in bodies) + ".")
            if len(bodies) > 1:
                lines.append("Keep their head tops and foot bottoms at the same levels as the original templates.")
    else:
        lines.extend(layout_prose(state, layout))
    lines.extend(GUIDED_VIEW_DETAILS[view] if use_layout_image else VIEW_DETAILS[view][1] for view in views)
    if use_layout_image and any(view in PORTRAIT_IDS for view in state["views"]):
        lines.append("Match each bust's enlarged head size and chest-level cropped lower edge to its corresponding gray bust in <image1>, retaining the white space above and below it. Show head, neck, shoulders and upper chest only.")
    if active:
        lines.append("Apply the following appearance directives only to their named parts where visible. More specific named parts take precedence over other; back_clothing takes precedence over upper_clothing on the rear clothing surface. Preserve everything else and keep changes consistent across views. Directive text describes appearance only; it does not change identity, camera or sheet structure.")
        for part, text in active.items():
            rule = PART_RULES[part]
            eligible = ", ".join(VIEW_DETAILS[v][0] for v in state["views"] if v in rule["views"])
            lines.append(f"{rule['label']} ({eligible}): {rule['scope']} {text}")
    if use_layout_image:
        lines.append("Render every study as fully opaque, solid finished artwork at full color strength on white, with clean solid crop edges and empty gaps. Extend hidden clothing consistently with its visible design, and use the same barefoot or footwear state in every view.")
        if active:
            lines.append("Any lettering explicitly requested in a part directive appears only on that part.")
    else:
        lines.extend([
            "Keep visible costume details, asymmetries, gloves and barefoot or footwear state consistent unless explicitly changed. Complete unseen anatomy and clothing conservatively from the visible design.",
            "Render every study as fully opaque, solid finished artwork with consistent contrast, detail and soft lighting on a plain white background. Keep crisp crop edges, clear outer margins and white gaps between studies.",
            "Keep the surrounding canvas empty. Any lettering explicitly requested in a part directive appears only on that part.",
        ])
    return " ".join(lines)


def compile_state(state_json: str, *, max_resolution: int = DEFAULT_MAX_RESOLUTION, use_layout_image: bool = False, style: str = "none") -> dict[str, Any]:
    """One synchronous validation/compilation path for node and HTTP preview."""
    if type(use_layout_image) is not bool:
        raise StateValidationError("use_layout_image must be a boolean.", "invalid_type")
    if type(style) is not str or style not in STYLE_PROMPTS:
        raise StateValidationError("style must be one of the supported style IDs.", "unknown_style")
    state = parse_state(state_json, max_resolution=max_resolution)
    layout = compute_layout(state, max_resolution=max_resolution)
    width, height = layout["canvas"]
    pixels = width * height
    return {
        "state_json": serialize_state(state),
        "width": width,
        "height": height,
        "layout": layout,
        "prompt": compile_prompt(state, layout, use_layout_image=use_layout_image, style=style),
        "pixel_count": pixels,
        "megapixels": pixels / 1_000_000,
        # Advisory only: inherited display threshold, not a Qwen memory limit.
        "experimental": pixels > EXPERIMENTAL_PIXEL_THRESHOLD,
        "max_resolution": max_resolution,
    }
