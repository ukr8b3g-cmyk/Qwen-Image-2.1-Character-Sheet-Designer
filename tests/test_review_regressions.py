"""Generation, selection previews and optional assembly have separate limits."""
import json
from copy import deepcopy

import pytest
import torch

from qwen_image21_character_sheet.compiler import StateValidationError
from qwen_image21_character_sheet.multi_reference_compiler import DEFAULT_MULTI_STATE, MULTI_VIEW_IDS
from qwen_image21_character_sheet.output_plan import compile_output_plan, compile_output_preview
from qwen_image21_character_sheet.reference_v12_compiler import compile_output_plan_v12, compile_output_preview_v12
from qwen_image21_character_sheet.reference_v13_preview import compile_preview_request
from qwen_image21_character_sheet import reference_v12_node, reference_v13_node, sheet_assemble
from qwen_image21_character_sheet.sheet_plan import parse_sheet_plan


def state(height, mode='auto'):
    value = deepcopy(DEFAULT_MULTI_STATE)
    value['views'] = list(MULTI_VIEW_IDS)
    value['size'].update(body_height=height, mode=mode, manual_width=1024, manual_height=1024)
    return json.dumps(value)


@pytest.fixture(autouse=True)
def cpu_limit(monkeypatch):
    for module in (reference_v12_node, reference_v13_node, sheet_assemble):
        monkeypatch.setattr(module, 'runtime_max_resolution', lambda: 16384)


@pytest.mark.parametrize('batch', [False, True])
@pytest.mark.parametrize('sheet', [dict(), dict(sheet_size_mode='manual', sheet_width=8192, sheet_height=4096),
                                  dict(sheet_size_mode='manual', sheet_width=31), dict(sheet_size_mode='invalid')])
def test_unused_invalid_assembly_does_not_change_generation(batch, sheet, monkeypatch):
    raw = state(2240, 'manual')
    options = dict(character_image=object(), batch_out=batch, use_layout_image=False)
    old = reference_v12_node.QwenImage21CharacterSheetDesignerReferenceV12().compile(raw, **options)
    node = reference_v13_node.QwenImage21CharacterSheetDesignerReferenceV13()
    new = node.compile(raw, **options, **sheet)
    assert new[:6] == old
    assert node.VALIDATE_INPUTS(raw, batch_out=batch, **sheet) is True
    error = json.loads(new[6])['error']
    assert len(new[7]) == (13 if batch else 0)
    if batch:
        assert [json.loads(record)['view_id'] for record in new[7]] == list(MULTI_VIEW_IDS)
    monkeypatch.setattr(torch, 'ones', lambda *a, **k: pytest.fail('Invalid assembly allocated a canvas'))
    with pytest.raises(StateValidationError) as exc:
        sheet_assemble.QwenImage21CharacterSheetAssemble().assemble([], new[7], [new[6]])
    assert exc.value.code == error['code']


def test_assembly_error_keeps_preview_and_can_be_repaired():
    envelope = dict(state_json=state(2240, 'manual'), reference_presence={'character_image': True})
    preview = compile_preview_request(json.dumps(envelope).encode(), max_resolution=16384)
    assert (preview['width'], preview['height']) == (1024, 1024)
    assert preview['sheet_plan']['error']['code'] == 'sheet_pixel_limit'
    envelope.update(sheet_size_mode='manual', sheet_width=1024, sheet_height=1024)
    repaired = compile_preview_request(json.dumps(envelope).encode(), max_resolution=16384)
    assert repaired['sheet_plan']['canvas'] == [1024, 1024]
    assert parse_sheet_plan(json.dumps(repaired['sheet_plan'])) == repaired['sheet_plan']


@pytest.mark.parametrize('planner,previewer', [(compile_output_plan, compile_output_preview),
                                             (compile_output_plan_v12, compile_output_preview_v12)])
@pytest.mark.parametrize('guide', [False, True])
def test_large_batch_overview_preserves_every_generation_item(planner, previewer, guide):
    raw = state(6720)
    options = dict(batch_out=True, max_resolution=16384, use_layout_image=guide,
                   reference_presence={'character_image': True})
    plan = planner(raw, **options)
    preview = previewer(raw, **options)
    assert preview['batch_plan'] == plan
    assert plan['count'] == 13
    assert max(max(item['width'], item['height']) for item in plan['items']) == 8064
    assert preview['overview_only'] is True and preview['state_json'] == raw
    assert [p['id'] for p in preview['layout']['panels']] == list(MULTI_VIEW_IDS)
    assert preview['width'] <= 16384 and preview['height'] <= 16384
    with pytest.raises(StateValidationError):
        planner(raw, **{**options, 'batch_out': False})


def test_actual_individual_output_limit_is_still_enforced():
    with pytest.raises(StateValidationError) as exc:
        compile_output_preview_v12(state(16384), batch_out=True, reference_presence={'character_image': True})
    assert exc.value.code == 'size_limit'
