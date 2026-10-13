"""Acceptance contracts for reference routing and independent output behavior."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
import torch

from qwen_image21_character_sheet.multi_reference_compiler import DEFAULT_MULTI_STATE, MULTI_VIEW_IDS
from qwen_image21_character_sheet.reference_plan import REFERENCE_ROLES
from qwen_image21_character_sheet.reference_v12_compiler import compile_output_plan_v12
from qwen_image21_character_sheet.reference_v12_plan import parse_reference_plan
from qwen_image21_character_sheet import reference_v12_node as node
from qwen_image21_character_sheet import sheet_encode as encoder

ALLOWED = {
    'face_front': {'face', 'head', 'clothing', 'clothing_front', 'same_character'},
    'face_left': {'face', 'head', 'clothing', 'clothing_front', 'clothing_back', 'same_character'},
    'face_right': {'face', 'head', 'clothing', 'clothing_front', 'clothing_back', 'same_character'},
    'face_3q_left': {'face', 'head', 'clothing', 'clothing_front', 'same_character'},
    'face_3q_right': {'face', 'head', 'clothing', 'clothing_front', 'same_character'},
    'face_back': {'head', 'clothing', 'clothing_back', 'same_character'},
    'body_front': {'face', 'head', 'clothing', 'clothing_front', 'hands', 'footwear', 'same_character'},
    'body_left': {'face', 'head', 'clothing', 'clothing_front', 'clothing_back', 'hands', 'footwear', 'same_character'},
    'body_back': {'head', 'clothing', 'clothing_back', 'hands', 'footwear', 'same_character'},
    'clothing_front': {'clothing', 'clothing_front', 'hands', 'same_character'},
    'clothing_back': {'clothing', 'clothing_back', 'hands', 'same_character'},
    'hands': {'hands'}, 'feet': {'footwear'},
}


def state(views, *, roles=None, garment=False, manual=False, prompts=None):
    value = deepcopy(DEFAULT_MULTI_STATE)
    value['views'] = list(views)
    value['clothing_mode'] = 'garment' if garment else 'worn'
    value['size'].update(mode='manual' if manual else 'auto', manual_width=1536, manual_height=864)
    value['reference_roles'].update(roles or {})
    value['part_prompts'] = prompts or {}
    return json.dumps(value)


@pytest.mark.parametrize('view', MULTI_VIEW_IDS)
@pytest.mark.parametrize('role', REFERENCE_ROLES)
def test_only_visible_roles_reach_encoder(view, role):
    item = compile_output_plan_v12(state([view], roles={'reference_image_3': role}),
        reference_presence={'character_image': True, 'reference_image_3': True})['items'][0]
    sources = {e['source'] for e in parse_reference_plan(item['reference_plan_json'])['sources']}
    assert ('reference_image_3' in sources) == (role in ALLOWED[view])
    if view in ('hands', 'feet') and role in ALLOWED[view]:
        assert 'character_image' not in sources


def test_ref3_only_winner_and_guide_numbering_are_the_encoded_images(monkeypatch):
    sent = []
    monkeypatch.setattr(encoder, 'TextEncodeQwenImage21', SimpleNamespace(execute=lambda **kw: (
        sent.append(kw) or SimpleNamespace(result=('positive', 'negative', 'unused latent')))))
    for guide in (False, True):
        raw = state(['face_front'], roles={'reference_image_1': 'face', 'reference_image_3': 'face'})
        item = compile_output_plan_v12(raw, use_layout_image=guide,
            reference_presence={'character_image': True, 'reference_image_1': True, 'reference_image_3': True})['items'][0]
        result = encoder.QwenImage21CharacterSheetEncode().encode('clip', item['prompt'], '', item['reference_plan_json'],
            character_image='identity', reference_image_1='losing ref', reference_image_2='unused clothes',
            reference_image_3='winning face', layout_image='guide' if guide else None)
        assert result == ('positive', 'negative')
        assert list(sent[-1]['images'].values()) == (['guide', 'identity', 'winning face'] if guide else ['identity', 'winning face'])
        assert item['reference_plan'][-1]['tag'] == ('<image3>' if guide else '<image2>')
        assert all(e['source'] != 'reference_image_1' for e in item['reference_plan'])


def test_guide_off_list_dimensions_and_prompt_crop(monkeypatch):
    monkeypatch.setattr(node, 'runtime_max_resolution', lambda: 16384)
    monkeypatch.setattr(node, 'render_layout_image', lambda *a, **kw: pytest.fail('Guide OFF rendered an image'))
    raw = state(['face_front', 'body_back', 'feet'], manual=True)
    output = node.QwenImage21CharacterSheetDesignerReferenceV12().compile(raw, character_image=torch.zeros(1, 8, 8, 3), batch_out=True)
    assert len(output) == 6 and all(len(values) == 3 for values in output)
    assert output[1] == [1536]*3 and output[2] == [864]*3 and output[3] == [None]*3
    assert 'single illustration' in output[0][0] and 'reference sheet' not in output[0][0]
    assert 'align the soles' not in output[0][0] and 'complete head' not in output[0][2]
    assert output[4] == ['_01_face_front', '_02_body_back', '_03_feet']


def test_garment_only_uses_no_identity_or_unrelated_refs():
    item = compile_output_plan_v12(state(['clothing_front', 'clothing_back'], garment=True,
        roles={'reference_image_1': 'face', 'reference_image_2': 'clothing', 'reference_image_3': 'footwear'}),
        reference_presence=dict.fromkeys(('character_image', 'reference_image_1', 'reference_image_2', 'reference_image_3'), True))['items'][0]
    assert [e['source'] for e in item['reference_plan']] == ['reference_image_2']
    assert 'baseline person' not in item['prompt'] and 'No head, neck' in item['prompt']


def test_literal_priority_and_missing_reference():
    literal = '  青い靴\n白いひも  '
    item = compile_output_plan_v12(state(['feet'], roles={'reference_image_3': 'footwear'}, prompts={'footwear': literal}),
        reference_presence={'reference_image_3': True})['items'][0]
    assert literal in item['prompt'] and 'Highest priority' in item['prompt']
    with pytest.raises(ValueError, match='body_front'):
        compile_output_plan_v12(state(['body_front']), reference_presence={'reference_image_3': True})


def test_missing_planned_source_does_not_shift_image_numbers(monkeypatch):
    monkeypatch.setattr(encoder, 'TextEncodeQwenImage21', SimpleNamespace(execute=lambda **kw: pytest.fail('Encoded missing reference')))
    item = compile_output_plan_v12(state(['face_front'], roles={'reference_image_3': 'face'}),
        reference_presence={'character_image': True, 'reference_image_3': True})['items'][0]
    with pytest.raises(ValueError, match='reference_image_3'):
        encoder.QwenImage21CharacterSheetEncode().encode('clip', item['prompt'], '', item['reference_plan_json'], character_image='identity')
