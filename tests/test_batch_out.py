import os
"""Independent-view execution contracts, without model loading or GPU work."""
import ast
import asyncio
from copy import deepcopy
import inspect
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import torch

from qwen_image21_character_sheet import multi_reference_compiler as c
from qwen_image21_character_sheet import multi_reference_node as n
from qwen_image21_character_sheet import multi_preview as p

ROOT = Path(__file__).resolve().parents[1]
PRESENT = {'character_image': True, 'reference_image_1': False, 'reference_image_2': True}


@pytest.fixture(autouse=True)
def cpu_resolution_limit(monkeypatch):
    monkeypatch.setattr(n, 'runtime_max_resolution', lambda: 16384)


def raw_state(views=None, manual=False):
    state = deepcopy(c.DEFAULT_MULTI_STATE)
    state['views'] = list(views or c.MULTI_PRESETS['five'])
    state['size'].update(body_height=224, mode='manual' if manual else 'auto', manual_width=768, manual_height=1152)
    return json.dumps(state, ensure_ascii=False)


@pytest.mark.parametrize('views', [('body_front',), c.MULTI_PRESETS['five'], c.MULTI_VIEW_IDS])
@pytest.mark.parametrize('manual', [False, True])
def test_each_view_has_its_own_prompt_canvas_and_filename_without_mutating_state(views, manual):
    raw = raw_state(reversed(views), manual)
    plan = c.compile_output_plan(raw, batch_out=True, reference_presence=PRESENT)
    assert plan['enabled'] is True and plan['count'] == len(views)
    state = json.loads(raw)
    for index, item in enumerate(plan['items'], 1):
        view = views[index - 1]
        assert item['index'] == index and item['view_id'] == view
        assert item['filename_suffix'] == f'_{index:02d}_{view}'
        expected_size = (192,192) if view in c.PORTRAIT_IDS else (160,256) if view in (*c.BODY_IDS,*c.CLOTHING_IDS) else (224,160)
        assert (item['width'],item['height']) == ((768,1152) if manual else expected_size)
        assert item['layout']['canvas'] == [item['width'],item['height']]
        assert [p['id'] for p in item['layout']['panels']] == [view]
        assert set(item['guide_artwork']) == {view}
        if manual:
            assert (item['width'], item['height']) == (768, 1152)
        assert 'Exactly 1 selected studies' in item['prompt']
    assert raw == json.dumps(state, ensure_ascii=False)


@pytest.mark.parametrize('layout,one,two', [(l, o, t) for l in (False, True) for o in (False, True) for t in (False, True)])
def test_off_plan_preserves_the_complete_sheet_and_actual_reference_numbering(layout, one, two):
    raw = raw_state(c.MULTI_VIEW_IDS)
    options = dict(use_layout_image=layout, reference_presence={**PRESENT, 'reference_image_1': one, 'reference_image_2': two})
    before = c.compile_multi_state(raw, **options)
    for batch_options in ({}, {'batch_out': False}):
        plan = c.compile_output_plan(raw, **options, **batch_options)
        assert plan == {'enabled': False, 'count': 1, 'items': [{**before, 'index': 1, 'view_id': 'sheet', 'filename_suffix': ''}]}


def test_auto_default_portrait_and_body_dimensions_and_legacy_json():
    state = deepcopy(c.DEFAULT_MULTI_STATE)
    state['views'] = list(c.MULTI_VIEW_IDS)
    plan = c.compile_output_plan(json.dumps(state), batch_out=True, reference_presence=PRESENT)
    for item in plan['items']:
        expected = (1024,1024) if item['view_id'] in c.PORTRAIT_IDS else (768,1344) if item['view_id'] in (*c.BODY_IDS,*c.CLOTHING_IDS) else (1184,864)
        assert (item['width'],item['height']) == expected
    from qwen_image21_character_sheet.compiler import DEFAULT_STATE_JSON
    plan = c.compile_output_plan(DEFAULT_STATE_JSON, batch_out=True, reference_presence=PRESENT)
    assert plan['count'] == 5


@pytest.mark.parametrize('role', c.REFERENCE_ROLES)
def test_single_view_filters_parts_and_dedicated_roles_without_removing_reference_slots(role):
    state = json.loads(raw_state(c.MULTI_VIEW_IDS))
    state['part_prompts'] = {'face': 'FACE-TOKEN', 'back_clothing': 'BACK-TOKEN', 'hands': 'HAND-TOKEN'}
    state['reference_roles']['reference_image_2'] = role
    plan = c.compile_output_plan(json.dumps(state), batch_out=True, reference_presence=PRESENT, style='watercolor')
    for item in plan['items']:
        view = item['view_id']
        for part, token in state['part_prompts'].items():
            assert (token in item['prompt']) == (view in c.part_views(state, part))
        if role != 'same_character':
            assert ('<image2> is an additional' in item['prompt']) == (view in c.role_views(state, role))
        assert 'watercolor' in item['prompt']


@pytest.mark.parametrize('bad', [None, 0, 1, 'true', [], {}])
def test_nonboolean_batch_rejected_by_preview_and_execution(bad):
    raw = raw_state()
    with pytest.raises(c.StateValidationError) as error:
        c.compile_output_plan(raw, batch_out=bad)
    assert error.value.code == 'invalid_type'
    with pytest.raises(c.StateValidationError):
        p.compile_preview_request(json.dumps({'state_json': raw, 'batch_out': bad}).encode(), max_resolution=16384)
    assert n.QwenImage21CharacterSheetDesignerMultiReference.VALIDATE_INPUTS(raw, batch_out=bad) is not True


def test_batch_preview_preserves_the_full_layout_and_both_missing_and_present_reference_states():
    raw = raw_state(c.MULTI_VIEW_IDS, manual=True)
    for presence in ({}, PRESENT):
        body = dict(state_json=raw, reference_presence=presence)
        off = p.compile_preview_request(json.dumps(body).encode(), max_resolution=16384)
        on = p.compile_preview_request(json.dumps({**body, 'batch_out': True}).encode(), max_resolution=16384)
        assert on.pop('batch_plan')['count'] == 13
        assert off.pop('batch_plan')['count'] == 1
        assert on == off


def test_batch_guide_off_never_loads_renders_or_tensorizes(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Guide OFF called the artwork or tensor path')
    monkeypatch.setattr(n, 'render_layout_image', forbidden)
    monkeypatch.setattr(n.np, 'asarray', forbidden)
    monkeypatch.setattr(n.torch, 'from_numpy', forbidden)
    output = n.QwenImage21CharacterSheetDesignerMultiReference().compile(raw_state(c.MULTI_VIEW_IDS), object(), batch_out=True)
    assert all(len(values) == 13 for values in output)
    assert output[3] == [None] * 13
    assert output[4][0] == '_01_face_front' and output[4][-1] == '_13_feet'
    assert n.QwenImage21CharacterSheetDesignerMultiReference.OUTPUT_IS_LIST == (True,) * 5
    with pytest.raises(c.StateValidationError):
        n.QwenImage21CharacterSheetDesignerMultiReference().compile(raw_state(), None, batch_out=True)


def test_empty_and_invalid_dimensions_fail_before_drawing(monkeypatch):
    monkeypatch.setattr(n, 'render_layout_image', lambda *args, **kwargs: pytest.fail('Invalid input reached drawing'))
    for changes in ({'views': []}, {'size': {**c.DEFAULT_MULTI_STATE['size'], 'manual_width': 767}}):
        state = {**c.DEFAULT_MULTI_STATE, **changes}
        with pytest.raises(c.StateValidationError):
            n.QwenImage21CharacterSheetDesignerMultiReference().compile(json.dumps(state), object(), batch_out=True, use_layout_image=True)


class ExecutionBlocker:
    pass


class ComfyInternal:
    pass


class NodeContext:
    def __init__(self, *args):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.mark.parametrize('layout_on', [False, True])
@pytest.mark.parametrize('views', [('body_front',), c.MULTI_PRESETS['five'], c.MULTI_VIEW_IDS])
def test_actual_core_list_mapping_and_encoder_pair_every_view_with_its_guide(views, layout_on):
    """Installed Core function bodies with CPU clip/VAE and context doubles."""
    core_root = os.environ.get('QWEN_SHEET_TEST_COMFYUI_ROOT')
    if not core_root:
        pytest.skip('Set QWEN_SHEET_TEST_COMFYUI_ROOT for installed Core interoperability checks')
    core = Path(core_root)
    execution = core / 'execution.py'
    if not execution.exists():
        pytest.skip('Installed Core source is not available')
    tree = ast.parse(execution.read_text(encoding='utf-8'))
    functions = [v for v in tree.body if isinstance(v, (ast.FunctionDef, ast.AsyncFunctionDef)) and v.name in ('_async_map_node_over_list', 'merge_result_data')]
    namespace = dict(asyncio=asyncio, inspect=inspect, is_class=inspect.isclass,
                     ExecutionBlocker=ExecutionBlocker, _ComfyNodeInternal=ComfyInternal, CurrentNodeContext=NodeContext)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(execution), 'exec'), namespace)
    source = core / 'comfy_extras/nodes_qwen.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    encoder = next(v for v in tree.body if isinstance(v, ast.ClassDef) and v.name == 'TextEncodeQwenImage21')
    execute = next(v for v in encoder.body if isinstance(v, ast.FunctionDef) and v.name == 'execute')
    cls = ast.ClassDef(name='Encoder', bases=[], keywords=[], body=[execute], decorator_list=[])
    namespace.update(torch=torch, math=math, io=SimpleNamespace(Autogrow=SimpleNamespace(Type=dict), NodeOutput=lambda *args: args),
        comfy=SimpleNamespace(model_management=SimpleNamespace(intermediate_device=lambda: 'cpu')),
        node_helpers=SimpleNamespace(conditioning_set_values=lambda condition, values, append=False: [[row[0], {**row[1], **values}] for row in condition]))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(source), 'exec'), namespace)
    calls = []
    clip = SimpleNamespace(tokenize=lambda prompt, **kwargs: calls.append((prompt, kwargs)) or prompt,
        encode_from_tokens_scheduled=lambda tokens: [[torch.zeros(1), {}]])
    reference = torch.ones((2, 32, 32, 4))
    raw = raw_state(views)
    output = n.QwenImage21CharacterSheetDesignerMultiReference().compile(raw, reference, reference_image_2=reference,
        use_layout_image=layout_on, batch_out=True)
    merged = namespace['merge_result_data']([output], n.QwenImage21CharacterSheetDesignerMultiReference())
    images = [{'image_1': guide, 'image_2': reference, 'image_4': reference} for guide in merged[3]]
    result = asyncio.run(namespace['_async_map_node_over_list']('test', 'encoder', namespace['Encoder'],
        {'clip': [clip], 'prompt': merged[0], 'negative_prompt': [''], 'vae': [SimpleNamespace(encode=lambda image: image)],
         'resolution': [0], 'images': images}, 'execute'))
    assert len(result) == len(views) and len(calls) == 2 * len(views)
    for index, (positive, _, latent) in enumerate(result):
        assert calls[2 * index][0] == merged[0][index]
        refs = positive[0][1]['reference_latents']
        assert len(refs) == (3 if layout_on else 2)
        if layout_on:
            assert tuple(refs[0].shape) == (1, merged[2][index], merged[1][index], 3)
            assert tuple(latent['samples'].shape) == (1, 64, merged[2][index] // 16, merged[1][index] // 16)
        else:
            assert tuple(latent['samples'].shape) == (1, 64, 2, 2)
        assert tuple(refs[-1].shape) == (1, 32, 32, 4)


def test_package_versions_match_and_widgets_are_appended_for_existing_workflows():
    version = json.loads((ROOT / 'package.json').read_text())['version']
    assert f'version = "{version}"' in (ROOT / 'pyproject.toml').read_text()
    optional = list(n.QwenImage21CharacterSheetDesignerMultiReference.INPUT_TYPES()['optional'])
    assert optional == ['reference_image_1', 'reference_image_2', 'use_layout_image', 'style', 'batch_out', 'reference_image_3']
    assert n.QwenImage21CharacterSheetDesignerMultiReference.INPUT_TYPES()['optional']['batch_out'][1]['default'] is False
