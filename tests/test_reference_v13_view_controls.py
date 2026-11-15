import json
import re

import pytest
import torch

from qwen_image21_character_sheet.multi_guide_geometry import panel_bounds
from qwen_image21_character_sheet.multi_layout_image import render_layout_image
from qwen_image21_character_sheet.multi_reference_compiler import MULTI_VIEW_IDS
from qwen_image21_character_sheet.reference_v12_compiler import DEFAULT_V12_STATE_JSON, compile_output_preview_v12
from qwen_image21_character_sheet.reference_v12_node import QwenImage21CharacterSheetDesignerReferenceV12
from qwen_image21_character_sheet.reference_v13_node import QwenImage21CharacterSheetDesignerReferenceV13
from qwen_image21_character_sheet.reference_v13_preview import compile_preview_request


@pytest.fixture(autouse=True)
def use_test_resolution_limit(monkeypatch):
    for version in ('v12', 'v13'):
        monkeypatch.setattr(f'qwen_image21_character_sheet.reference_{version}_node.runtime_max_resolution', lambda: 16384)


def preview(state, *, guide=False, batch=False, **references):
    payload = dict(state_json=json.dumps(state), use_layout_image=guide, batch_out=batch,
                   reference_presence={'character_image': True, **references})
    return compile_preview_request(json.dumps(payload).encode(), max_resolution=16384)


@pytest.mark.parametrize('guide', [False, True])
@pytest.mark.parametrize('batch', [False, True])
def test_natural_surface_keeps_saved_selection_and_filters_every_output(guide, batch):
    state = json.loads(DEFAULT_V12_STATE_JSON)
    state.update(views=list(MULTI_VIEW_IDS), clothing_type='none', hand_state='gloved', footwear_state='unshod',
                 view_prompts={'clothing_front': 'Retain the gold embroidery.', 'hands': 'Show the left and right gloved paws.'},
                 part_prompts={'upper_clothing': 'A red leather jacket.', 'footwear': 'Black socks.'})
    state['size'].update(mode='manual', manual_width=640, manual_height=256)
    result = preview(state, guide=guide, batch=batch)
    saved = json.loads(result['state_json'])
    assert saved == state
    views = [v for v in state['views'] if not v.startswith('clothing_')]
    assert [p['id'] for p in result['layout']['panels']] == views
    assert [p['view_id'] for p in result['sheet_plan']['views']] == views
    assert all(p['blank'] for p in result['layout']['panels'])
    assert result['guide_artwork'] == {}
    outputs = QwenImage21CharacterSheetDesignerReferenceV13().compile(
        result['state_json'], character_image=torch.zeros((1, 4, 4, 3)), use_layout_image=guide, batch_out=batch)
    assert len(outputs[0]) == (11 if batch else 1)
    assert outputs[0] == [i['prompt'] for i in result['batch_plan']['items']]
    assert outputs[1:3] == ([640] * len(outputs[0]), [256] * len(outputs[0]))
    assert json.loads(outputs[6]) == result['sheet_plan']
    assert all(json.loads(plan)['sources'][0]['role'] == ('layout' if guide else 'character') for plan in outputs[5])
    if batch:
        assert [json.loads(row)['view_id'] for row in outputs[7]] == views
        assert [json.loads(plan)['view_ids'][0] for plan in outputs[5]] == views
    else:
        assert json.loads(outputs[5][0])['view_ids'] == views
    if guide:
        assert all(set(img.unique().tolist()) == {0.0, 1.0} for img in outputs[3])
    else:
        assert all(img is None for img in outputs[3])
    prompt = '\n'.join(outputs[0])
    for included in ('Keep the character unclothed', 'Show the left and right gloved paws.', 'Black socks.'):
        assert included in prompt
    for suppressed in ('Keep the baseline outfit', 'A red leather jacket.', 'Retain the gold embroidery.'):
        assert suppressed not in prompt
    saved['clothing_type'] = 'reference'
    restored = preview(saved, guide=guide)
    assert [p['id'] for p in restored['layout']['panels']] == state['views']
    assert 'Retain the gold embroidery.' in restored['prompt']


def test_clothing_conflicts_and_legacy_input_are_reported():
    state = json.loads(DEFAULT_V12_STATE_JSON)
    state.update(clothing_type='none')
    state['reference_roles']['reference_image_2'] = 'clothing_back'
    assert preview(state)['layout']['panels']
    with pytest.raises(ValueError, match='reference_image_2'):
        preview(state, reference_image_2=True)
    state['views'] = ['clothing_front', 'clothing_back']
    with pytest.raises(ValueError, match='at least one non-clothing'):
        preview(state)
    assert QwenImage21CharacterSheetDesignerReferenceV12.VALIDATE_INPUTS(json.dumps(state)) is not True


def test_side_override_and_blank_are_used_only_for_their_views():
    state = json.loads(DEFAULT_V12_STATE_JSON)
    state['view_prompts'] = {'body_left': 'Show the character sitting in a strict left profile.', 'face_front': ''}
    result = preview(state, guide=True)
    side = next(line for line in result['prompt'].splitlines() if 'full-body anatomical left profile, region' in line)
    assert 'sitting' in side and 'neutral standing' not in side
    assert result['prompt'].count('neutral standing') == 2
    assert 'Use matching scale and aligned ground contact for the full-body front and full-body back views.' in result['prompt']
    assert 'A front-facing bust' not in result['prompt']
    assert json.loads(result['state_json'])['view_prompts']['face_front'] == ''
    assert 'A front-facing bust' in result['default_view_prompts']['face_front']
    assert QwenImage21CharacterSheetDesignerReferenceV12.VALIDATE_INPUTS(json.dumps(state)) is not True


def test_guided_natural_turnaround_uses_the_guide_positions_without_panel_numbers():
    state = json.loads(DEFAULT_V12_STATE_JSON)
    state.update(views=list(MULTI_VIEW_IDS), clothing_type='none')
    result = preview(state, guide=True)
    assert len(result['layout']['panels']) == 11
    assert 'three rows of two' in result['prompt']
    prompt_lines = result['prompt'].splitlines()
    profile = next(line for line in prompt_lines if line.startswith('Top-right portrait frame:'))
    oblique = next(line for line in prompt_lines if line.startswith('Middle-right portrait frame:'))
    assert prompt_lines.index(profile) < prompt_lines.index(oblique)
    assert '90-degree profile facing image-left' in profile and 'only the near eye visible' in profile
    assert 'three-quarter view' in oblique and 'toward image-left' in oblique
    assert 'both irises clearly visible' in oblique
    assert 'Directly below the top-right portrait' in oblique
    assert 'Bottom-right portrait frame: Direct rear portrait' in result['prompt']
    assert 'First tall frame in the middle block: Direct full-body front view with the camera centered' in result['prompt']
    assert 'Second tall frame in the middle block: Turn the entire body into a strict profile' in result['prompt']
    assert 'Upper frame in the far-right column: One isolated close-up of the complete left and right hands' in result['prompt']
    assert not re.search(r'^\d+\.', result['prompt'], re.MULTILINE)
    guide = render_layout_image(result['layout'])
    red, green, blue = guide.getextrema()
    assert red == green == blue and 230 <= red[0] < red[1] == 255
    assert guide.getpixel((0, 0)) == (255, 255, 255)
    for panel in result['layout']['panels']:
        left, top, right, bottom = panel_bounds(result['layout'], panel)
        middle = (top + bottom) // 2
        assert guide.getpixel((left, middle)) == (255, 255, 255)
        assert guide.getpixel(((left + right) // 2, middle))[0] < 255
    state['view_prompts'] = {
        'face_left': 'Show a close-up with one closed eye.',
        'face_3q_left': 'Show a left three-quarter portrait with a wink.',
        'body_front': 'Tilt the shoulders as the character greets the viewer.',
    }
    edited = preview(state, guide=True)
    profile = next(line for line in edited['prompt'].splitlines() if line.startswith('Top-right portrait frame:'))
    assert 'one closed eye' in profile and '90-degree' not in profile
    left = next(line for line in edited['prompt'].splitlines() if line.startswith('Middle-right portrait frame:'))
    assert 'with a wink' in left and 'both irises' not in left
    front = next(line for line in edited['prompt'].splitlines() if line.startswith('First tall frame in the middle block:'))
    assert 'Tilt the shoulders' in front and 'camera centered' not in front


def test_guided_standard_width_redistribution_keeps_canvas_and_gaps():
    state = json.loads(DEFAULT_V12_STATE_JSON)
    before = compile_output_preview_v12(DEFAULT_V12_STATE_JSON, use_layout_image=True)
    after = preview(state, guide=True)
    assert before['layout']['canvas'] == after['layout']['canvas']
    old = [panel_bounds(before['layout'], p) for p in before['layout']['panels']]
    new = [panel_bounds(after['layout'], p) for p in after['layout']['panels']]
    assert [b[2] - b[0] for b in old] == [560, 560, 448, 448, 448]
    assert [b[2] - b[0] for b in new] == [524, 524, 472, 472, 472]
    assert [(b[1], b[3]) for b in old] == [(b[1], b[3]) for b in new]
    assert [b[0] - a[2] for a, b in zip(old, old[1:])] == [b[0] - a[2] for a, b in zip(new, new[1:])]
    assert preview(state)['layout'] == before['layout']
