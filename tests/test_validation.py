import copy
import json
from pathlib import Path
import pytest
from qwen_image21_character_sheet import compiler as q
from tests.upstream import h3_compiler as h3

ROOT = Path(__file__).resolve().parents[1]


def error_code(raw, maximum=16384):
    with pytest.raises(q.StateValidationError) as exc:
        q.compile_state(raw, max_resolution=maximum)
    return exc.value.code


def test_shared_normalization_cases():
    cases = json.loads((ROOT / "tests/fixtures/state_cases.json").read_text())
    for case in cases:
        if case["valid"]:
            assert q.parse_state(case["raw"], max_resolution=case["max_resolution"]) == case["normalized"]
        else:
            assert error_code(case["raw"],case["max_resolution"]) == case["code"]
            with pytest.raises(h3.StateValidationError) as old:
                h3.compile_state(case["raw"],max_resolution=case["max_resolution"])
            assert old.value.code == case["code"]


@pytest.mark.parametrize("field", ["body_height","manual_width","manual_height"])
@pytest.mark.parametrize("value", [True, False, None, 32.0, "32", -32, 0, 31, 33, 16416])
def test_every_size_is_validated(field,value):
    s = copy.deepcopy(q.DEFAULT_STATE);s["size"][field] = value
    assert error_code(json.dumps(s))


def test_byte_boundaries_and_utf16():
    s = q.DEFAULT_STATE_JSON
    assert q.compile_state(s+" "*(q.STATE_MAX_BYTES-len(s)))["width"] > 0
    assert error_code(s+" "*(q.STATE_MAX_BYTES-len(s)+1)) == "state_too_large"
    state = json.loads(s);state.update(schema_version=2, part_prompts={"hands":"🧤"*500})
    assert q.parse_state(json.dumps(state))["part_prompts"]["hands"] == "🧤"*500
    state["part_prompts"]["hands"] += "x"
    assert error_code(json.dumps(state)) == "part_prompt_too_long"
    state["part_prompts"] = {"other":"\u3000\n\t\ufeff"}
    assert q.parse_state(json.dumps(state))["part_prompts"] == {}


def test_utf8_and_json_strictness():
    assert error_code(q.DEFAULT_STATE_JSON.replace('"schema_version":1','"schema_version":1,"schema_version":1')) == "duplicate_key"
    for bad in ("NaN", "Infinity", "-Infinity"):
        assert error_code(q.DEFAULT_STATE_JSON.replace('"body_height":1120', '"body_height":'+bad)) == "non_finite"
    state = json.loads(q.DEFAULT_STATE_JSON);state.update(schema_version=2,part_prompts={"other":"\ud800"})
    assert error_code(json.dumps(state)) == "invalid_utf8"
    assert error_code('\ud800') == "invalid_utf8"


def test_manual_mode_no_auto_shrink_or_mode_change():
    s = json.loads(q.DEFAULT_STATE_JSON);s["size"].update(mode="manual",manual_width=2240,manual_height=1280)
    for views in (["feet"],list(q.VIEW_IDS)):
        s["views"] = views
        result=q.compile_state(json.dumps(s))
        assert (result["width"],result["height"]) == (2240,1280)
        assert json.loads(result["state_json"])["size"]["mode"] == "manual"
    s["size"].update(mode="auto",body_height=16384)
    assert error_code(json.dumps(s)) == "size_limit"
