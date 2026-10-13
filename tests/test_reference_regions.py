"""Crops change actual encoded pixels without changing output or source routing."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
import torch

from qwen_image21_character_sheet import sheet_encode
from qwen_image21_character_sheet.multi_reference_compiler import DEFAULT_MULTI_STATE
from qwen_image21_character_sheet.reference_regions import crop_reference, parse_reference_regions
from qwen_image21_character_sheet.reference_v12_compiler import compile_output_plan_v12


def image():
    return torch.arange(2 * 10 * 20 * 4, dtype=torch.float32).reshape(2, 10, 20, 4)


def test_unspecified_and_full_regions_are_a_true_pixel_bypass():
    value = image()
    for rules in ({}, {'reference_image_1': {}}, {'reference_image_1': {'*': [0, 0, 1, 1]}}):
        assert crop_reference(value, 'reference_image_1', ['face_front'], rules) is value


def test_crop_preserves_batch_channels_values_and_owns_its_pixels():
    value = image()
    rules = {'reference_image_1': {'*': [.25, .2, .5, .4]}}
    cropped = crop_reference(value, 'reference_image_1', ['face_front'], rules)
    assert torch.equal(cropped, value[:, 2:6, 5:15, :])
    assert cropped.shape == (2, 4, 10, 4)
    cropped[0, 0, 0, 0] = -1
    assert value[0, 2, 5, 0] != -1


def test_view_override_and_shared_sheet_union():
    value = image()
    rules = {'character_image': {'*': [0, 0, 1, 1],
                               'face_front': [.1, .1, .2, .3],
                               'face_back': [.5, .2, .3, .4]}}
    front = crop_reference(value, 'character_image', ['face_front'], rules)
    rear = crop_reference(value, 'character_image', ['face_back'], rules)
    combined = crop_reference(value, 'character_image', ['face_front', 'face_back'], rules)
    assert torch.equal(front, value[:, 1:4, 2:6])
    assert torch.equal(rear, value[:, 2:6, 10:16])
    assert torch.equal(combined, value[:, 1:6, 2:16])
    assert crop_reference(value, 'character_image', ['face_front', 'body_front'], rules) is value


def test_unspecified_view_in_mixed_sheet_retains_complete_reference():
    value = image()
    rules = {'character_image': {'face_front': [.2, .2, .2, .2]}}
    assert crop_reference(value, 'character_image', ['face_front', 'body_front'], rules) is value


def test_outside_region_is_clipped_to_real_pixels():
    value = image()
    assert torch.equal(crop_reference(value, 'character_image', ['hands'],
        {'character_image': {'*': [-.5, -.5, 1, 1]}}), value[:, :5, :10])
    with pytest.raises(ValueError, match='no pixels'):
        crop_reference(value, 'character_image', ['hands'], {'character_image': {'*': [2, 0, 1, 1]}})
    with pytest.raises(ValueError, match='no pixels'):
        crop_reference(value, 'character_image', ['hands'], {'character_image': {'*': [1e308, 0, 1e308, 1]}})


@pytest.mark.parametrize('rules', [[], {'layout_image': {'*': [0, 0, 1, 1]}},
    {'character_image': [0, 0, 1, 1]}, {'character_image': {'portrait': [0, 0, 1, 1]}},
    {'character_image': {'*': [0, 0, 1]}}, {'character_image': {'*': [True, 0, 1, 1]}},
    {'character_image': {'*': [0, 0, 0, 1]}}, {'character_image': {'*': [0, 0, float('nan'), 1]}}])
def test_invalid_configuration_fails_before_encoding(rules):
    with pytest.raises(ValueError):
        parse_reference_regions(json.dumps(rules))


@pytest.mark.parametrize('mode', ['auto', 'manual'])
@pytest.mark.parametrize('batch', [False, True])
@pytest.mark.parametrize('guide', [False, True])
def test_regions_leave_six_outputs_sizes_numbering_and_guide_untouched(monkeypatch, mode, batch, guide):
    state = deepcopy(DEFAULT_MULTI_STATE)
    state['views'] = ['face_front', 'body_front']
    state['reference_roles']['reference_image_1'] = 'face'
    state['size'].update(mode=mode, manual_width=1536, manual_height=864)
    items = compile_output_plan_v12(json.dumps(state), batch_out=batch, use_layout_image=guide,
        reference_presence={'character_image': True, 'reference_image_1': True})['items']
    sent = []
    monkeypatch.setattr(sheet_encode, 'TextEncodeQwenImage21', SimpleNamespace(execute=lambda **kw:
        sent.append(kw) or SimpleNamespace(result=('positive', 'negative', 'latent'))))
    original = image()
    cropped_config = json.dumps({'reference_image_1': {'*': [.25, .2, .5, .4]}})
    for item in items:
        if mode == 'manual':
            assert (item['width'], item['height']) == (1536, 864)
        layout = torch.zeros(1, 3, 5, 3) if guide else None
        result = sheet_encode.QwenImage21CharacterSheetEncode().encode('clip', item['prompt'], '',
            item['reference_plan_json'], resolution=1024, vae='vae', character_image=original,
            reference_image_1=original, layout_image=layout, reference_regions=cropped_config)
        assert result == ('positive', 'negative')
        inputs = list(sent[-1]['images'].values())
        assert len(inputs) == len(item['reference_plan'])
        if guide:
            assert inputs[0] is layout
        assert inputs[-2] is original
        assert torch.equal(inputs[-1], original[:, 2:6, 5:15])
        assert sent[-1]['resolution'] == 1024
        assert sent[-1]['vae'] == 'vae'


def test_reference_mode_has_no_unrequested_coverage_examples():
    state = deepcopy(DEFAULT_MULTI_STATE)
    state['views'] = ['clothing_front', 'hands', 'feet']
    item = compile_output_plan_v12(json.dumps(state), reference_presence={'character_image': True})['items'][0]
    assert 'gloved hands' not in item['prompt']
    assert 'barefoot feet' not in item['prompt']
    assert 'hand coverage override' not in item['prompt'].lower()
    assert 'Preserve the assigned reference hand coverage' in item['prompt']
    for setting, wording in (('bare', 'bare skin, no gloves'), ('gloved', 'visible hands are gloved')):
        state['hand_state'] = setting
        text = compile_output_plan_v12(json.dumps(state), reference_presence={'character_image': True})['items'][0]['prompt']
        assert wording in text
