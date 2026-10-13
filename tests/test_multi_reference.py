import os
"""Multi Reference contract checks; image quality remains a separate GPU gate."""
import ast
import asyncio
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageOps
import pytest
import torch
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from qwen_image21_character_sheet import compiler as legacy
from qwen_image21_character_sheet import multi_reference_compiler as c
from qwen_image21_character_sheet import multi_reference_node as n
from qwen_image21_character_sheet import multi_preview as p
from qwen_image21_character_sheet import multi_layout_image as art
from qwen_image21_character_sheet.multi_guide_geometry import body_artwork_placements, panel_bounds, MIRRORED_VIEWS
from qwen_image21_character_sheet.reference_plan import build_reference_plan

ROOT = Path(__file__).resolve().parents[1]
PRESENT = {'character_image': True, 'reference_image_1': False, 'reference_image_2': False}


def state(views=None, height=448, **changes):
    result = copy.deepcopy(c.DEFAULT_MULTI_STATE)
    result['size']['body_height'] = height
    if views is not None:
        result['views'] = list(views)
    result.update(changes)
    return result


def raw(value):
    return json.dumps(value, ensure_ascii=True)


def test_all_8191_view_selections_are_ordered_bounded_and_nonoverlapping():
    for mask in range(1, 1 << len(c.MULTI_VIEW_IDS)):
        views = [v for i, v in enumerate(c.MULTI_VIEW_IDS) if mask & (1 << i)]
        layout = c.compute_multi_layout(state(views))
        assert [p['id'] for p in layout['panels']] == views
        assert all(v >= 32 and v % 32 == 0 for v in layout['canvas'])
        rects = [p['rect'] for p in layout['panels']]
        for x, y, w, h in rects:
            assert 0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0
            assert x + w <= 1.000002 and y + h <= 1.000002
        for i, (x, y, w, h) in enumerate(rects):
            for xx, yy, ww, hh in rects[i + 1:]:
                assert min(x + w, xx + ww) - max(x, xx) <= 0.000002 or min(y + h, yy + hh) - max(y, yy) <= 0.000002


def test_all_127_legacy_selections_keep_canvas_and_rects_in_auto_and_manual():
    for mask in range(1, 128):
        views = [v for i, v in enumerate(legacy.VIEW_IDS) if mask & (1 << i)]
        for mode in ('auto', 'manual'):
            value = state(views)
            value['size'].update(mode=mode, manual_width=896, manual_height=1184)
            before = legacy.compute_layout(value)
            after = c.compute_multi_layout(value)
            assert before['canvas'] == after['canvas']
            assert [p['rect'] for p in before['panels']] == [p['rect'] for p in after['panels']]


@pytest.mark.parametrize('views,height,expected', [
    (c.MULTI_PRESETS['five'], 1120, [2816, 1280]),
    (c.MULTI_VIEW_IDS, 1120, [4416, 1280]),
    (c.MULTI_PRESETS['five'], 448, [1152, 512]),
    (c.MULTI_VIEW_IDS, 448, [1760, 512]),
])
def test_approved_auto_dimensions(views, height, expected):
    assert c.compute_multi_layout(state(views, height))['canvas'] == expected


def test_preview_legacy_does_not_rewrite_saved_json_and_missing_character_still_has_layout():
    for value in (legacy.DEFAULT_STATE_JSON, raw({**legacy.DEFAULT_STATE, 'schema_version': 2, 'part_prompts': {}})):
        result = c.compile_multi_state(value)
        assert result['state_json'] == value and result['width'] == 2816
        assert result['prompt'] == '' and result['reference_plan'] == []
        assert result['notices'] == ['missing_character']
        assert c.parse_multi_state(value)['schema_version'] == 3


@pytest.mark.parametrize('layout,one,two', [(l, o, t) for l in (False, True) for o in (False, True) for t in (False, True)])
def test_eight_numbering_cases_use_actual_none_and_fixed_core_slots(layout, one, two):
    plan = build_reference_plan(object(), object() if one else None, object() if two else None, use_layout_image=layout)
    sources = (['layout_image'] if layout else []) + ['character_image'] + (['reference_image_1'] if one else []) + (['reference_image_2'] if two else [])
    assert [v['source'] for v in plan.references] == sources
    slots = {'layout_image': 1, 'character_image': 2, 'reference_image_1': 3, 'reference_image_2': 4}
    assert [v['core_input'] for v in plan.references] == [f'images.image_{slots[source]}' for source in sources]
    assert [v['tag'] for v in plan.references] == [f'<image{i}>' for i in range(1, len(sources) + 1)]
    presence = {'character_image': True, 'reference_image_1': one, 'reference_image_2': two}
    result = c.compile_multi_state(raw(state()), use_layout_image=layout, reference_presence=presence)
    assert result['reference_plan'] == list(plan.references)


def test_off_never_renders_or_tensorizes_and_accepts_core_batches_rgba(monkeypatch):
    monkeypatch.setitem(sys.modules, 'nodes', SimpleNamespace(MAX_RESOLUTION=16384))
    def forbidden(*args, **kwargs):
        raise AssertionError('OFF must not read guide artwork or allocate a guide tensor')
    monkeypatch.setattr(n, 'render_layout_image', forbidden)
    monkeypatch.setattr(n.np, 'asarray', forbidden)
    for image in (object(), torch.zeros((2, 32, 32, 4)), torch.zeros((1, 32, 32, 3))):
        output = n.QwenImage21CharacterSheetDesignerMultiReference().compile(raw(state()), image, reference_image_2=image)
        assert output[3] == [None] and output[1:3] == ([1152], [512])
        assert '<image2>' in output[0][0]
    with pytest.raises(c.StateValidationError) as error:
        n.QwenImage21CharacterSheetDesignerMultiReference().compile(raw(state()), None)
    assert error.value.code == 'missing_character'


def test_on_rgb_tensor_range_matches_png_and_missing_asset_has_clear_error(monkeypatch):
    monkeypatch.setitem(sys.modules, 'nodes', SimpleNamespace(MAX_RESOLUTION=16384))
    value = state(c.MULTI_PRESETS['head'])
    output = n.QwenImage21CharacterSheetDesignerMultiReference().compile(raw(value), object(), use_layout_image=True)
    guide = output[3][0]
    assert tuple(guide.shape) == (1, output[2][0], output[1][0], 3)
    assert guide.dtype == torch.float32 and 0 <= guide.min() <= guide.max() <= 1
    expected = np.asarray(art.render_layout_image(c.compute_multi_layout(value)), dtype=np.float32) / 255
    np.testing.assert_array_equal(guide[0].numpy(), expected)
    monkeypatch.setattr(art, 'ATLAS_PATH', ROOT / 'not-a-guide.png')
    with pytest.raises(c.StateValidationError) as error:
        n.QwenImage21CharacterSheetDesignerMultiReference().compile(raw(value), object(), use_layout_image=True)
    assert error.value.code == 'missing_guide_asset'


def test_clothing_garment_panels_are_blank_with_black_frames():
    value = state(c.CLOTHING_IDS, clothing_mode='garment')
    layout = c.compute_multi_layout(value)
    canvas = art.render_layout_image(layout, clothing_mode='garment')
    for panel in layout['panels']:
        left, top, right, bottom = panel_bounds(layout, panel)
        assert canvas.getpixel((left, top)) == (0, 0, 0)
        assert set(canvas.crop((left + 3, top + 3, right - 3, bottom - 3)).getdata()) == {(255, 255, 255)}


def test_body_baseline_and_width_fit_and_exact_one_mirror():
    layout = c.compute_multi_layout(state(c.MULTI_VIEW_IDS))
    placements = body_artwork_placements(layout)
    assert len({p['rect'][3] for p in placements.values()}) == 1
    assert len({p['rect'][1] + p['rect'][3] for p in placements.values()}) == 1
    for panel in layout['panels']:
        if panel['id'] not in placements:
            continue
        l, t, r, b = panel_bounds(layout, panel)
        x, y, w, h = placements[panel['id']]['rect']
        assert l <= x < x + w <= r and t <= y < y + h <= b
    assert MIRRORED_VIEWS == ('face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'body_left')
    # Pixel expectation from source artwork with one horizontal mirror.
    layout = c.compute_multi_layout(state(['face_left']))
    panel = layout['panels'][0]
    l, t, r, b = panel_bounds(layout, panel)
    with Image.open(art.ATLAS_PATH) as source:
        x, y, w, h = art.ATLAS_CROPS['face_left']
        cropped = ImageOps.mirror(source.convert('RGBA').crop((x, y, x + w, y + h)))
    cropped = ImageOps.contain(cropped, (r - l, b - t), Image.Resampling.LANCZOS)
    expected = Image.new('RGB', tuple(layout['canvas']), 'white')
    expected.paste(cropped, (l + (r - l - cropped.width) // 2, t + (b - t - cropped.height) // 2), cropped)
    actual = art.render_layout_image(layout)
    inset = 4
    assert np.array_equal(np.asarray(actual.crop((l + inset, t + inset, r - inset, b - inset))), np.asarray(expected.crop((l + inset, t + inset, r - inset, b - inset))))


def test_scopes_priorities_and_literal_text_do_not_leak_h3_grammar():
    text = '胸に星\n  正面だけ "ORBIT"  '
    value = state(c.MULTI_VIEW_IDS, part_prompts={'upper_clothing': text, 'hands': 'red rings; keep gloves'}, hand_state='bare', clothing_mode='garment')
    value['reference_roles'] = {'reference_image_1': 'clothing_back', 'reference_image_2': 'face'}
    result = c.compile_multi_state(raw(value), use_layout_image=True, style='watercolor', reference_presence=dict.fromkeys(PRESENT, True))
    prompt = result['prompt']
    assert text in prompt and 'all visible hands are bare skin' in prompt
    assert 'back_clothing takes precedence over upper_clothing' in prompt
    assert 'face-only reference takes precedence over a head reference' in prompt
    assert '<image3>' in prompt and '<image4>' in prompt
    assert 'No head, neck, arms, hands, legs' in prompt and 'Change only rendering technique' in prompt
    for word in ('Picture', '<Subject', '<Shot', 'subject_definitions:', 'retention_analysis:', 'audio', 'music', '"rect":'):
        assert word not in prompt
    assert 'LEFT edge' in c.panel_details(value, 'face_left')[1]
    assert 'RIGHT edge' in c.panel_details(value, 'face_right')[1]
    assert 'body_back' not in c.role_views(value, 'face')
    assert 'clothing_back' not in c.role_views(value, 'hands')
    value['clothing_mode'] = 'worn'
    assert 'clothing_back' in c.role_views(value, 'hands')
    value = state(['face_back'])
    value['reference_roles']['reference_image_2'] = 'face'
    unused = c.compile_multi_state(raw(value), reference_presence={**PRESENT, 'reference_image_2': True})
    assert '<image2>' not in unused['prompt']


def test_state_limits_and_preview_strict_envelope():
    value = state(c.MULTI_VIEW_IDS)
    del value['hand_state']; del value['clothing_mode']
    parsed = c.parse_multi_state(raw(value))
    assert parsed['hand_state'] == 'reference' and parsed['clothing_mode'] == 'worn'
    for body, code in [
        (b'{}', 'invalid_request'), (b'\xff', 'invalid_utf8'),
        (json.dumps({'state_json': raw(value), 'reference_presence': {'character_image': 1}}).encode(), 'invalid_type'),
        (json.dumps({'state_json': raw(value), 'reference_presence': {'path': 'x'}}).encode(), 'invalid_request'),
        (json.dumps({'state_json': raw(value), 'reference_presence': None}).encode(), 'invalid_type'),
        (b' ' * (p.HTTP_MAX_BYTES + 1), 'request_too_large'),
    ]:
        with pytest.raises(c.StateValidationError) as error:
            p.compile_preview_request(body, max_resolution=16384)
        assert error.value.code == code
    for field, bad in [('hand_state', 'x'), ('clothing_mode', True), ('views', []), ('reference_roles', {})]:
        with pytest.raises(c.StateValidationError):
            c.parse_multi_state(raw(state(**{field: bad})))


def test_multi_http_and_route_registration_are_independent(monkeypatch):
    monkeypatch.setattr(p, 'runtime_max_resolution', lambda: 16384)
    async def checks():
        app = web.Application(client_max_size=p.HTTP_MAX_BYTES + 4096)
        app.router.add_post(p.PREVIEW_PATH, p.preview)
        async with TestClient(TestServer(app)) as client:
            body = {'state_json': raw(state()), 'reference_presence': PRESENT}
            response = await client.post(p.PREVIEW_PATH, json=body)
            assert response.status == 200
            result = await response.json()
            assert result.pop('batch_plan') == c.compile_output_plan(body['state_json'], reference_presence=PRESENT)
            assert result == c.compile_multi_state(body['state_json'], reference_presence=PRESENT)
            response = await client.post(p.PREVIEW_PATH, data='{}', headers={'Content-Type': 'text/plain'})
            assert response.status == 415
            monkeypatch.setattr(p, 'runtime_max_resolution', lambda: (_ for _ in ()).throw(RuntimeError('PRIVATE')))
            response = await client.post(p.PREVIEW_PATH, json=body)
            assert response.status == 500 and 'PRIVATE' not in await response.text()
    asyncio.run(checks())
    calls = []
    instance = SimpleNamespace(routes=SimpleNamespace(post=lambda path: lambda handler: calls.append(path)), _qwen_image21_character_sheet_designer_route_registered=True)
    monkeypatch.setitem(sys.modules, 'server', SimpleNamespace(PromptServer=SimpleNamespace(instance=instance)))
    assert p.register_routes() and p.register_routes()
    assert calls == [p.PREVIEW_PATH] and instance._qwen_image21_character_sheet_designer_route_registered


def test_legacy_modules_and_all_new_assets_match_pinned_source_baseline():
    baseline = json.loads((ROOT / 'tests/fixtures/public_source_contract.json').read_text(encoding='utf-8'))
    protected = ('qwen_image21_character_sheet/', 'web/', 'workflows/')
    for row in baseline['files']:
        if row['group'] == 'qwen' and row['path'].startswith(protected):
            assert hashlib.sha256((ROOT / row['path']).read_bytes().replace(b'\r\n', b'\n') if row['text'] else (ROOT / row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
    for row in baseline['files']:
        name = Path(row['path']).name
        dest = ROOT / 'web/assets/multi_reference' / name
        if row['group'] == 'h3' and dest.is_file():
            assert hashlib.sha256(dest.read_bytes()).hexdigest() == row['sha256']


@pytest.mark.parametrize('use_layout,one,two,three', [(l, o, t, h) for l in (False, True) for o in (False, True) for t in (False, True) for h in (False, True)])
def test_actual_installed_core_encoder_compacts_none_preserves_input_order_and_first_batch(use_layout, one, two, three):
    """Execute the installed method body with CPU clip/VAE test doubles."""
    core_root = os.environ.get('QWEN_SHEET_TEST_COMFYUI_ROOT')
    if not core_root:
        pytest.skip('Set QWEN_SHEET_TEST_COMFYUI_ROOT for installed Core interoperability checks')
    core = Path(core_root) / 'comfy_extras/nodes_qwen.py'
    if not core.exists():
        pytest.skip('Installed Core source is not available on this host')
    text = core.read_text(encoding='utf-8')
    tree = ast.parse(text)
    original = next(v for v in tree.body if isinstance(v, ast.ClassDef) and v.name == 'TextEncodeQwenImage21')
    execute = next(v for v in original.body if isinstance(v, ast.FunctionDef) and v.name == 'execute')
    cls = ast.ClassDef(name='ActualCoreEncoder', bases=[], keywords=[], body=[execute], decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    recorded, vae_recorded = [], []
    clip = SimpleNamespace(tokenize=lambda prompt, **kw: recorded.append((prompt, kw)) or prompt,
                           encode_from_tokens_scheduled=lambda tokens: [[torch.zeros(1), {}]])
    vae = SimpleNamespace(encode=lambda image: vae_recorded.append(image) or image)
    def add_values(conditioning, values, append=False):
        return [[entry[0], {**entry[1], **values}] for entry in conditioning]
    namespace = {'torch': torch, 'math': math,
                 'io': SimpleNamespace(Autogrow=SimpleNamespace(Type=dict), NodeOutput=lambda *args: args),
                 'comfy': SimpleNamespace(model_management=SimpleNamespace(intermediate_device=lambda: 'cpu')),
                 'node_helpers': SimpleNamespace(conditioning_set_values=add_values)}
    exec(compile(module, str(core), 'exec'), namespace)
    def color(index, rgba=False, batch=1):
        image = torch.full((batch, 32, 32, 4 if rgba else 3), index / 10)
        if rgba:
            image[..., 3] = 1
        if batch > 1:
            image[1] = 0.9
        return image
    images = {'image_5': color(5) if three else None, 'image_4': color(4) if two else None, 'image_2': color(2, rgba=True, batch=2),
              'image_1': color(1) if use_layout else None, 'image_3': color(3) if one else None}
    result = c.compile_multi_state(raw(state()), use_layout_image=use_layout, reference_presence={'character_image': True, 'reference_image_1': one, 'reference_image_2': two, 'reference_image_3': three})
    positive, negative, latent = namespace['ActualCoreEncoder'].execute(clip, result['prompt'], '', vae=vae, resolution=0, images=images)
    expected = ([1] if use_layout else []) + [2] + ([3] if one else []) + ([4] if two else []) + ([5] if three else [])
    assert [round(v[0, 0, 0, 0].item() * 10) for v in recorded[0][1]['images']] == expected
    assert len(vae_recorded) == len(result['reference_plan']) == len(expected)
    assert all(v.shape[0] == 1 for v in vae_recorded)
    assert any(v.shape[-1] == 4 for v in vae_recorded)
    assert len(positive[0][1]['reference_latents']) == len(expected)
    assert latent['samples'].shape == (1, 64, 2, 2)
