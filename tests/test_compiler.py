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
    b = (ROOT / "tests/upstream/h3_compiler.py").read_bytes().replace(b"\r\n", b"\n")
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
        assert q.compile_state(raw(state))["prompt"] == (ROOT / "tests/snapshots" / (name + ".qwen.txt")).read_text(encoding="utf-8")
        assert h3.compile_state(raw(state))["prompt"] == (ROOT / "tests/snapshots" / (name + ".h3.txt")).read_text(encoding="utf-8")


def test_concise_prompt_and_explicit_reference_roles():
    s=state_for(31);s["part_prompts"]={"upper_clothing":"青い絹のジャケット"}
    plain=q.compile_state(raw(s))
    guided=q.compile_state(raw(s),use_layout_image=True)
    assert guided["state_json"]==plain["state_json"]
    assert guided["layout"]==plain["layout"]
    assert "<image1>" in guided["prompt"] and "<image2>" in guided["prompt"]
    assert "<image1>" not in plain["prompt"] and "<image2>" not in plain["prompt"]
    for result in (plain,guided):
        prompt=result["prompt"]
        assert prompt.count("青い絹のジャケット")==1
        assert '"rect"' not in prompt and "normalized [left" not in prompt
        assert "chest-level cropped lower edge" in prompt and "Full-body front" in prompt
        assert "fully opaque, solid finished artwork" in prompt
        assert "\n" not in prompt
    assert "Edit <image1> in place" in guided["prompt"]
    assert "Preserve all black rectangular frames exactly as drawn" in guided["prompt"]
    assert "one rendering for each existing framed panel" in guided["prompt"]
    assert "matching top and bottom limits" not in guided["prompt"]
    assert "its corresponding gray bust" in guided["prompt"]


@pytest.mark.parametrize("bits", [1, 2, 3, 31, 127])
def test_guided_bust_crop_preserves_visible_template_extent(bits):
    s=state_for(bits);s["part_prompts"]={}
    prompt=q.compile_state(raw(s),use_layout_image=True)["prompt"]
    assert "visible size, viewing direction and crop fixed" in prompt
    assert "white space above and below" in prompt
    assert "full height of its column" not in prompt
    assert "matching top and bottom limits" not in prompt
    assert "\n" not in prompt
    if "face_front" in s["views"]:
        assert "nose centered between the eyes" in prompt
    if "face_left" in s["views"]:
        assert "nose pointing toward the right edge" in prompt


def test_guided_body_only_has_no_bust_crop_directive():
    s=state_for(28);s["part_prompts"]={}
    prompt=q.compile_state(raw(s),use_layout_image=True)["prompt"]
    assert "bust" not in prompt and "chest-level" not in prompt
    assert "full-body back" in prompt.lower()


def test_inapplicable_part_is_absent_from_final_prompt():
    s=state_for(1);s["part_prompts"]={"back_clothing":"背面だけの月模様"}
    assert "背面だけの月模様" not in q.compile_state(raw(s),use_layout_image=True)["prompt"]


@pytest.mark.parametrize("bits", range(1, 128))
@pytest.mark.parametrize("guided", [False, True])
def test_checked_views_only_and_separate_study_inventory(bits, guided):
    s = state_for(bits); s["part_prompts"] = {}
    result = q.compile_state(raw(s), use_layout_image=guided)
    prompt = result["prompt"]
    selected = s["views"]
    assert [p["id"] for p in result["layout"]["panels"]] == selected
    descriptions=q.GUIDED_VIEW_DETAILS.items() if guided else [(view,description) for view,(_,description) in q.VIEW_DETAILS.items()]
    for view, description in descriptions:
        assert (description in prompt) == (view in selected)
    inventory=f"Fill exactly {len(selected)} existing black-framed panels:" if guided else f"Compose exactly {len(selected)} distinct, unlabelled view panels:"
    assert inventory in prompt
    assert ("Preserve all black rectangular frames exactly as drawn" in prompt)==guided
    if guided and not any(view in q.BODY_IDS for view in selected):
        assert "standing figures" not in prompt
    groups = [
        (sum(v in ("face_front", "face_left") for v in selected), "enlarged head-and-shoulders bust stud"),
        (sum(v in ("body_front", "body_left", "body_back") for v in selected), "complete standing full-body figure"),
        (sum(v in ("hands", "feet") for v in selected), "isolated anatomical detail stud"),
    ]
    for count, label in groups:
        assert (f"{count} {label}" in prompt) == bool(count)
    assert "separate depictions of the same character" not in prompt
    if not guided:
        if groups[1][0] == 1:
            assert "Place the single" in prompt
            assert "matching head heights" not in prompt and "full-body columns" not in prompt
        if not groups[0][0]:
            assert "bust" not in prompt
        if not groups[2][0]:
            assert "detail studies in the leftmost" not in prompt


def test_detail_off_keeps_hands_and_shoes_on_full_body():
    s = state_for(4)
    s["part_prompts"] = {"hands": "青い手袋", "footwear": "黒いブーツ"}
    for guided in (False, True):
        result = q.compile_state(raw(s), use_layout_image=guided)
        assert "青い手袋" in result["prompt"] and "黒いブーツ" in result["prompt"]
        assert "Hand-detail study:" not in result["prompt"]
        assert "Foot-detail study:" not in result["prompt"]
        assert [p["id"] for p in result["layout"]["panels"]] == ["body_front"]
