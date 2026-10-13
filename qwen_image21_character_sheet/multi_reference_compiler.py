"""Multi Reference v3 state and H3-derived geometry; Qwen-specific prompt compiler."""

from fractions import Fraction
import json

from .common.state import (
    BODY_IDS, DEFAULT_MAX_RESOLUTION, EXPERIMENTAL_PIXEL_THRESHOLD, PART_IDS,
    PART_PROMPT_MAX_UNITS, PART_RULES, PRESETS, StateValidationError, VIEW_IDS,
    _BLANK_CHARACTERS, _check_max_resolution, _exact_keys, _size_value,
    decode_json, parse_state, serialize_state,
)
from .common.geometry import _ceil_32, _round_coordinate
from .compiler import STYLE_PROMPTS, compute_layout
from .reference_plan import EXTRA_INPUTS, REFERENCE_ROLES, build_reference_plan
from .multi_guide_geometry import body_baseline, body_artwork_placements

PORTRAIT_IDS = (
    "face_front", "face_left", "face_right", "face_3q_left",
    "face_3q_right", "face_back",
)
CLOTHING_IDS = ("clothing_front", "clothing_back")
MULTI_VIEW_IDS = (*PORTRAIT_IDS, *BODY_IDS, *CLOTHING_IDS, "hands", "feet")
MULTI_PRESETS = {
    **PRESETS, "detail": MULTI_VIEW_IDS, "head": PORTRAIT_IDS,
    "clothing": CLOTHING_IDS,
}
HAND_STATES = ('reference', 'bare', 'gloved')
CLOTHING_MODES = ('worn', 'garment')
CLOTHING_TYPES = ('reference', 'pants', 'skirt_robe')
FOOTWEAR_STATES = ('reference', 'shod', 'unshod')
DEFAULT_MULTI_STATE = {
    "schema_version": 3, "views": list(PRESETS["five"]),
    "size": {"mode": "auto", "body_height": 1120,
             "manual_width": 2208, "manual_height": 1280},
    "part_prompts": {},
    "reference_roles": {key: "same_character" for key in EXTRA_INPUTS},
    "hand_state": "reference", "clothing_mode": "worn",
}
DEFAULT_MULTI_STATE_JSON = serialize_state(DEFAULT_MULTI_STATE)
VIEW_DETAILS = {
    "face_front": ("front bust", "A front-facing bust, complete head and hair through the upper chest; both eyes visible."),
    "face_left": ("anatomical left-profile bust", "A strict anatomical left-profile bust, head and hair through the upper chest. Camera on the person's anatomical LEFT side, seeing only the left side of the face. Nose points to the LEFT edge of the final image; one visible eye. No front or three-quarter view; do not mirror the character's asymmetric features."),
    "face_right": ("anatomical right-profile bust", "A strict anatomical right-profile bust, head and hair through the upper chest. Camera on the person's anatomical RIGHT side, seeing only the right side of the face. Nose points to the RIGHT edge of the final image; one visible eye. No front or three-quarter view; do not mirror the character's asymmetric features."),
    "face_3q_left": ("anatomical left three-quarter bust", "A front-left three-quarter bust, head and hair through the upper chest. Camera halfway between the front and the person's anatomical LEFT side, at 45 degrees. Nose points toward the LEFT edge of the final image; both eyes visible, the far eye foreshortened. Not frontal and not a strict profile."),
    "face_3q_right": ("anatomical right three-quarter bust", "A front-right three-quarter bust, head and hair through the upper chest. Camera halfway between the front and the person's anatomical RIGHT side, at 45 degrees. Nose points toward the RIGHT edge of the final image; both eyes visible, the far eye foreshortened. Not frontal and not a strict profile."),
    "face_back": ("rear bust", "A direct rear bust, complete back of head and hair through the upper chest. No face or eyes visible; do not turn the head."),
    "body_front": ("full-body front", "A neutral standing front view, complete head and hair through both feet or footwear; leave clear space above the head and below the soles."),
    "body_left": ("full-body anatomical left profile", "A strict anatomical left-profile neutral standing view. Camera on the person's anatomical LEFT side. Nose, chest and toes point to the LEFT edge of the final image. Include the complete head through feet or footwear; do not mirror asymmetric clothing or accessories."),
    "body_back": ("full-body back", "A direct rear neutral standing view, complete head and hair through feet or footwear. No face visible; do not turn the head."),
    "clothing_front": ("clothing front", "A front-facing detail of the same referenced outfit as worn, neck through its complete lowest clothing edge. Omit the head. Preserve the referenced garment construction, silhouette, sleeve lengths, hems, colors and patterns, except for applicable explicit clothing directives. Do not replace its garment type or add separate leg openings."),
    "clothing_back": ("clothing back", "A direct rear detail of the same referenced outfit as worn, neck through its complete lowest clothing edge. Omit the head. Preserve the same garment construction, silhouette, sleeve lengths, hems, colors and patterns, except for applicable explicit clothing directives; infer unseen rear surfaces conservatively."),
    "hands": ("hands detail", "One isolated close-up of both complete hands, cropped at the wrists. Follow the referenced hand appearance unless an explicit applicable directive changes it. No head, torso or whole figure."),
    "feet": ("feet and footwear detail", "One isolated close-up of both complete feet or footwear, including visible boot shafts. Keep the resulting barefoot or footwear design; closed shoes do not expose bare toes. No head, torso or whole figure."),
}
MULTI_PART_VIEWS = {
    "head_hair": (*PORTRAIT_IDS, *BODY_IDS),
    "face": (*PORTRAIT_IDS[:-1], "body_front", "body_left"),
    "upper_clothing": (*PORTRAIT_IDS, *BODY_IDS, *CLOTHING_IDS),
    "back_clothing": ("face_left", "face_right", "face_back", "body_left", "body_back", "clothing_back"),
    "lower_body": (*BODY_IDS, *CLOTHING_IDS),
    "hands": (*BODY_IDS, "hands"),
    "footwear": (*BODY_IDS, "feet"),
    "other": MULTI_VIEW_IDS,
}
MULTI_PART_SCOPES = {
    **{part: rule["scope"] for part, rule in PART_RULES.items()},
    "back_clothing": "Apply only to the rear clothing surface actually visible from the panel's fixed camera, including a rear bust or rear clothing detail. Never move rear designs onto front surfaces or turn the subject to reveal them.",
    "hands": "Apply only to visible hands and their accessories. A selected hand-state override takes precedence only for whether the hands are covered; keep other hand details from this directive.",
}


def part_views(state, part):
    views = MULTI_PART_VIEWS[part]
    if part == 'hands' and state['clothing_mode'] == 'worn':
        views = (*views, *CLOTHING_IDS)
    return views


def panel_details(state, view):
    if view in CLOTHING_IDS and state['clothing_mode'] == 'garment':
        side = 'FRONT' if view == 'clothing_front' else 'REAR'
        return (f'garments only, {side.lower()}',
                f'An isolated {side} view of the same referenced garments ONLY. No head, neck, arms, hands, legs, feet, torso, skin, person, mannequin or body inside the garments. Preserve the complete referenced clothing silhouette, construction, openings, sleeve lengths, hems, colors and patterns except for applicable explicit clothing directives. Empty sleeves and clothing openings must not contain limbs. Do not replace the garment type or split a continuous hem into separate leg openings.')
    return VIEW_DETAILS[view]


def role_views(state, role):
    if role == 'clothing_front':
        return (*PORTRAIT_IDS[:-1], 'body_front', 'body_left', 'clothing_front')
    part = {'face': 'face', 'head': 'head_hair', 'clothing': 'upper_clothing',
            'clothing_back': 'back_clothing', 'hands': 'hands', 'footwear': 'footwear'}.get(role)
    return part_views(state, part) if part else ()


def parse_multi_state(raw, *, max_resolution=DEFAULT_MAX_RESOLUTION):
    _check_max_resolution(max_resolution)
    state = decode_json(raw)
    if type(state) is not dict:
        raise StateValidationError("state must be an object.", "invalid_type")
    version = state.get("schema_version")
    if type(version) is int and version in (1, 2):
        legacy = parse_state(raw, max_resolution=max_resolution)
        return {**legacy, "schema_version": 3,
                "part_prompts": legacy.get("part_prompts", {}),
                "reference_roles": {key: "same_character" for key in EXTRA_INPUTS},
                "hand_state": "reference", "clothing_mode": "worn"}
    if type(version) is not int or version != 3:
        raise StateValidationError("MultiReference supports schema_version 1, 2 or 3.", "unsupported_schema")
    state = {**state, 'hand_state': state.get('hand_state', 'reference'),
             'clothing_mode': state.get('clothing_mode', 'worn')}
    choices = {key: state[key] for key in ('clothing_type', 'footwear_state') if key in state}
    _exact_keys(state, ("schema_version", "views", "size", "part_prompts", "reference_roles", "hand_state", "clothing_mode", *choices), "state")
    for field, allowed in (('clothing_type', CLOTHING_TYPES), ('footwear_state', FOOTWEAR_STATES)):
        if field in choices and (type(choices[field]) is not str or choices[field] not in allowed):
            raise StateValidationError(f'Unknown {field}.', 'invalid_' + field)
    if type(state['hand_state']) is not str or state['hand_state'] not in HAND_STATES:
        raise StateValidationError('Unknown hand state.', 'invalid_hand_state')
    if type(state['clothing_mode']) is not str or state['clothing_mode'] not in CLOTHING_MODES:
        raise StateValidationError('Unknown clothing mode.', 'invalid_clothing_mode')
    views = state["views"]
    if type(views) is not list or any(type(view) is not str for view in views):
        raise StateValidationError("views must be an array of view-ID strings.", "invalid_type")
    if not views:
        raise StateValidationError("Select at least one view.", "empty_views")
    if set(views) - set(MULTI_VIEW_IDS):
        raise StateValidationError("Unknown MultiReference view IDs.", "unknown_view")
    size = state["size"]
    _exact_keys(size, ("mode", "body_height", "manual_width", "manual_height"), "size")
    if type(size["mode"]) is not str or size["mode"] not in ("auto", "manual"):
        raise StateValidationError("size.mode must be auto or manual.", "invalid_mode")
    normalized_size = {"mode": size["mode"]}
    for field in ("body_height", "manual_width", "manual_height"):
        normalized_size[field] = _size_value(size[field], f"size.{field}", max_resolution)
    prompts = state["part_prompts"]
    if type(prompts) is not dict:
        raise StateValidationError("part_prompts must be an object.", "invalid_type")
    if prompts.keys() - set(PART_IDS):
        raise StateValidationError("Unknown part IDs.", "unknown_part")
    normalized_prompts = {}
    for part in PART_IDS:
        if part not in prompts:
            continue
        text = prompts[part]
        if type(text) is not str:
            raise StateValidationError("Part prompts must be strings.", "invalid_type")
        if len(text.encode("utf-16-le")) // 2 > PART_PROMPT_MAX_UNITS:
            raise StateValidationError("Part prompt exceeds 1000 UTF-16 code units.", "part_prompt_too_long")
        if text.strip(_BLANK_CHARACTERS):
            normalized_prompts[part] = text
    roles = state["reference_roles"]
    if type(roles) is dict and "reference_image_3" not in roles:
        _exact_keys(roles, EXTRA_INPUTS[:-1], "reference_roles")
        roles = {**roles, "reference_image_3": "same_character"}
    else:
        _exact_keys(roles, EXTRA_INPUTS, "reference_roles")
    if any(type(roles[key]) is not str or roles[key] not in REFERENCE_ROLES for key in EXTRA_INPUTS):
        raise StateValidationError("Unknown reference role.", "unknown_reference_role")
    return {
        "schema_version": 3,
        "views": [view for view in MULTI_VIEW_IDS if view in views],
        "size": normalized_size, "part_prompts": normalized_prompts,
        "reference_roles": {key: roles[key] for key in EXTRA_INPUTS},
        "hand_state": state['hand_state'], "clothing_mode": state['clothing_mode'],
        **choices,
    }


def _ideal_multi_layout(views, h):
    h = Fraction(h)
    margin, gap, body_w, aux_w = h / 14, h / 25, 2 * h / 5, h / 2
    portraits = [view for view in PORTRAIT_IDS if view in views]
    bodies = [view for view in BODY_IDS if view in views]
    clothes = [view for view in CLOTHING_IDS if view in views]
    details = [view for view in ("hands", "feet") if view in views]
    groups = []
    if portraits:
        cols = min(2, len(portraits))
        rows = (len(portraits) + cols - 1) // cols
        cell_h = (h - (rows - 1) * gap) / rows
        rects = {view: (i % cols * (aux_w + gap), i // cols * (cell_h + gap), aux_w, cell_h)
                 for i, view in enumerate(portraits)}
        groups.append((cols * aux_w + (cols - 1) * gap, rects))
    for view in (*bodies, *clothes):
        groups.append((body_w, {view: (Fraction(0), Fraction(0), body_w, h)}))
    if details:
        cell_h = (h - (len(details) - 1) * gap) / len(details)
        groups.append((aux_w, {view: (Fraction(0), i * (cell_h + gap), aux_w, cell_h)
                               for i, view in enumerate(details)}))
    width = sum(group[0] for group in groups) + (len(groups) - 1) * gap + 2 * margin
    rects, x = {}, margin
    for group_w, group in groups:
        for view, (left, top, w, height) in group.items():
            rects[view] = (x + left, margin + top, w, height)
        x += group_w + gap
    return width, h + 2 * margin, rects, margin + h if bodies else None


def compute_multi_layout(state, *, max_resolution=DEFAULT_MAX_RESOLUTION):
    views, size = state["views"], state["size"]
    if set(views).issubset(VIEW_IDS):
        # Use exact legacy arithmetic, including its detail-band layouts.
        layout = compute_layout({"views": views, "size": size, "part_prompts": {}},
                                max_resolution=max_resolution)
        return finish_layout(state, layout)
    ideal_w, ideal_h, rects, feet_y = _ideal_multi_layout(views, size["body_height"])
    width, height = ((_ceil_32(ideal_w), _ceil_32(ideal_h)) if size["mode"] == "auto"
                     else (size["manual_width"], size["manual_height"]))
    for name, value in (("output width", width), ("output height", height)):
        _size_value(value, name, max_resolution)
    scale = Fraction(1) if size["mode"] == "auto" else min(Fraction(width) / ideal_w, Fraction(height) / ideal_h)
    ox, oy = (width - ideal_w * scale) / 2, (height - ideal_h * scale) / 2
    panels = []
    for view in views:
        left, top, w, h = rects[view]
        rect = [_round_coordinate((left * scale + ox) / width),
                _round_coordinate((top * scale + oy) / height),
                _round_coordinate(w * scale / width), _round_coordinate(h * scale / height)]
        panels.append({"id": view, "rect": rect, "view": VIEW_DETAILS[view][0],
                       "content": VIEW_DETAILS[view][1]})
    baseline = None if feet_y is None else _round_coordinate((feet_y * scale + oy) / height)
    return finish_layout(state, {"canvas": [width, height], "panels": panels, "feet_y": baseline})


def finish_layout(state, layout):
    panels = [{**panel, 'view': panel_details(state, panel['id'])[0],
               'content': panel_details(state, panel['id'])[1]} for panel in layout['panels']]
    result = {**layout, 'panels': panels}
    result['feet_y'] = body_baseline(result)
    return result


ROLE_INSTRUCTIONS = {
    "same_character": "Supplement the same person's identity and unseen details from this additional angle. Do not introduce a second character, pose, background or layout.",
    "face": "Use only facial anatomy, eyes, nose, mouth and facial skin. Do not transfer hair, clothing, body proportions, pose or background.",
    "head": "Use only the face, hair, head and headwear. Do not transfer clothing, body proportions, pose or background.",
    "clothing": "Use only the complete outfit's construction, colors, materials and patterns. Ignore the source person's face, body proportions, pose and background.",
    "clothing_front": "Use only FRONT surfaces of the outfit. Do not move front designs onto the back. Ignore the source person's head, physique, pose and background.",
    "clothing_back": "Use only REAR surfaces of the outfit where visible from each fixed camera. Do not move rear designs onto the front or rotate the character to reveal them.",
    "hands": "Use only the referenced hand appearance and hand accessories wherever hands are visible, even when no hands detail panel is selected. Do not invent coverings absent from the reference; explicit hand-state or part directives may override its appearance. Ignore unrelated anatomy, pose and background.",
    "footwear": "Use only feet, shoes, boots and foot accessories wherever feet are visible, even when no footwear detail panel is selected. Ignore unrelated anatomy, pose and background.",
}


def _layout_prose(state, layout):
    """Describe the computed arrangement, including legacy seven-view layouts."""
    panels = layout['panels']
    if layout.get('layout_version') == 'adaptive-1':
        descriptions = [f"{panel['view']} occupies normalized [left, top, width, height] {panel['rect']}." for panel in panels]
        descriptions.append('Within each row of full-body panels, keep the same figure height and align the soles. Separate rows have separate baselines. Preserve complete heads and feet and every assigned crop.')
        return descriptions
    if len(panels) == 1:
        return ['Center the single selected study with clear white margins.']
    # Group panels with the same horizontal origin/width instead of assuming
    # that legacy detail-band layouts have the new thirteen-view column order.
    columns = {}
    for panel in panels:
        x, y, w, _ = panel['rect']
        columns.setdefault((x, w), []).append(panel)
    result = []
    for index, (_, group) in enumerate(sorted(columns.items())):
        labels = [panel_details(state, p['id'])[0] for p in sorted(group, key=lambda p: p['rect'][1])]
        result.append(f"Region {index + 1} from the left: " + ' above '.join(labels) + '.')
    if len([v for v in state['views'] if v in BODY_IDS]) > 1:
        result.append('Keep the complete standing figures at the same scale, with matching head heights and aligned soles or footwear bottoms.')
    return result


def compile_multi_prompt(state, layout, plan, *, use_layout_image=False, style='none'):
    """Author Qwen image-edit prose directly; preserve literal user directives."""
    refs = {item['source']: item for item in plan.references}
    if 'character_image' not in refs:
        raise StateValidationError('Connect the character_image input.', 'missing_character')
    character = refs['character_image']['tag']
    active = {part: text for part, text in state['part_prompts'].items()
              if any(view in part_views(state, part) for view in state['views'])}
    extras = [ref for ref in plan.references if ref['source'] in EXTRA_INPUTS
              and (ref['role'] == 'same_character' or any(v in role_views(state, ref['role']) for v in state['views']))]
    if use_layout_image:
        guide = refs['layout_image']['tag']
        action = (f'Edit {guide} in place into one completed static character design sheet of the character from {character}. '
                  'Preserve every solid black rectangular frame exactly in its original position and size. '
                  'Replace gray mannequins with finished character studies; fill blank garment-only frames with the referenced garments. '
                  'Keep the white canvas, occupied sizes, viewing directions and crops.')
    else:
        action = (f'Create one completed static character design reference sheet of the character from {character} on a plain white canvas. '
                  'Compose only the selected studies with white gaps and clear margins, without panel borders or alignment lines.')
    lines = [action, '']
    lines.append(f'{character} supplies the baseline identity, facial and body proportions, hairstyle, outfit, accessories, colors and rendering medium. Ignore its background and pose.')
    if use_layout_image:
        lines.append(f'{guide} is a layout guide only: its frames, positions, sizes, orientations and crops are structural. Gray mannequins are placeholders, never identity, anatomy, physique or outfit references.')
    for ref in extras:
        role = ref['role']
        lines.append(f"{ref['tag']} is an additional {role} reference. {ROLE_INSTRUCTIONS[role]}")
        if role != 'same_character':
            eligible = [panel_details(state, v)[0] for v in state['views'] if v in role_views(state, role)]
            lines.append('Use it only on the relevant visible surfaces in these selected studies: ' + ', '.join(eligible) + '.')
    lines.append('')
    groups = []
    for ids, singular, plural in (
        (PORTRAIT_IDS, 'enlarged bust study', 'enlarged bust studies'),
        (BODY_IDS, 'complete standing full-body figure', 'complete standing full-body figures'),
        (CLOTHING_IDS, 'clothing study', 'clothing studies'),
        (('hands', 'feet'), 'isolated anatomical detail study', 'isolated anatomical detail studies'),
    ):
        count = sum(v in ids for v in state['views'])
        if count:
            groups.append(f'{count} {singular if count == 1 else plural}')
    lines.append(f"Exactly {len(state['views'])} selected studies, each appearing once: " + '; '.join(groups) + '.')
    lines.extend(_layout_prose(state, layout))
    lines.append('')
    for view in state['views']:
        label, instruction = panel_details(state, view)
        lines.append(f'{label}: {instruction}')
    lines.append('')
    lines.append('The assigned sheet structure, camera directions and crops are fixed. Garment-only clothing panels exclude every person, body, limb, skin surface and mannequin. Appearance instructions cannot change those constraints.')
    hands_visible = any(v in part_views(state, 'hands') for v in state['views'])
    if hands_visible and state['hand_state'] == 'bare':
        lines.append('Hand coverage override: all visible hands are bare skin, with no gloves. This takes precedence only for hand coverage; retain compatible hand shapes, materials, jewelry and other explicit hand details.')
    elif hands_visible and state['hand_state'] == 'gloved':
        lines.append('Hand coverage override: all visible hands wear gloves, consistently across all relevant studies. Keep referenced glove designs where available and retain compatible hand shapes, materials, jewelry and other explicit hand details.')
    elif hands_visible:
        lines.append('Follow the referenced hand coverage unless an explicit applicable part directive changes it. Do not automatically add gloves absent from the reference.')
    lines.append('Applicable literal part directives take precedence over dedicated part references. Named parts take precedence over other; back_clothing takes precedence over upper_clothing on rear clothing surfaces. A face-only reference takes precedence over a head reference for facial features; clothing_front or clothing_back takes precedence over a complete-outfit reference on its corresponding visible surfaces.')
    if len([r for r in extras if r['role'] != 'same_character']) > 1:
        if any(ref['source'] == 'reference_image_3' and ref['role'] != 'same_character' for ref in extras):
            lines.append('Dedicated references of the same role complement one another across angles; if their visible details conflict, the higher-numbered additional reference takes precedence for that role only.')
        else:
            lines.append('Two dedicated references of the same role complement one another across angles; if their visible details conflict, additional reference 2 takes precedence over additional reference 1 for that role only.')
    lines.append('Same-character references supplement additional angles and unseen details without overriding baseline identity or appearance. Preserve every unspecified detail from the baseline; infer unseen surfaces conservatively. New camera views and panel arrangements do not authorize appearance changes. Keep outfit asymmetries, hand coverage and barefoot or footwear state consistent without mirroring the character.')
    if style != 'none':
        lines.append('Change only rendering technique, consistently across all selected studies. ' + STYLE_PROMPTS[style] + ' Preserve identity, proportions, garment construction, accessories, colors and assigned crops.')
    if active:
        lines.append('')
        for part, text in active.items():
            eligible = ', '.join(panel_details(state, v)[0] for v in state['views'] if v in part_views(state, part))
            lines.append(f"{PART_RULES[part]['label']} ({eligible}): {MULTI_PART_SCOPES[part]} Literal appearance instruction:\n{text}")
    lines.extend(['', 'Render opaque finished artwork with consistent contrast and soft lighting. Keep every study inside its assigned region and leave the gaps empty. Add no unselected views, extra figures, captions or watermarks. Lettering explicitly requested in a part directive appears only on its named part.'])
    return '\n'.join(lines)


def compile_multi_state(state_json, *, max_resolution=DEFAULT_MAX_RESOLUTION,
                        use_layout_image=False, style='none', reference_presence=None, layout=None):
    """One pure preview/execution compiler, with actual or provisional presence."""
    if type(use_layout_image) is not bool:
        raise StateValidationError('use_layout_image must be a boolean.', 'invalid_type')
    if type(style) is not str or style not in STYLE_PROMPTS:
        raise StateValidationError('Unknown style ID.', 'unknown_style')
    presence = validate_reference_presence(reference_presence)
    state = parse_multi_state(state_json, max_resolution=max_resolution)
    layout = compute_multi_layout(state, max_resolution=max_resolution) if layout is None else layout
    width, height = layout['canvas']
    plan = build_reference_plan(
        True if presence['character_image'] else None,
        True if presence['reference_image_1'] else None,
        True if presence['reference_image_2'] else None,
        True if presence['reference_image_3'] else None,
        use_layout_image=use_layout_image, roles=state['reference_roles'])
    notices = [] if presence['character_image'] else ['missing_character']
    return {
        'state_json': state_json,
        'layout': layout, 'width': width, 'height': height,
        'prompt': compile_multi_prompt(state, layout, plan, use_layout_image=use_layout_image, style=style) if not notices else '',
        'reference_plan': list(plan.references), 'reference_numbering_provisional': True,
        'guide_artwork': body_artwork_placements(layout),
        'pixel_count': width * height, 'megapixels': width * height / 1_000_000,
        'max_resolution': max_resolution,
        'experimental': width * height > EXPERIMENTAL_PIXEL_THRESHOLD, 'notices': notices,
    }


def validate_reference_presence(value):
    names = ('character_image', *EXTRA_INPUTS)
    if value is None:
        return dict.fromkeys(names, False)
    if type(value) is not dict or set(value) - set(names):
        raise StateValidationError('reference_presence accepts image input names only.', 'invalid_request')
    if any(type(v) is not bool for v in value.values()):
        raise StateValidationError('Reference presence values must be booleans.', 'invalid_type')
    return {name: value.get(name, False) for name in names}

from . import output_plan as _outputs


def compile_output_plan(state_json, **options):
    """Compatibility import for callers of the original Batch Out compiler."""
    return _outputs.compile_output_plan(state_json, **options)
