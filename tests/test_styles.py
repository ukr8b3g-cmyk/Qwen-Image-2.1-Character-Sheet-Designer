import json
import sys
from types import SimpleNamespace

import pytest

from qwen_image21_character_sheet import compiler as q
from qwen_image21_character_sheet import node as n
from qwen_image21_character_sheet import preview as p


@pytest.mark.parametrize("style", list(q.STYLE_PROMPTS))
@pytest.mark.parametrize("guided", [False, True])
def test_style_changes_rendering_only_and_keeps_part_directives(style, guided):
    state = json.loads(q.DEFAULT_STATE_JSON)
    state.update(schema_version=2, part_prompts={"upper_clothing": "青いコート\n  柄は参照のまま"})
    raw = json.dumps(state, ensure_ascii=False)
    baseline = q.compile_state(raw, use_layout_image=guided)
    result = q.compile_state(raw, use_layout_image=guided, style=style)
    assert {key: value for key, value in result.items() if key != "prompt"} == {key: value for key, value in baseline.items() if key != "prompt"}
    assert state["part_prompts"]["upper_clothing"] in result["prompt"]
    assert "studio photography" not in result["prompt"]
    assert "character concept art" not in result["prompt"]
    assert "anime-inspired facial features" not in result["prompt"]
    if style == "none":
        assert result == baseline
        assert "Change only the character's rendering style" not in result["prompt"]
    else:
        assert result["prompt"].count(q.STYLE_PROMPTS[style]) == 1
        assert "and rendering medium" not in result["prompt"]
        assert "existing accessories, colors and patterns" in result["prompt"]
        assert "except for explicit part directives below" in result["prompt"]
        assert "Use the reference only for the character" in result["prompt"]
    if guided:
        assert "Preserve all black rectangular frames exactly as drawn" in result["prompt"]
        if style != "none":
            assert "colors and patterns from <image2>" in result["prompt"]


@pytest.mark.parametrize("style", list(q.STYLE_PROMPTS))
@pytest.mark.parametrize("guided", [False, True])
def test_style_preview_and_node_queue_output_match(style, guided, monkeypatch):
    monkeypatch.setitem(sys.modules, "nodes", SimpleNamespace(MAX_RESOLUTION=16384))
    state = json.loads(q.DEFAULT_STATE_JSON)
    state["size"].update(mode="manual", manual_width=320, manual_height=192)
    raw = json.dumps(state)
    envelope = {"state_json": raw, "use_layout_image": guided, "style": style}
    result = p.compile_preview_request(json.dumps(envelope).encode(), max_resolution=16384)
    output = n.QwenImage21CharacterSheetDesigner().compile(raw, guided, style)
    assert output[:3] == (result["prompt"], result["width"], result["height"])
    assert tuple(output[3].shape) == (1, 192, 320, 3)
    assert n.QwenImage21CharacterSheetDesigner.VALIDATE_INPUTS(raw, guided, style) is True


@pytest.mark.parametrize("style", [None, True, 1, [], {}, "anime; add jewelry"])
def test_invalid_style_is_rejected_without_prompt_injection(style):
    with pytest.raises(q.StateValidationError) as exc:
        q.compile_state(q.DEFAULT_STATE_JSON, style=style)
    assert exc.value.code == "unknown_style"
    with pytest.raises(q.StateValidationError):
        p.compile_preview_request(json.dumps({"state_json": q.DEFAULT_STATE_JSON, "style": style}).encode(), max_resolution=16384)


def test_style_is_optional_and_defaults_to_none():
    specification = n.QwenImage21CharacterSheetDesigner.INPUT_TYPES()
    assert specification["optional"]["style"][0] == list(q.STYLE_PROMPTS)
    assert specification["optional"]["style"][1]["default"] == "none"
