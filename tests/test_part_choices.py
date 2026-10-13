"""Part choices affect their visible parts without changing output geometry or routing."""
from copy import deepcopy
from itertools import product
import json

import pytest

from qwen_image21_character_sheet.multi_reference_compiler import (
    BODY_IDS, CLOTHING_IDS, CLOTHING_TYPES, DEFAULT_MULTI_STATE, FOOTWEAR_STATES,
    HAND_STATES, MULTI_VIEW_IDS, StateValidationError, parse_multi_state,
)
from qwen_image21_character_sheet.reference_v12_compiler import DEFAULT_V12_STATE_JSON, compile_output_plan_v12

PRESENT = dict.fromkeys(('character_image', 'reference_image_1', 'reference_image_2', 'reference_image_3'), True)
CHOICES = list(product(CLOTHING_TYPES, HAND_STATES, FOOTWEAR_STATES))


def state(views, choice=('reference', 'reference', 'reference'), clothing_mode='worn'):
    value = deepcopy(DEFAULT_MULTI_STATE)
    value.update(views=list(views), clothing_mode=clothing_mode,
                 clothing_type=choice[0], hand_state=choice[1], footwear_state=choice[2])
    return value


def output(value, **options):
    return compile_output_plan_v12(json.dumps(value), reference_presence=PRESENT, **options)


@pytest.mark.parametrize('choice', CHOICES)
@pytest.mark.parametrize('view', MULTI_VIEW_IDS)
def test_choice_scope_and_reference_plan(choice, view):
    item = output(state([view], choice))['items'][0]
    baseline = output(state([view]))['items'][0]
    prompt = item['prompt']
    assert ('Lower clothing structure override' in prompt) == (choice[0] != 'reference' and view in (*BODY_IDS, *CLOTHING_IDS))
    assert ('Hand coverage override' in prompt) == (choice[1] != 'reference' and view in (*BODY_IDS, *CLOTHING_IDS, 'hands'))
    assert ('Footwear presence override' in prompt) == (choice[2] != 'reference' and view in (*BODY_IDS, 'feet'))
    for key in ('width', 'height', 'layout', 'reference_plan_json', 'filename_suffix'):
        assert item[key] == baseline[key]


@pytest.mark.parametrize('choice', CHOICES)
@pytest.mark.parametrize('view', CLOTHING_IDS)
def test_garments_only_does_not_gain_hands_or_feet(choice, view):
    prompt = output(state([view], choice, 'garment'))['items'][0]['prompt']
    assert 'Hand coverage override' not in prompt
    assert 'Footwear presence override' not in prompt
    assert 'No head, neck, arms, hands, legs, feet, torso, skin, person, mannequin or body' in prompt


@pytest.mark.parametrize('batch', [False, True])
@pytest.mark.parametrize('mode', ['auto', 'manual'])
def test_output_modes_keep_geometry_and_apply_only_to_each_output(batch, mode):
    value = state(['face_front', 'body_front', 'clothing_front', 'hands', 'feet'], ('pants', 'bare', 'unshod'))
    value['size'].update(mode=mode, manual_width=1024, manual_height=1024)
    result = output(value, batch_out=batch)
    reference = deepcopy(value)
    reference.update(clothing_type='reference', hand_state='reference', footwear_state='reference')
    baseline = output(reference, batch_out=batch)
    assert result['count'] == baseline['count']
    for item, old in zip(result['items'], baseline['items']):
        for key in ('width', 'height', 'layout', 'reference_plan_json', 'filename_suffix'):
            assert item[key] == old[key]
        if item['view_id'] == 'face_front':
            assert item['prompt'] == old['prompt']


def test_shape_choice_replaces_conflicting_fixed_clothing_retention_only():
    value = state(['clothing_front'], ('pants', 'bare', 'reference'))
    value['part_prompts']['lower_body'] = 'Keep the blue fabric. A single skirt hem.'
    prompt = output(value)['items'][0]['prompt']
    assert 'pants with separate sections for each leg' in prompt
    assert 'Do not replace its garment type or add separate leg openings' not in prompt
    assert 'Do not replace the garment type or split a continuous hem' not in prompt
    assert 'Highest priority compatible appearance details' in prompt
    assert prompt.count(value['part_prompts']['lower_body']) == 1
    assert 'without changing garment length' not in prompt


def test_footwear_presence_keeps_kind_open_and_reference_legwear():
    shod = output(state(['feet'], ('reference', 'reference', 'shod')))['items'][0]['prompt']
    assert 'preserve its referenced kind and design' in shod
    assert 'outfit-appropriate kind only when no reference shows it' in shod
    unshod = output(state(['feet'], ('reference', 'reference', 'unshod')))['items'][0]['prompt']
    assert 'no shoes or boots' in unshod
    assert 'keep referenced bare feet, socks or tights, without inventing socks' in unshod
    assert 'including complete boot shafts where present' not in unshod


@pytest.mark.parametrize('field', ['clothing_type', 'footwear_state'])
@pytest.mark.parametrize('value', ['unknown', None, 1, [], {}])
def test_invalid_new_choice_is_reported_at_the_state_boundary(field, value):
    data = deepcopy(DEFAULT_MULTI_STATE)
    data[field] = value
    with pytest.raises(StateValidationError) as error:
        parse_multi_state(json.dumps(data))
    assert error.value.code == 'invalid_' + field


def test_old_state_shape_and_saved_hand_choice_are_preserved():
    for hand in HAND_STATES:
        old = deepcopy(DEFAULT_MULTI_STATE)
        old['hand_state'] = hand
        assert parse_multi_state(json.dumps(old)) == old
        assert 'clothing_type' not in parse_multi_state(json.dumps(old))
        assert 'footwear_state' not in parse_multi_state(json.dumps(old))
    new = parse_multi_state(DEFAULT_V12_STATE_JSON)
    assert new['hand_state'] == new['clothing_type'] == new['footwear_state'] == 'reference'


def test_new_state_roundtrip_does_not_mutate_other_inputs():
    value = state(['body_front', 'hands', 'feet'], ('skirt_robe', 'gloved', 'shod'))
    value['part_prompts']['footwear'] = '  赤いヒール\n参照の飾りを保持  '
    value['reference_roles']['reference_image_3'] = 'footwear'
    assert parse_multi_state(json.dumps(parse_multi_state(json.dumps(value)), ensure_ascii=False)) == value


@pytest.mark.parametrize('view', CLOTHING_IDS)
@pytest.mark.parametrize('choice', CLOTHING_TYPES)
def test_worn_clothing_uses_the_wearer_for_auto_and_explicit_shapes(view, choice):
    prompt = output(state([view], (choice, 'reference', 'reference')))['items'][0]['prompt']
    assert 'same character actually wearing the complete outfit' in prompt
    assert 'human body inside the clothing' in prompt
    assert 'head outside the frame' in prompt
    assert 'empty clothes or a floating outfit' in prompt
    assert 'No head, neck, arms, hands, legs' not in prompt


@pytest.mark.parametrize('batch', [False, True])
def test_gloves_add_real_coverage_without_overriding_a_fingerless_directive(batch):
    value = state(['face_front', 'hands', 'body_front'], ('reference', 'gloved', 'reference'))
    value['part_prompts']['hands'] = 'Black fingerless leather gloves; keep the fingers exposed.'
    result = output(value, batch_out=batch)
    for item in result['items']:
        if item['view_id'] == 'face_front':
            assert 'gloves' not in item['prompt']
            continue
        prompt = item['prompt']
        assert 'actual gloves' in prompt
        assert 'replace reference bare hands with gloves' in prompt
        assert value['part_prompts']['hands'] in prompt
        assert 'Follow applicable glove details and finger openings' in prompt


def test_auto_feet_preserve_visible_coverage_without_a_default_boot_example():
    value = state(['feet'])
    prompt = output(value)['items'][0]['prompt']
    assert 'matching pair' in prompt
    assert 'reproduce BOTH corresponding reference feet' in prompt
    assert 'Keep footwear presence consistent across the pair' in prompt
    assert 'preserve left-right differences only when the reference itself shows them' in prompt
    assert 'Do not infer or invent footwear from the outfit' in prompt
    assert 'boot shafts' not in prompt
    assert 'foot or shoe' not in prompt
    value['part_prompts']['footwear'] = 'Use open-toe sandals with red straps.'
    prompt = output(value)['items'][0]['prompt']
    assert 'Unless applicable footwear text changes it' in prompt
    assert prompt.count(value['part_prompts']['footwear']) == 1


def test_shod_is_identifiable_footwear_in_details_and_mixed_sheets():
    for views in (['feet'], ['face_front', 'body_front', 'body_back']):
        prompt = output(state(views, ('reference', 'reference', 'shod')))['items'][0]['prompt']
        assert 'actual footwear' in prompt
        assert 'uppers or straps and soles' in prompt
        assert 'outfit-appropriate kind only when no reference shows it' in prompt
