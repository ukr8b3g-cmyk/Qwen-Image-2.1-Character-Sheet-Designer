"""Short single-view prompts with an explicit, executable reference plan."""
from .common.state import PART_RULES, serialize_state
from .compiler import STYLE_PROMPTS
from .multi_reference_compiler import (
    BODY_IDS, CLOTHING_IDS, PORTRAIT_IDS, DEFAULT_MULTI_STATE, StateValidationError, panel_details,
    parse_multi_state, part_views,
)
from .output_plan import compile_output_plan, preview_summary
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

NATURAL_PORTRAITS = {
    'face_front': 'Straight-on portrait with both eyes visible.',
    'face_left': 'Strict profile facing image-left, with one eye visible.',
    'face_right': 'Strict profile facing image-right, with one eye visible.',
    'face_3q_left': 'Three-quarter portrait turned 45 degrees toward image-left, with both eyes visible.',
    'face_3q_right': 'Three-quarter portrait turned 45 degrees toward image-right, with both eyes visible.',
    'face_back': 'Direct rear portrait showing only the back of the head and shoulders, with no face visible.',
}
NATURAL_BODY_DIRECTIONS = {
    'body_front': 'Face straight forward.',
    'body_left': 'Turn the entire body into a strict profile facing image-left.',
    'body_back': 'Face directly away from the viewer so the face is hidden.',
}

NATURAL_TURNAROUND_SLOTS = {
    'face_front': 'Top-left portrait frame',
    'face_left': 'Top-right portrait frame',
    'face_right': 'Middle-left portrait frame',
    'face_3q_left': 'Middle-right portrait frame',
    'face_3q_right': 'Bottom-left portrait frame',
    'face_back': 'Bottom-right portrait frame',
    'body_front': 'First tall frame in the middle block',
    'body_left': 'Second tall frame in the middle block',
    'body_back': 'Third tall frame in the middle block',
    'hands': 'Upper frame in the far-right column',
    'feet': 'Lower frame in the far-right column',
}


def _view_references(state, view, plan):
    presence = {entry['source']: True for entry in plan['sources'] if entry['role'] != 'layout'}
    selected, _missing = build_reference_plan({**state, 'views': [view]}, presence)
    numbers = {entry['source']: entry for entry in numbered_references(plan)}
    return [numbers[entry['source']] for entry in selected['sources']]


def _view_instruction(state, view):
    label, instruction = panel_details(state, view)
    if state.get('clothing_type') == 'none':
        if view in NATURAL_PORTRAITS:
            return label, NATURAL_PORTRAITS[view] + ' Include the whole head and crop at the upper chest.'
        if view in BODY_IDS:
            return label, (
                NATURAL_BODY_DIRECTIONS[view] + ' Show the complete silhouette. Match the stance, limb arrangement '
                'and proportions of the reference character, including any visible ears, tail and paws.'
            )
        if view == 'hands' and state['hand_state'] != 'gloved':
            return label, 'One isolated close-up of the complete left and right hands or forepaws, cropped at the wrists. No whole figure.'
        if view == 'feet' and state.get('footwear_state', 'reference') == 'reference':
            return label, 'One isolated close-up of the complete left and right feet or hind paws, with any footwear shown in the applicable reference. No whole figure.'
    clothing_choice = state.get('clothing_type') in ('pants', 'skirt_robe')
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


def _requested_view_instruction(state, view):
    label, default = _view_instruction(state, view)
    return label, state.get('view_prompts', {}).get(view, default)


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
                if state.get('clothing_type') == 'none':
                    lines.append(f'Use {tag} for the character design and visible natural markings.')
                    continue
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
    if state.get('clothing_type') in ('pants', 'skirt_robe') and view in (*BODY_IDS, *CLOTHING_IDS):
        lines.append('The selected lower-garment structure overrides conflicting reference structure only; preserve compatible clothing details.')
    if state.get('footwear_state', 'reference') != 'reference' and view in part_views(state, 'footwear'):
        lines.append('The selected footwear presence overrides conflicting reference footwear only; preserve compatible details and reference socks or tights.')
    return ' '.join(lines)


def uses_guided_natural_turnaround(state, layout, use_layout_image):
    return (use_layout_image and state.get('clothing_type') == 'none'
            and len(layout['panels']) == len(NATURAL_TURNAROUND_SLOTS)
            and layout.get('layout_version') != 'adaptive-1')


def compile_prompt(state, layout, plan, *, use_layout_image=False, style='none'):
    views = state['views']
    refs = numbered_references(plan)
    active = {part: text for part, text in state['part_prompts'].items()
              if any(v in part_views(state, part) for v in views)}
    single = len(views) == 1
    natural = state.get('clothing_type') == 'none'
    natural_turnaround = uses_guided_natural_turnaround(state, layout, use_layout_image)
    if single:
        label, instruction = _requested_view_instruction(state, views[0])
        lines = [f'Generate a single illustration: {label}.' + (f' {instruction}' if instruction else '')]
    else:
        lines = [f'Generate one character reference sheet with exactly {len(views)} views, each appearing once.']
        if not natural_turnaround:
            lines.append('Regions use normalized coordinates from 0 to 1, with the origin at the top-left: [left, top, width, height].')
    for ref in refs:
        tag, role = ref['tag'], ref['role']
        if role == 'layout':
            if natural_turnaround:
                lines.append(f'Use the eleven soft placement marks in {tag} as an invisible alignment guide. '
                             'Keep the exact position, size and spacing of each drawing. '
                             'The left block has portraits in three rows of two, the middle block has three tall full-body slots, '
                             'and the far-right column has two detail slots. Draw one view in each existing slot on pure white.')
            elif natural:
                lines.append(f'{tag} is a guide to panel positions only. Fill each requested region with finished artwork and leave white gaps between views.')
            else:
                lines.append(f'{tag} is only a layout guide. Keep its frames, camera directions and crops. Replace gray placeholders with finished artwork; do not copy their anatomy, colors or clothing.')
        elif role == 'character':
            lines.append(f'{tag}: baseline identity, proportions and rendering medium.')
        else:
            description = 'foot appearance' if role == 'footwear' else role
            role_text = ROLE_TEXT[role]
            if natural and role == 'same_character':
                role_text = 'Use as an additional angle of the same character; keep the requested camera and crop.'
            lines.append(f'{tag}: {description} reference. {role_text}')
    lines.append('References supply appearance only; use the requested camera, crop and arrangement. Ignore unrelated referenced parts and backgrounds.')
    if natural:
        lines.append('Keep the character unclothed. Preserve its natural body surface, markings, anatomy and proportions. Retain compatible accessories and follow the separate hand and footwear settings.')
    for index, panel in enumerate(layout['panels'], 1):
        view = panel['id']
        references = _view_reference_text(state, view, plan)
        if single:
            lines.append('Requested view: ' + references)
        elif natural_turnaround:
            _, instruction = _requested_view_instruction(state, view)
            if view not in state.get('view_prompts', {}):
                if view == 'face_left':
                    instruction = ('A strict 90-degree profile facing image-left, with only the near eye visible. '
                                   'Include the whole head and crop at the upper chest.')
                elif view == 'face_3q_left':
                    instruction = ('Directly below the top-right portrait, show a three-quarter view turned only about 25 degrees '
                                   'from straight on toward image-left. Keep the nose slightly left of center. '
                                   'Show two distinct eyes with both irises clearly visible on opposite sides of the nose. '
                                   'Show the entire head through the upper chest.')
                elif view == 'body_front':
                    instruction = ('Direct full-body front view with the camera centered. The face, shoulders, chest, hips '
                                   'and feet all face straight toward the viewer, with both sides equally visible. '
                                   'Keep the reference stance and show the entire silhouette.')
            lines.append(f'{NATURAL_TURNAROUND_SLOTS[view]}: {instruction} {references}')
        elif natural:
            label, instruction = _requested_view_instruction(state, view)
            lines.append(f'{label.capitalize()} in region {panel["rect"]}: {instruction} {references}')
        else:
            label, instruction = _requested_view_instruction(state, view)
            lines.append(f'{index}. {label}, region {panel["rect"]}: {instruction} {references}')
    rows = {}
    for panel in layout['panels']:
        if panel['id'] in BODY_IDS:
            row = (panel['rect'][1], panel['rect'][3]) if natural else panel['rect'][1]
            rows.setdefault(row, []).append(panel['id'])
    unedited = set(BODY_IDS) - state.get('view_prompts', {}).keys()
    if any(len(row) > 1 for row in rows.values()):
        if all(v in unedited for row in rows.values() for v in row):
            lines.append('Within each row of full-body figures, keep their height equal and align the soles. Keep every complete head and foot within its own region.')
        else:
            for row in rows.values():
                matched = [panel_details(state, view)[0] for view in row if view in unedited]
                if len(matched) > 1:
                    lines.append(f'Use matching scale and aligned ground contact for the {" and ".join(matched)} views.')
    hands_visible = any(v in part_views(state, 'hands') for v in views)
    clothing_views = [str(i) for i, v in enumerate(views, 1) if v in (*BODY_IDS, *CLOTHING_IDS)]
    footwear_views = [str(i) for i, v in enumerate(views, 1) if v in part_views(state, 'footwear')]
    clothing_type = state.get('clothing_type', 'reference')
    footwear_state = state.get('footwear_state', 'reference')
    clothing_override = bool(clothing_views) and clothing_type in ('pants', 'skirt_robe')
    footwear_override = bool(footwear_views) and footwear_state != 'reference'
    has_choices = clothing_override or footwear_override or (hands_visible and state['hand_state'] != 'reference')
    if hands_visible and state['hand_state'] == 'reference':
        lines.append('Preserve the assigned reference hand coverage and accessories; do not invent or remove coverage.')
    elif hands_visible:
        uncovered = 'uncovered, with the natural surface visible and no gloves' if natural else 'bare skin, no gloves'
        coverage = (uncovered if state['hand_state'] == 'bare' else
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
                     ' Keep the same resulting footwear or foot covering across visible views,'
                     + (' without revealing hidden feet.' if natural else ' without changing garment length or revealing hidden feet.'))
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
        priority = ('Selected part controls take precedence wherever explicitly specified.' if natural else
                    'Selected part controls take precedence only for lower-garment structure, hand coverage and footwear presence where specified.')
        lines.append(f'Plain white background, finished opaque artwork, consistent lighting. {priority}'
                     ' For compatible appearance details, follow explicit part text first, dedicated references next, then preserve unspecified baseline details.')
    else:
        lines.append('Plain white background, finished opaque artwork, consistent lighting. Follow explicit part text first, dedicated references next, then preserve unspecified baseline details.')
    if single:
        lines.append('Only the one requested view, centered and enlarged with a small white margin. No additional figures, alternative designs, contact sheets, captions or watermarks.')
    else:
        lines.append('Keep every requested view in its assigned region and leave gaps empty. No additional figures, unselected views, captions or watermarks.')
    if natural_turnaround:
        lines.append('The far-right column contains only the paired hands above the paired feet. '
                     'The middle block contains one front, one side and one rear drawing. '
                     'Use an uninterrupted pure white background behind and between all drawings. '
                     'Separate them with white space only. Erase the placement marks and omit borders, labels and numbers.')
    elif not use_layout_image or natural:
        lines.append('No panel borders.')
    if natural and not single and not natural_turnaround:
        lines.append('Use only white space to separate views. Keep every guide slot distinct, with one requested view in each. The sheet contains artwork only, with no labels or numbers.')
    return '\n'.join(lines)


def compile_output_plan_v12(state_json, *, strict=True, **options):
    state = parse_multi_state(state_json, max_resolution=options.get('max_resolution', 16384))
    plan = compile_output_plan(state_json, **options)
    return apply_reference_prompts(plan, state, strict=strict,
                                   reference_presence=options.get('reference_presence'),
                                   use_layout_image=options.get('use_layout_image', False), style=options.get('style', 'none'))


def apply_reference_prompts(plan, state, *, strict, reference_presence, use_layout_image, style):
    for item in plan['items']:
        selected = {**state, 'views': [p['id'] for p in item['layout']['panels']]}
        refs, missing = build_reference_plan(selected, reference_presence, use_layout_image=use_layout_image)
        if strict and missing:
            raise StateValidationError('Connect character_image or an applicable part reference for: ' + ', '.join(missing), 'missing_reference')
        item['reference_plan'] = numbered_references(refs)
        item['reference_plan_json'] = serialize_reference_plan(refs)
        item['notices'] = ['missing_reference:' + v for v in missing]
        item['prompt'] = '' if missing else compile_prompt(selected, item['layout'], refs, use_layout_image=use_layout_image, style=style)
    return plan


def compile_output_preview_v12(state_json, **options):
    plan = compile_output_plan_v12(state_json, strict=False, **options)
    summary = preview_summary(state_json, plan, compile_output_plan_v12, strict=False, **options)
    return {**{k: v for k, v in summary.items() if k not in ('index', 'view_id', 'filename_suffix')}, 'batch_plan': plan}
