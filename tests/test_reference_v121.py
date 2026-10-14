"""Mixed-view acceptance and preservation of the V1.2 execution contract."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from qwen_image21_character_sheet.multi_reference_compiler import DEFAULT_MULTI_STATE, MULTI_VIEW_IDS
from qwen_image21_character_sheet.reference_v12_compiler import (
    _view_instruction, _view_references, _view_reference_text, compile_output_plan_v12,
)
from qwen_image21_character_sheet.reference_v12_plan import build_reference_plan
from tests.test_reference_v12 import ALLOWED

ALL_PRESENT = dict.fromkeys(('character_image', 'reference_image_1', 'reference_image_2', 'reference_image_3'), True)


def state(views, *, roles=None, parts=None, mode='auto', clothing_mode='worn'):
    value = deepcopy(DEFAULT_MULTI_STATE)
    value['views'] = list(views)
    value['reference_roles'].update(roles or {})
    value['part_prompts'] = parts or {}
    value['clothing_mode'] = clothing_mode
    value['size'].update(mode=mode, manual_width=1536, manual_height=864)
    return value


def output(value, **options):
    return compile_output_plan_v12(json.dumps(value), reference_presence=ALL_PRESENT, **options)


def test_rear_only_reference_keeps_front_baseline_in_mixed_sheet():
    value = state(['body_front', 'body_back'], roles={'reference_image_3': 'clothing_back'})
    plan, missing = build_reference_plan(value, ALL_PRESENT)
    assert not missing
    front = _view_reference_text(value, 'body_front', plan)
    rear = _view_reference_text(value, 'body_back', plan)
    assert 'Keep the baseline outfit' in front
    assert 'rear surfaces only' not in front
    assert 'rear surfaces only' in rear
    assert 'Keep the baseline outfit' not in rear


def test_chest_crop_and_clothing_scope_do_not_depend_on_other_selections():
    roles = {'reference_image_3': 'clothing'}
    for view in ('face_front', 'face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'face_back'):
        single = state([view], roles=roles)
        mixed = state([view, 'body_front', 'body_back'], roles=roles)
        one, _ = build_reference_plan(single, ALL_PRESENT)
        many, _ = build_reference_plan(mixed, ALL_PRESENT)
        assert _view_instruction(single, view) == _view_instruction(mixed, view)
        for value, plan in ((single, one), (mixed, many)):
            text = _view_reference_text(value, view, plan)
            assert 'upper-chest garment surfaces only' in text
            assert 'without expanding the requested crop' in text


def test_named_part_edit_preserves_unassigned_clothing_and_literal_once():
    literal = '  襟の縁だけを変更\nその他の形状は維持  '
    value = state(['face_front', 'body_front', 'body_back'], parts={'upper_clothing': literal})
    item = output(value)['items'][0]
    assert item['prompt'].count(literal) == 1
    assert 'in view(s) 1, 2, 3' in item['prompt']
    assert 'outside the visible named-part edits' in item['prompt']
    assert 'Replace the baseline outfit' not in item['prompt']


def test_supplemental_person_does_not_apply_to_hand_foot_or_garment_details():
    value = state(['face_front', 'hands', 'feet', 'clothing_front'], clothing_mode='garment')
    plan, _ = build_reference_plan(value, ALL_PRESENT)
    for view in ('hands', 'feet', 'clothing_front'):
        assert all(r['role'] != 'same_character' for r in _view_references(value, view, plan))
    assert any(r['role'] == 'same_character' for r in _view_references(value, 'face_front', plan))


def test_worn_coverage_and_detail_counts_remain_explicit_in_sheet():
    value = state(['clothing_front', 'hands', 'feet'])
    item = output(value)['items'][0]
    assert 'The same character is wearing' in item['prompt']
    assert 'do not add or remove coverage' in item['prompt']
    assert 'Exactly two hands: one left and one right' in item['prompt']
    assert 'complete matching pair shown in the applicable reference, one left and one right, shown once each' in item['prompt']
    assert 'coverage, construction and openings' in item['prompt']
    assert 'normalized coordinates from 0 to 1' in item['prompt']
    garment = output(state(['clothing_front'], clothing_mode='garment'))['items'][0]['prompt']
    assert 'The same character is wearing' not in garment
    assert 'No head, neck' in garment


def test_all_8191_selections_use_visible_sources_and_global_image_numbers():
    roles = {'reference_image_1': 'clothing_back', 'reference_image_2': 'same_character', 'reference_image_3': 'footwear'}
    for bits in range(1, 1 << len(MULTI_VIEW_IDS)):
        views = [view for i, view in enumerate(MULTI_VIEW_IDS) if bits & (1 << i)]
        value = state(views, roles=roles)
        plan, missing = build_reference_plan(value, ALL_PRESENT)
        assert not missing
        union = set()
        global_numbers = {entry['source']: i for i, entry in enumerate(plan['sources'], 1)}
        for view in views:
            selected = _view_references(value, view, plan)
            union.update(entry['source'] for entry in selected)
            for entry in selected:
                assert entry['image_number'] == global_numbers[entry['source']]
                if entry['role'] != 'character':
                    assert entry['role'] in ALLOWED[view], (views, view, entry)
        assert union == set(global_numbers), views


@pytest.mark.parametrize('mode,batch,guide', [(m,b,g) for m in ('auto','manual') for b in (False,True) for g in (False,True)])
def test_dimensions_plan_suffix_and_layout_are_identical_to_snapshot(mode, batch, guide):
    stage = Path(__file__).resolve().parents[1]
    fixture = json.loads((stage / 'tests/fixtures/reference_v120_contract.json').read_text(encoding='utf-8'))
    value = deepcopy(fixture['state'])
    value['size']['mode'] = mode
    options = {'reference_presence':ALL_PRESENT,'batch_out':batch,'use_layout_image':guide}
    before = fixture['cases'][f'{mode}-{int(batch)}-{int(guide)}']
    after = compile_output_plan_v12(json.dumps(value), **options)
    assert before['count'] == after['count']
    for a, b in zip(before['items'], after['items']):
        for key in ('width','height','layout','filename_suffix','reference_plan_json','view_id','index'):
            assert a[key] == b[key], key
