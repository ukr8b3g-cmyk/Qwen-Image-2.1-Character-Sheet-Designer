"""Pure CPU tests. The pinned H3 source is a read-only regression oracle."""
import ast
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import pytest

from qwen_image21_character_sheet import compiler as q
from qwen_image21_character_sheet.common.geometry import compute_geometry
from qwen_image21_character_sheet.common.layout_serialization import layout_json
from tests.upstream import h3_compiler as h3

ROOT = Path(__file__).resolve().parents[1]
VIEWS = q.VIEW_IDS
CASES = [(bits, mode, version) for bits in range(1, 128) for mode in ("auto", "manual") for version in (1, 2)]
TOKENS = ("<Subject 1>", "<Picture 1>", "[Shot 1]", "subject_definitions", "retention_analysis", "overall_soundscape", "non_diegetic_music", "first frame", "last frame")


def state_for(bits=127, mode="auto", version=2):
    state = copy.deepcopy(q.DEFAULT_STATE)
    state["schema_version"] = version
    state["views"] = [v for i, v in enumerate(VIEWS) if bits & (1 << i)]
    state["size"]["mode"] = mode
    if version == 2:
        state["part_prompts"] = {part: f"{part}: 日本語 \n  raw 🧤" for part in q.PART_IDS}
    return state


def raw(state):
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"))


def test_oracle_is_pinned():
    b = (ROOT / "tests/upstream/h3_compiler.py").read_bytes()
    assert hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest() == "e74e778131a58d564ff55ced4ebd75df1a129111"


@pytest.mark.parametrize("bits,mode,version", CASES)
def test_all_layouts_state_and_h3_byte_parity(bits, mode, version):
    s = state_for(bits, mode, version)
    text = raw(s)
    old = h3.compile_state(text)
    new = q.compile_state(text)
    assert q.parse_state(text) == h3.parse_state(text)
    assert new["state_json"] == old["state_json"]
    assert q.compile_state(new["state_json"]) == new
    for key in ("width", "height", "pixel_count", "megapixels", "experimental", "max_resolution"):
        assert new[key] == old[key]
    geometry = compute_geometry(q.parse_state(text))
    assert geometry["canvas"] == old["layout"]["canvas"]
    assert geometry["feet_y"] == old["layout"]["feet_y"]
    assert geometry["panels"] == [{"id": p["id"], "rect": p["rect"]} for p in old["layout"]["panels"]]
    # Reattach unchanged H3 renderer to extracted geometry: no H3 prose rewrite.
    rebuilt = {**geometry, "panels": [
        {**p, "view": h3.VIEW_DETAILS[p["id"]][0], "content": h3._panel_content(s, p["id"])}
        for p in geometry["panels"]
    ]}
    assert layout_json(rebuilt).encode() == h3.layout_json(old["layout"]).encode()
    assert h3.compile_prompt(s, rebuilt).encode() == old["prompt"].encode()
    assert new["width"] % 32 == new["height"] % 32 == 0
    assert [p["id"] for p in new["layout"]["panels"]] == s["views"]
    for panel in new["layout"]["panels"]:
        x, y, w, h = panel["rect"]
        assert all(math.isfinite(n) for n in panel["rect"])
        assert x >= 0 and y >= 0 and w > 0 and h > 0 and x+w <= 1.000002 and y+h <= 1.000002
        assert not any(token in panel["content"] for token in TOKENS)
    for a, b in itertools.combinations(geometry["panels"], 2):
        ax, ay, aw, ah = a["rect"]; bx, by, bw, bh = b["rect"]
        assert min(ax+aw, bx+bw) - max(ax,bx) <= 0.000002 or min(ay+ah, by+bh) - max(ay,by) <= 0.000002
    bodies = [p for p in geometry["panels"] if p["id"] in q.BODY_IDS]
    if bodies:
        for panel in bodies:
            assert abs(sum(panel["rect"][i] for i in (1, 3)) - geometry["feet_y"]) <= 0.000002
    else:
        assert geometry["feet_y"] is None
    assert not any(token in new["prompt"] for token in TOKENS)
    assert new["prompt"].endswith("\n")


@pytest.mark.parametrize("height,preset,expected", [
    (672,"basic",(1344,768)), (672,"turnaround",(960,768)),
    (672,"detail",(1696,768)), (1120,"basic",(2208,1280)),
])
def test_known_sizes(height,preset,expected):
    s = copy.deepcopy(q.DEFAULT_STATE); s["size"]["body_height"] = height; s["views"] = list(q.PRESETS[preset])
    r = q.compile_state(raw(s))
    assert (r["width"],r["height"]) == expected


@pytest.mark.parametrize("height", [32,672,896,1120,1344,1792,4096])
def test_additional_scale_parity(height):
    for bits in (1, 2, 3, 4, 24, 31, 64, 96, 127):
        s = state_for(bits); s["size"]["body_height"] = height
        new = q.compile_state(raw(s)); old = h3.compile_state(raw(s))
        assert (new["width"], new["height"]) == (old["width"], old["height"])
        assert [p["rect"] for p in new["layout"]["panels"]] == [p["rect"] for p in old["layout"]["panels"]]


def test_part_application_and_preservation():
    s = state_for(127)
    s["part_prompts"] = {"back_clothing":"背中に <Subject 1>\n月🌙", "hands":"黒い革手袋", "footwear":"赤いロングブーツ"}
    r = q.compile_state(raw(s))
    panels = {p["id"]:p["content"] for p in r["layout"]["panels"]}
    for view in ("face_front","face_left","body_front","hands","feet"):
        assert "背中に" not in panels[view]
    for view in ("body_left","body_back"):
        assert s["part_prompts"]["back_clothing"] in panels[view]
    s["views"] = list(q.BODY_IDS)
    r = q.compile_state(raw(s))
    for p in r["layout"]["panels"]:
        assert "黒い革手袋" in p["content"] and "赤いロングブーツ" in p["content"]
    # A user-entered H3-looking token remains literal, not a generated section.
    assert "<Subject 1>" in r["prompt"]
    assert "back_clothing takes precedence over upper_clothing" in r["prompt"]


def test_no_irrelevant_preservation_conflicts():
    s = state_for(96); s["part_prompts"] = {"hands":"bare hands", "footwear":"bare feet"}
    r = q.compile_state(raw(s))
    assert "Preserve reference gloves" not in r["prompt"]
    assert "rather than replacing them with bare hands" not in r["prompt"]
    assert "rather than substituting bare feet" not in r["prompt"]
    assert [p["id"] for p in r["layout"]["panels"]] == ["hands","feet"]


@pytest.mark.parametrize("token", TOKENS)
def test_user_tokens_never_removed(token):
    s = state_for(4); text = f"  {token}\n日本語🧤  "; s["part_prompts"] = {"upper_clothing":text}
    r = q.compile_state(raw(s))
    assert text in r["prompt"] and text in r["layout"]["panels"][0]["content"]
    assert q.parse_state(r["state_json"])["part_prompts"]["upper_clothing"] == text


def test_no_runtime_h3_or_gpu_dependency():
    for path in (ROOT / "qwen_image21_character_sheet").rglob("*.py"):
        if path.name in ("node.py", "preview.py"):
            continue
        tree = ast.parse(path.read_text())
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                assert not any(a.name.split('.')[0] in ("torch", "comfy", "server", "requests", "aiohttp", "h3_character_sheet") for a in n.names)
    assert '"H3CharacterSheetDesigner"' not in (ROOT / "__init__.py").read_text()


def test_golden_snapshots():
    fixtures = json.loads((ROOT / "tests/fixtures/golden_states.json").read_text())
    for name, state in fixtures.items():
        assert q.compile_state(raw(state))["prompt"].encode() == (ROOT / "tests/snapshots" / (name + ".qwen.txt")).read_bytes()
        assert h3.compile_state(raw(state))["prompt"].encode() == (ROOT / "tests/snapshots" / (name + ".h3.txt")).read_bytes()
