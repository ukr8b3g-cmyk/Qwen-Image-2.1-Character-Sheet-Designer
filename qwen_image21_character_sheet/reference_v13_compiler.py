"""Saved view edits and effective output views for the current Designer."""
from functools import partial

from .common.state import DEFAULT_MAX_RESOLUTION, PRESETS, StateValidationError, decode_json, serialize_state
from .multi_guide_geometry import body_artwork_placements, panel_bounds
from .multi_reference_compiler import BODY_IDS, CLOTHING_IDS, MULTI_VIEW_IDS, parse_multi_state, validate_reference_presence
from .output_plan import compile_output_plan, preview_summary
from .reference_v12_compiler import _view_instruction, apply_reference_prompts, uses_guided_natural_turnaround
from .reference_plan import EXTRA_INPUTS

CLOTHING_ROLES = ('clothing', 'clothing_front', 'clothing_back')
CLOTHING_PARTS = ('upper_clothing', 'back_clothing', 'lower_body')
VIEW_PROMPT_MAX_UNITS = 2000


def parse_v13_state(raw, *, max_resolution=DEFAULT_MAX_RESOLUTION):
    data = decode_json(raw)
    if not isinstance(data, dict) or data.get('schema_version') != 3:
        return parse_multi_state(raw, max_resolution=max_resolution)
    natural = data.get('clothing_type') == 'none'
    overrides = {}
    if 'view_prompts' in data:
        overrides = data.pop('view_prompts')
        if not isinstance(overrides, dict) or any(view not in MULTI_VIEW_IDS for view in overrides):
            raise StateValidationError('View prompts must be an object with known view IDs.', 'invalid_view_prompts')
        for text in overrides.values():
            if not isinstance(text, str):
                raise StateValidationError('View prompts must be strings.', 'invalid_view_prompts')
            if len(text.encode('utf-16-le')) // 2 > VIEW_PROMPT_MAX_UNITS:
                raise StateValidationError('View prompts may contain at most 2000 UTF-16 code units.', 'view_prompt_too_long')
    if natural:
        data['clothing_type'] = 'reference'
    state = parse_multi_state(serialize_state(data), max_resolution=max_resolution)
    if overrides:
        state['view_prompts'] = {view: overrides[view] for view in MULTI_VIEW_IDS if view in overrides}
    if natural:
        if all(view in CLOTHING_IDS for view in state['views']):
            raise StateValidationError('Select at least one non-clothing view when using No clothing.', 'no_effective_views')
        state['clothing_type'] = 'none'
    return state


def effective_state(state):
    if state.get('clothing_type') != 'none':
        return state
    return {**state, 'views': [view for view in state['views'] if view not in CLOTHING_IDS],
            'part_prompts': {part: text for part, text in state['part_prompts'].items() if part not in CLOTHING_PARTS}}


def layout_state_json(state):
    """Only the existing geometry fields are needed by packing and assembly."""
    layout_state = {key: value for key, value in state.items() if key != 'view_prompts'}
    if layout_state.get('clothing_type') == 'none':
        layout_state['clothing_type'] = 'reference'
    return serialize_state(layout_state)


def _widen_standard_body_panels(layout):
    width = layout['canvas'][0]
    # Standard five has two portrait columns and three equal body columns.
    panels = layout['panels']
    left, _, right, _ = panel_bounds(layout, panels[2])
    extra = round((right - left) * 3 / 56)
    face_loss = extra * 3 // 2
    deltas = (-face_loss, face_loss - extra * 3, extra, extra, extra)
    offset = 0
    for panel, delta in zip(panels, deltas, strict=True):
        left, top, span, height = panel['rect']
        panel['rect'] = [round(left + offset / width, 6), top, round(span + delta / width, 6), height]
        offset += delta


def _compile_plan(state, raw, *, strict, max_resolution=DEFAULT_MAX_RESOLUTION, reference_presence=None,
                  use_layout_image=False, style='none', batch_out=False):
    natural = state.get('clothing_type') == 'none'
    if natural:
        presence = validate_reference_presence(reference_presence)
        conflicts = [slot for slot in EXTRA_INPUTS if presence[slot] and state['reference_roles'][slot] in CLOTHING_ROLES]
        if conflicts:
            raise StateValidationError('No clothing conflicts with a connected outfit reference: ' + ', '.join(conflicts),
                                       'clothing_reference_conflict')
    plan = compile_output_plan(raw, max_resolution=max_resolution, use_layout_image=use_layout_image, style=style,
                               reference_presence=reference_presence, batch_out=batch_out)
    widen = use_layout_image and not batch_out and state['size']['mode'] == 'auto' and state['views'] == list(PRESETS['five'])
    for item in plan['items']:
        layout = item['layout']
        if widen and layout.get('layout_version') != 'adaptive-1':
            _widen_standard_body_panels(layout)
            item['guide_artwork'] = body_artwork_placements(layout)
        if natural:
            pale_guide = uses_guided_natural_turnaround(state, layout, use_layout_image)
            for panel in layout['panels']:
                panel['blank'] = True
                if pale_guide:
                    panel['guide_fill'] = '#e8e8e8'
            item['guide_artwork'] = {}
        for panel in layout['panels']:
            view = panel['id']
            if natural or view in state.get('view_prompts', {}):
                label, default = _view_instruction(state, view)
                panel.update(view=label, content=state.get('view_prompts', {}).get(view, default))
    return apply_reference_prompts(plan, state, strict=strict, reference_presence=reference_presence,
                                   use_layout_image=use_layout_image, style=style)


def compile_output_plan_v13(state, *, strict=True, **options):
    return _compile_plan(state, layout_state_json(state), strict=strict, **options)


def compile_output_preview_v13(saved, raw, **options):
    state = effective_state(saved)
    layout_raw = layout_state_json(state)
    compile_plan = partial(_compile_plan, state, strict=False)
    plan = compile_plan(layout_raw, **options)
    summary = preview_summary(layout_raw, plan, compile_plan, **options)
    return {**{key: value for key, value in summary.items() if key not in ('index', 'view_id', 'filename_suffix')},
            'state_json': raw, 'batch_plan': plan,
            'default_view_prompts': {view: _view_instruction(state, view)[1] for view in MULTI_VIEW_IDS}}
