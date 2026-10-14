"""Exact correspondence and geometry are checked independently from image content."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
import torch

from qwen_image21_character_sheet.compiler import StateValidationError
from qwen_image21_character_sheet.multi_reference_compiler import MULTI_VIEW_IDS
from qwen_image21_character_sheet.multi_guide_geometry import panel_bounds
from qwen_image21_character_sheet.output_plan import compile_output_plan
from qwen_image21_character_sheet.reference_v12_compiler import DEFAULT_V12_STATE_JSON, compile_output_plan_v12
from qwen_image21_character_sheet.reference_v12_node import QwenImage21CharacterSheetDesignerReferenceV12 as V12
from qwen_image21_character_sheet.reference_v13_node import QwenImage21CharacterSheetDesignerReferenceV13 as V13
from qwen_image21_character_sheet.reference_v13_preview import compile_preview_request
from qwen_image21_character_sheet.sheet_plan import make_sheet_plan, validate_sheet_plan, serialize_sheet_plan, plan_hash, contain_bounds
from qwen_image21_character_sheet.sheet_assemble import QwenImage21CharacterSheetAssemble
from qwen_image21_character_sheet import reference_v12_node, reference_v13_node, sheet_assemble


@pytest.fixture(autouse=True)
def cpu_runtime_limit(monkeypatch):
    for module in (reference_v12_node, reference_v13_node, sheet_assemble):
        monkeypatch.setattr(module, 'runtime_max_resolution', lambda: 16384)


def state(views=('face_front', 'body_front'), mode='auto'):
    value = json.loads(DEFAULT_V12_STATE_JSON)
    value['views'] = list(views)
    value['size'].update(mode=mode, manual_width=1536, manual_height=864)
    return json.dumps(value)


def plan(views=('face_front', 'body_front'), **options):
    return make_sheet_plan(state(views), sheet_size_mode='manual', sheet_width=256, sheet_height=256, **options)


def inputs(sheet):
    images, records = [], []
    for index, view in enumerate(sheet['views']):
        width, height = (32, 64) if index % 2 else (64, 32)
        image = torch.full((1, height, width, 3), index / max(1, len(sheet['views'])))
        images.append(image)
        records.append(json.dumps({'schema_version': 1, 'view_id': view['view_id'], 'sheet_plan_hash': sheet['plan_hash'],
                                   'width': width, 'height': height, 'prompt': 'declared view ' + view['view_id']}))
    return images, records, [serialize_sheet_plan(sheet)]


def sign(value):
    value['plan_hash'] = plan_hash({k: v for k, v in value.items() if k != 'plan_hash'})
    return value


def test_ragged_images_are_bound_by_id_and_contained_without_mutation():
    sheet = plan()
    images, records, root = inputs(sheet)
    before = [im.clone() for im in images]
    node = QwenImage21CharacterSheetAssemble()
    output, raw = node.assemble(images, records, root)
    reversed_output, _ = node.assemble(images[::-1], records[::-1], root)
    assert torch.equal(output, reversed_output)
    assert output.shape == (1, 256, 256, 3) and output.device.type == 'cpu'
    assert all(torch.equal(a, b) for a, b in zip(images, before))
    info = json.loads(raw)
    for view, image, placement in zip(sheet['views'], images, info['views']):
        l, t, r, b = placement['image_bounds']
        pl, pt, pr, pb = view['bounds']
        assert pl <= l < r <= pr and pt <= t < b <= pb
        assert abs((r-l) / (b-t) - image.shape[2] / image.shape[1]) < .05
        assert torch.allclose(output[:, t:b, l:r], image[0, 0, 0].expand_as(output[:, t:b, l:r]))
    assert torch.equal(output[0, 0, 0], torch.ones(3))


@pytest.mark.parametrize('problem', ['missing_image', 'extra_image', 'missing_record', 'duplicate_id', 'unknown_id', 'wrong_hash', 'wrong_size', 'batch2', 'nan', 'range', 'multiple_plans', 'invalid_record'])
def test_invalid_correspondence_is_rejected_before_canvas_allocation(problem, monkeypatch):
    sheet = plan()
    images, records, root = inputs(sheet)
    if problem == 'missing_image': images.pop()
    elif problem == 'extra_image': images.append(images[-1])
    elif problem == 'missing_record': records.pop()
    elif problem == 'duplicate_id': records[1] = records[0]
    elif problem == 'unknown_id':
        rec = json.loads(records[0]); rec['view_id'] = 'body_back'; records[0] = json.dumps(rec)
    elif problem == 'wrong_hash':
        rec = json.loads(records[0]); rec['sheet_plan_hash'] = '0' * 64; records[0] = json.dumps(rec)
    elif problem == 'wrong_size': images[0] = torch.zeros(1, 1, 1, 3)
    elif problem == 'batch2': images[0] = images[0].repeat(2, 1, 1, 1)
    elif problem == 'nan': images[0][0, 0, 0, 0] = float('nan')
    elif problem == 'range': images[0][0, 0, 0, 0] = 2
    elif problem == 'multiple_plans': root.append(root[0])
    elif problem == 'invalid_record': records[0] = '[]'
    monkeypatch.setattr(torch, 'ones', lambda *a, **k: pytest.fail('Allocated invalid sheet'))
    with pytest.raises(StateValidationError):
        QwenImage21CharacterSheetAssemble().assemble(images, records, root)


@pytest.mark.parametrize('problem', ['bounds_empty', 'bounds_outside', 'bounds_float', 'overlap', 'unknown_view', 'duplicate_view', 'hash', 'version_bool', 'pixel_limit'])
def test_sheet_plan_rejects_invalid_geometry(problem):
    sheet = deepcopy(plan())
    if problem == 'bounds_empty': sheet['views'][0]['bounds'][2] = sheet['views'][0]['bounds'][0]
    elif problem == 'bounds_outside': sheet['views'][0]['bounds'][0] = -1
    elif problem == 'bounds_float': sheet['views'][0]['bounds'][0] = 1.5
    elif problem == 'overlap': sheet['views'][1]['bounds'] = sheet['views'][0]['bounds'].copy()
    elif problem == 'unknown_view': sheet['views'][0]['view_id'] = 'unknown'
    elif problem == 'duplicate_view': sheet['views'][1]['view_id'] = sheet['views'][0]['view_id']
    elif problem == 'version_bool': sheet['schema_version'] = True
    elif problem == 'pixel_limit': sheet['canvas'] = [8192, 8192]
    sign(sheet)
    if problem == 'hash': sheet['plan_hash'] = '0' * 64
    with pytest.raises(StateValidationError): validate_sheet_plan(sheet)


@pytest.mark.parametrize('generation_mode,sheet_mode,width,height', [('auto', 'manual', 1536, 864), ('manual', 'manual', 864, 1536), ('manual', 'manual', 1024, 1024), ('manual', 'auto', 1536, 864)])
@pytest.mark.parametrize('guide,batch', [(g, b) for g in (False, True) for b in (False, True)])
def test_v13_keeps_six_generation_outputs_and_separates_sheet_dimensions(generation_mode, sheet_mode, width, height, guide, batch):
    raw = state(['face_front', 'face_left', 'body_front', 'body_left', 'body_back'], generation_mode)
    image = torch.zeros(1, 32, 32, 3)
    options = dict(state_json=raw, character_image=image, use_layout_image=guide, batch_out=batch)
    old = V12().compile(**options)
    new = V13().compile(**options, sheet_size_mode=sheet_mode, sheet_width=width, sheet_height=height)
    for i in (0, 1, 2, 4, 5): assert old[i] == new[i]
    for a, b in zip(old[3], new[3]):
        assert (a is None and b is None) if not guide else torch.equal(a, b)
    assert V12.RETURN_TYPES == V13.RETURN_TYPES[:6] and len(V12.RETURN_TYPES) == 6
    sheet = json.loads(new[6])
    assert len(sheet['views']) == 5
    if sheet_mode == 'manual': assert sheet['canvas'] == [width, height]
    if generation_mode == 'manual': assert old[1] == [1536] * (5 if batch else 1) and old[2] == [864] * (5 if batch else 1)
    assert len(new[7]) == (5 if batch else 0)


def test_preview_returns_the_same_pixel_bounds_and_hash_as_execution():
    raw = state(['face_front', 'face_left', 'body_front', 'body_left', 'body_back'])
    options = {'state_json': raw, 'sheet_size_mode': 'manual', 'sheet_width': 1536, 'sheet_height': 864, 'batch_out': True, 'use_layout_image': False, 'reference_presence': {'character_image': True}}
    preview = compile_preview_request(json.dumps(options).encode(), max_resolution=16384)
    new = V13().compile(raw, character_image=torch.zeros(1, 32, 32, 3), sheet_size_mode='manual', sheet_width=1536, sheet_height=864)
    assert preview['sheet_plan'] == json.loads(new[6])
    selection = json.loads(raw); selection['size'].update(mode='manual', manual_width=1536, manual_height=864)
    full = compile_output_plan(json.dumps(selection))['items'][0]['layout']
    assert [list(panel_bounds(full, p)) for p in full['panels']] == [v['bounds'] for v in preview['sheet_plan']['views']]
    assert preview['batch_plan']['items'][0]['width'] != preview['sheet_plan']['canvas'][0]


def test_all_8191_view_subsets_have_unique_valid_integer_geometry():
    base = make_sheet_plan(state(MULTI_VIEW_IDS), sheet_size_mode='manual', sheet_width=1536, sheet_height=864)
    for bits in range(1, 1 << len(MULTI_VIEW_IDS)):
        payload = {'schema_version': 1, 'canvas': base['canvas'], 'views': [v for i, v in enumerate(base['views']) if bits & (1 << i)]}
        sheet = {**payload, 'plan_hash': plan_hash(payload)}
        assert validate_sheet_plan(sheet) == sheet


def test_only_generated_reference_labels_change_and_user_literals_stay_intact():
    cases = json.loads((Path(__file__).parent / 'fixtures/foot_reference_label_baseline.json').read_text(encoding='utf-8'))
    literal = 'Literal wording: footwear reference / footwear details.'
    for case in cases:
        after = compile_output_plan_v12(**case['options'])
        before = deepcopy(case['before'])
        for item in before['items']:
            prompt = item['prompt']
            sentinel = '__LITERAL_PART_WORDING__'
            prompt = prompt.replace(literal, sentinel)
            prompt = prompt.replace('footwear reference', 'foot appearance reference').replace('footwear details', 'foot appearance details')
            item['prompt'] = prompt.replace(sentinel, literal)
        assert after == before


def test_contain_size_keeps_full_image_with_one_pixel_rounding_tolerance():
    for box in ([0, 0, 1, 1], [11, 19, 251, 619], [0, 0, 640, 128]):
        for width, height in ((1, 20), (20, 1), (1184, 864), (768, 1344)):
            l, t, r, b = contain_bounds(box, width, height)
            assert box[0] <= l < r <= box[2] and box[1] <= t < b <= box[3]


@pytest.mark.parametrize('alpha', [0.0, 0.5, 1.0])
def test_rgba_is_composited_on_white_without_changing_source(alpha):
    sheet = plan(['feet'])
    images, records, root = inputs(sheet)
    rgb = images[0]
    rgba = torch.cat((rgb, torch.full_like(rgb[..., :1], alpha)), dim=-1)
    before = rgba.clone()
    output, raw = QwenImage21CharacterSheetAssemble().assemble([rgba], records, root)
    expected, _ = QwenImage21CharacterSheetAssemble().assemble([rgb * alpha + (1 - alpha)], records, root)
    assert torch.equal(output, expected)
    assert torch.equal(rgba, before)


def test_v13_defaults_match_v12_single_sheet_without_guide():
    assert V13.INPUT_TYPES()['optional']['batch_out'][1]['default'] is False
    assert V13.INPUT_TYPES()['optional']['use_layout_image'][1]['default'] is False
    image = torch.zeros(1, 32, 32, 3)
    old = V12().compile(DEFAULT_V12_STATE_JSON, character_image=image)
    new = V13().compile(DEFAULT_V12_STATE_JSON, character_image=image)
    assert new[:6] == old
    assert len(new[0]) == 1 and new[3] == [None] and new[7] == []


def test_standard_v13_workflow_has_one_save_for_both_modes_and_no_assembly_branch():
    from tools.workflow import validate_graph, api_prompt
    path = Path(__file__).parents[1] / 'workflows/QwenImage21_Character_Sheet_Designer_Reference_V13_template.json'
    graph = json.loads(path.read_text(encoding='utf-8'))
    validate_graph(graph)
    designer = next(node for node in graph['nodes'] if node['type'] == 'QwenImage21CharacterSheetDesignerReferenceV13')
    saves = [node for node in graph['nodes'] if node['type'] == 'SaveWebPMeta']
    assert len(saves) == 1 and saves[0]['widgets_values_named']['quality'] == 70
    assert designer['widgets_values_named']['batch_out'] is False
    assert not any(node['type'] == 'QwenImage21CharacterSheetAssemble' for node in graph['nodes'])
    for batch, count in [(False, 1), (True, 5)]:
        designer['widgets_values'][3] = batch
        designer['widgets_values_named']['batch_out'] = batch
        active = deepcopy(graph)
        for node in active['nodes']: node['mode'] = 0
        api = api_prompt(active)
        compiled = V13().compile(designer['widgets_values_named']['state_json'], character_image=torch.zeros(1, 32, 32, 3), batch_out=batch)
        assert len(compiled[0]) == count
        assert len(compiled[1]) == count and len(compiled[5]) == count
        assert compiled[3] == [None] * count
        assert sum(node['class_type'] == 'SaveWebPMeta' for node in api.values()) == 1
