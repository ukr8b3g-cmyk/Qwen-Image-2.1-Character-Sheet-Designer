import importlib
import itertools
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from qwen_image21_character_sheet import multi_reference_compiler as compiler
from qwen_image21_character_sheet import multi_reference_node as node
from qwen_image21_character_sheet.reference_plan import build_reference_plan, REFERENCE_ROLES


@pytest.mark.parametrize('guide,flags', itertools.product((False, True), itertools.product((False, True), repeat=3)))
def test_third_reference_slots_and_compact_numbers_match_preview(guide, flags):
    plan = build_reference_plan(object(), *(object() if connected else None for connected in flags), use_layout_image=guide)
    sources = (['layout_image'] if guide else []) + ['character_image']
    sources += [f'reference_image_{index}' for index, connected in enumerate(flags, 1) if connected]
    slots = {'layout_image': 1, 'character_image': 2, 'reference_image_1': 3, 'reference_image_2': 4, 'reference_image_3': 5}
    assert [ref['source'] for ref in plan.references] == sources
    assert [ref['core_input'] for ref in plan.references] == [f'images.image_{slots[source]}' for source in sources]
    assert [ref['tag'] for ref in plan.references] == [f'<image{i}>' for i in range(1, len(sources) + 1)]
    presence = {'character_image': True, **{f'reference_image_{i}': value for i, value in enumerate(flags, 1)}}
    result = compiler.compile_multi_state(compiler.DEFAULT_MULTI_STATE_JSON, use_layout_image=guide, reference_presence=presence)
    assert result['reference_plan'] == list(plan.references)


def test_old_two_reference_state_is_loaded_without_rewriting_its_raw_json():
    state = json.loads(compiler.DEFAULT_MULTI_STATE_JSON)
    state['reference_roles'].pop('reference_image_3')
    state['reference_roles']['reference_image_2'] = 'clothing_back'
    raw = json.dumps(state)
    result = compiler.compile_multi_state(raw)
    assert result['state_json'] == raw
    migrated = compiler.parse_multi_state(raw)
    assert migrated['reference_roles'] == {**state['reference_roles'], 'reference_image_3': 'same_character'}
    assert migrated['size'] == state['size'] and migrated['views'] == state['views']


@pytest.mark.parametrize('role', REFERENCE_ROLES)
def test_third_reference_role_reaches_every_applicable_batch_prompt(role, monkeypatch):
    monkeypatch.setitem(sys.modules, 'nodes', SimpleNamespace(MAX_RESOLUTION=16384))
    state = json.loads(compiler.DEFAULT_MULTI_STATE_JSON)
    state['views'] = list(compiler.MULTI_VIEW_IDS)
    state['reference_roles']['reference_image_3'] = role
    raw = json.dumps(state)
    result = node.QwenImage21CharacterSheetDesignerMultiReference().compile(raw, object(), batch_out=True, reference_image_3=object())
    assert len(result[0]) == 13 and result[3] == [None] * 13
    for view, prompt in zip(compiler.MULTI_VIEW_IDS, result[0]):
        applicable = role == 'same_character' or view in compiler.role_views(state, role)
        assert (f'<image2> is an additional {role} reference.' in prompt) == applicable
        assert '<image3>' not in prompt


@pytest.mark.parametrize('role', (None, False, 'unknown'))
def test_invalid_third_role_is_rejected(role):
    state = json.loads(compiler.DEFAULT_MULTI_STATE_JSON)
    state['reference_roles']['reference_image_3'] = role
    with pytest.raises(compiler.StateValidationError):
        compiler.parse_multi_state(json.dumps(state))


def test_two_reference_prompts_and_geometry_are_unchanged_from_snapshot():
    # This local regression compares the user's previous runtime, not Git HEAD.
    record = Path(__file__).resolve().parents[2] / 'before.json'
    if not record.exists():
        pytest.skip('Pre-change local snapshot is unavailable')
    root = Path(json.loads(record.read_text())['snapshot']) / 'qwen_image21_character_sheet'
    package = ModuleType('qwen_before_reference3')
    package.__path__ = [str(root)]
    sys.modules[package.__name__] = package
    old = importlib.import_module(package.__name__ + '.multi_reference_compiler')
    raw = old.DEFAULT_MULTI_STATE_JSON
    for guide, one, two in itertools.product((False, True), repeat=3):
        presence = {'character_image': True, 'reference_image_1': one, 'reference_image_2': two}
        expected = old.compile_multi_state(raw, use_layout_image=guide, reference_presence=presence)
        assert compiler.compile_multi_state(raw, use_layout_image=guide, reference_presence=presence) == expected
