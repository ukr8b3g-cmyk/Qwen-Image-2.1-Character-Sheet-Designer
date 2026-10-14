"""Short single-view prompts with an explicit, executable reference plan."""
from .common.state import PART_RULES, serialize_state
from .compiler import STYLE_PROMPTS
from .multi_reference_compiler import (
    BODY_IDS, CLOTHING_IDS, PORTRAIT_IDS, DEFAULT_MULTI_STATE, StateValidationError, panel_details,
    parse_multi_state, part_views,
)
from .output_plan import compile_output_plan
from .reference_v12_plan import build_reference_plan, numbered_references, serialize_reference_plan

DEFAULT_V12_STATE_JSON = serialize_state({**DEFAULT_MULTI_STATE, 'clothing_type': 'reference', 'footwear_state': 'reference'})

ROLE_TEXT = {
    'same_character': 'Use as an additional angle of the same person; keep the requested camera and crop.',
    'face': 'Use its facial features and eye color only; keep the baseline hairstyle and the requested camera.',
    'head': 'Use its head, hair and headwear; a dedicated face reference controls the facial features.',
    'clothing': 'Preserve its garment construction, connected silhouette, layers, openings, hems, colors and patterns.',
    'clothing_front': 'Use the front clothing surfaces only; they take priority over a complete-outfit reference on the front.',
    'clothing_back': 'Use the rear clothing surfaces only where visible; never move rear decorations to the front or turn the subject to reveal them.',
    'hands': 'Use only the visible hand details and accessories.',
    'footwear': 'Match the visible pair: its silhouette, material, coverage and existing openings. Keep covered surfaces covered and uncovered surfaces uncovered; explicit footwear text overrides conflicting details.',
}


def _view_references(state, view, plan):
    presence = {entry['source']: True for entry in plan['sources'] if entry['role'] != 'layout'}
    selected, _missing = build_reference_plan({**state, 'views': [view]}, presence)
    numbers = {entry['source']: entry for entry in numbered_references(plan)}
    return [numbers[entry['source']] for entry in selected['sources']]


def _view_instruction(state, view):
    label, instruction = panel_details(state, view)
    clothing_choice = state.get('clothing_type', 'reference') != 'reference'
    if view in CLOTHING_IDS and (clothing_choice or state['clothing_mode'] == 'worn'):
        side = 'front-facing' if view == 'clothing_front' else 'direct rear'
        if state['clothing_mode'] == 'garment':
            instruction = (f'An isolated {side} view of the same outfit\'s garments ONLY.'
                           ' No head, neck, arms, hands, legs, feet, torso, skin, person, mannequin or body inside the garments.'
                           ' Keep complete garments with empty sleeves and openings, using the selected lower-garment structure.'
                           ' Preserve compatible upper clothing, layers, hems, colors and patterns.')
        else:
            instruction = (f'A {side} cropped view of the same character actually wearing the complete outfit.'
                           ' Frame the wearer from the base of the neck to the lowest garment edge, with the head outside the frame.'
                           ' Keep the human body inside the clothing and the arms and hands where naturally visible; do not display empty clothes or a floating outfit.'
                           ' Retain compatible upper clothing, layers, hems, colors and patterns.')
            if clothing_choice:
                instruction += ' Use the selected lower-garment structure.'
    if view in PORTRAIT_IDS:
        instruction += ' Stop the frame at the upper chest, even when the outfit reference contains a complete garment.'
    elif view in CLOTHING_IDS and state['clothing_mode'] == 'worn':
        instruction += (' The same character is wearing the referenced outfit; retain the wearer\'s body and naturally visible limbs.'
                        ' Place the head outside the frame. Keep the complete clothing from neckline to its lowest garment edge.')
        if clothing_choice or state['hand_state'] != 'reference':
            instruction += ' Preserve referenced clothing coverage and construction except for the selected lower-garment structure; apply a hand-coverage choice only to naturally visible hands.'
        else:
            instruction += ' Preserve the referenced coverage and connected garment shape; do not add or remove coverage.'
    elif view == 'hands':
        if state['hand_state'] == 'gloved':
            instruction = ('One isolated close-up of two hands wearing actual gloves, cropped at the wrists.'
                           ' Each hand has a glove physically worn over it; replace any bare hands in the reference with gloves.'
                           ' Follow the glove type and finger openings supplied by an applicable hand directive or glove reference.'
                           ' When neither supplies a glove type, use full-finger gloves covering the fingers and palms.'
                           ' No head, torso or whole figure.')
        instruction += ' Exactly two hands: one left and one right, shown once each.'
    elif view == 'feet':
        if state.get('footwear_state', 'reference') == 'unshod':
            instruction = ('One isolated close-up of exactly one left and one right complete foot, shown once each.'
                           ' No shoes or boots. Preserve referenced bare feet or compatible socks and tights; do not invent socks.'
                           ' No head, torso, whole figure or collection of alternative designs.')
        elif state.get('footwear_state', 'reference') == 'shod':
            instruction = ('One isolated close-up of a complete matching pair of actual footwear, one left and one right, shown once each.'
                           ' Match the referenced or explicitly requested silhouette, material, coverage, construction and openings.'
                           ' Reproduce the enclosing surfaces as continuous material; show skin only through existing openings.'
                           ' Keep the complete pair within the frame, with only the lower-leg extent needed for it.'
                           ' No head, torso, whole figure or collection of alternative designs.')
        else:
            instruction = ('One isolated close-up reproducing the complete matching pair shown in the applicable reference, one left and one right, shown once each.'
                           ' Unless applicable footwear text changes it, match its silhouette, material, coverage, construction and openings.'
                           ' Reproduce enclosing surfaces as continuous material and uncovered surfaces as shown; add no openings or coverings.'
                           ' Keep footwear presence consistent across the pair; preserve left-right differences only when the reference itself shows them.'
                           ' Do not infer or invent footwear from the outfit.'
                           ' Show the complete pair with only the lower-leg extent needed for it.'
                           ' No head, torso, whole figure or collection of alternative designs.')
    return label, instruction


def _view_reference_text(state, view, plan):
    refs = _view_references(state, view, plan)
    lines = []
    active = {part for part in state['part_prompts'] if view in part_views(state, part)}
    outfit_refs = [ref for ref in refs if ref['role'] in ('clothing', 'clothing_front', 'clothing_back')]
    for ref in refs:
        tag, role = ref['tag'], ref['role']
        if role == 'character':
            subject = view in (*PORTRAIT_IDS, *BODY_IDS) or (view in CLOTHING_IDS and state['clothing_mode'] == 'worn')
            if subject:
                lines.append(f'Use {tag} for the visible baseline identity, proportions and rendering medium; preserve unspecified visible details.')
                if outfit_refs:
                    lines.append(f'Keep clothing from {tag} only on visible surfaces with no assigned clothing reference or named-part edit; ignore conflicting baseline clothing on assigned surfaces.')
                elif active & {'upper_clothing', 'back_clothing', 'lower_body'}:
                    lines.append(f'Keep baseline clothing from {tag} outside the visible named-part edits below.')
                else:
                    lines.append(f'Keep the baseline outfit from {tag}, except for applicable explicit part instructions.')
            else:
                lines.append(f'Use {tag} only for this requested detail; omit the person and unrelated parts.')
        elif role in ('clothing', 'clothing_front', 'clothing_back'):
            surfaces = 'the visible neckline, shoulders and upper-chest garment surfaces only' if view in PORTRAIT_IDS else 'the visible clothing surfaces within this crop'
            side = 'front surfaces only' if role == 'clothing_front' else 'rear surfaces only' if role == 'clothing_back' else 'the referenced garment design'
            lines.append(f'Clothing: use {tag} for {side}, on {surfaces}; replace conflicting baseline details there without expanding the requested crop.')
        else:
            description = 'foot appearance' if role == 'footwear' else role
            lines.append(f'Use {tag} for {description} details only within this view\'s visible crop.')
    if state.get('clothing_type', 'reference') != 'reference' and view in (*BODY_IDS, *CLOTHING_IDS):
        lines.append('The selected lower-garment structure overrides conflicting reference structure only; preserve compatible clothing details.')
    if state.get('footwear_state', 'reference') != 'reference' and view in part_views(state, 'footwear'):
        lines.append('The selected footwear presence overrides conflicting reference footwear only; preserve compatible details and reference socks or tights.')
    return ' '.join(lines)


def compile_prompt(state, layout, plan, *, use_layout_image=False, style='none'):
    views = state['views']
    refs = numbered_references(plan)
    active = {part: text for part, text in state['part_prompts'].items()
              if any(v in part_views(state, part) for v in views)}
    single = len(views) == 1
    if single:
        label, instruction = _view_instruction(state, views[0])
        lines = [f'Generate a single illustration: {label}. {instruction}']
    else:
        lines = [f'Generate one character reference sheet with exactly {len(views)} views, each appearing once.']
        lines.append('Regions use normalized coordinates from 0 to 1, with the origin at the top-left: [left, top, width, height].')
    for ref in refs:
        tag, role = ref['tag'], ref['role']
        if role == 'layout':
            lines.append(f'{tag} is only a layout guide. Keep its frames, camera directions and crops. Replace gray placeholders with finished artwork; do not copy their anatomy, colors or clothing.')
        elif role == 'character':
            lines.append(f'{tag}: baseline identity, proportions and rendering medium.')
        else:
            description = 'foot appearance' if role == 'footwear' else role
            lines.append(f'{tag}: {description} reference. {ROLE_TEXT[role]}')
    lines.append('References supply appearance only; use the requested camera, crop and arrangement. Ignore unrelated referenced parts and backgrounds.')
    for index, panel in enumerate(layout['panels'], 1):
        view = panel['id']
        references = _view_reference_text(state, view, plan)
        if single:
            lines.append('Requested view: ' + references)
        else:
            label, instruction = _view_instruction(state, view)
            lines.append(f'{index}. {label}, region {panel["rect"]}: {instruction} {references}')
    rows = {}
    for panel in layout['panels']:
        if panel['id'] in BODY_IDS:
            rows.setdefault(panel['rect'][1], []).append(panel['id'])
    if any(len(row) > 1 for row in rows.values()):
        lines.append('Within each row of full-body figures, keep their height equal and align the soles. Keep every complete head and foot within its own region.')
    hands_visible = any(v in part_views(state, 'hands') for v in views)
    clothing_views = [str(i) for i, v in enumerate(views, 1) if v in (*BODY_IDS, *CLOTHING_IDS)]
    footwear_views = [str(i) for i, v in enumerate(views, 1) if v in part_views(state, 'footwear')]
    clothing_type = state.get('clothing_type', 'reference')
    footwear_state = state.get('footwear_state', 'reference')
    clothing_override = bool(clothing_views) and clothing_type != 'reference'
    footwear_override = bool(footwear_views) and footwear_state != 'reference'
    has_choices = clothing_override or footwear_override or (hands_visible and state['hand_state'] != 'reference')
    if hands_visible and state['hand_state'] == 'reference':
        lines.append('Preserve the assigned reference hand coverage and accessories; do not invent or remove coverage.')
    elif hands_visible:
        coverage = ('bare skin, no gloves' if state['hand_state'] == 'bare' else
                    'gloved, wearing actual gloves over the hands; replace reference bare hands with gloves.'
                    ' Follow applicable glove details and finger openings; otherwise use full-finger gloves with covered fingers and palms')
        eligible = ', '.join(str(i) for i, v in enumerate(views, 1) if v in part_views(state, 'hands'))
        lines.append(f'Hand coverage override in view(s) {eligible}: visible hands are {coverage}; retain compatible accessories and explicit hand details.')
    if clothing_override:
        structure = ('pants with separate sections for each leg' if clothing_type == 'pants' else
                     'skirt or robe construction with one continuous hem rather than separate leg openings')
        lines.append(f'Lower clothing structure override in view(s) {", ".join(clothing_views)}: {structure}.'
                     ' Preserve whether the compatible outfit is separate pieces or one connected garment, its upper clothing, layers, length, colors and materials.'
                     ' This selected structure takes precedence over conflicting reference structure or part text; do not change the camera or crop.')
    if footwear_override:
        coverage = ('feet wear actual footwear;'
                    ' preserve its referenced kind and design, coverage, construction and existing openings;'
                    ' keep enclosing surfaces continuous, showing skin only through existing openings;'
                    ' choose an outfit-appropriate kind only when no reference shows it'
                    if footwear_state == 'shod' else
                    'no shoes or boots; keep referenced bare feet, socks or tights, without inventing socks')
        lines.append(f'Footwear presence override in view(s) {", ".join(footwear_views)}: {coverage}.'
                     ' This selected presence takes precedence over conflicting footwear or part text only for footwear presence; preserve compatible appearance details.'
                     ' Keep the same resulting footwear or foot covering across visible views, without changing garment length or revealing hidden feet.')
    for part, text in active.items():
        eligible = ', '.join(str(i) for i, v in enumerate(views, 1) if v in part_views(state, part))
        priority = 'Highest priority compatible appearance details' if has_choices else 'Highest priority'
        lines.append(f'{priority}, {PART_RULES[part]["label"]} in view(s) {eligible}; apply only to visible named parts, preserving the requested camera and crop:\n{text}')
    if 'back_clothing' in active and 'upper_clothing' in active:
        lines.append('The back clothing directive takes precedence on rear surfaces.')
    if 'other' in active and len(active) > 1:
        lines.append('Named part directives take precedence over the other directive.')
    if style != 'none':
        lines.append('Rendering technique only: ' + STYLE_PROMPTS[style])
    if has_choices:
        lines.append('Plain white background, finished opaque artwork, consistent lighting.'
                     ' Selected part controls take precedence only for lower-garment structure, hand coverage and footwear presence where specified.'
                     ' For compatible appearance details, follow explicit part text first, dedicated references next, then preserve unspecified baseline details.')
    else:
        lines.append('Plain white background, finished opaque artwork, consistent lighting. Follow explicit part text first, dedicated references next, then preserve unspecified baseline details.')
    if single:
        lines.append('Only the one requested view, centered and enlarged with a small white margin. No additional figures, alternative designs, contact sheets, captions or watermarks.')
    else:
        lines.append('Keep every requested view in its assigned region and leave gaps empty. No additional figures, unselected views, captions or watermarks.')
    if not use_layout_image:
        lines.append('No panel borders.')
    return '\n'.join(lines)


def compile_output_plan_v12(state_json, *, strict=True, **options):
    state = parse_multi_state(state_json, max_resolution=options.get('max_resolution', 16384))
    plan = compile_output_plan(state_json, **options)
    for item in plan['items']:
        selected = {**state, 'views': [p['id'] for p in item['layout']['panels']]}
        refs, missing = build_reference_plan(selected, options.get('reference_presence'), use_layout_image=options.get('use_layout_image', False))
        if strict and missing:
            raise StateValidationError('Connect character_image or an applicable part reference for: ' + ', '.join(missing), 'missing_reference')
        item['reference_plan'] = numbered_references(refs)
        item['reference_plan_json'] = serialize_reference_plan(refs)
        item['notices'] = ['missing_reference:' + v for v in missing]
        item['prompt'] = '' if missing else compile_prompt(selected, item['layout'], refs,
                                                          use_layout_image=options.get('use_layout_image', False), style=options.get('style', 'none'))
    return plan


def compile_output_preview_v12(state_json, **options):
    plan = compile_output_plan_v12(state_json, strict=False, **options)
    summary = plan['items'][0] if not plan['enabled'] else compile_output_plan_v12(
        state_json, strict=False, **{**options, 'batch_out': False})['items'][0]
    return {**{k: v for k, v in summary.items() if k not in ('index', 'view_id', 'filename_suffix')}, 'batch_plan': plan}
