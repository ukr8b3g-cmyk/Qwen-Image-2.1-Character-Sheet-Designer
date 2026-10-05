import copy
import json
from pathlib import Path
import pytest
from qwen_image21_character_sheet.compiler import compile_state, DEFAULT_STATE_JSON, PRESETS
from tools.workflow import TEMPLATE_NAME, validate_graph, api_prompt, main as workflow_main

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "workflows" / TEMPLATE_NAME


def test_actual_saved_workflow():
    assert [path.name for path in (ROOT / "workflows").iterdir()] == [TEMPLATE.name]
    graph = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    report = validate_graph(graph)
    nodes = {n["id"]: n for n in graph["nodes"]}
    prompt = api_prompt(graph)
    by_type = {node["class_type"]: key for key, node in prompt.items()}
    assert not set(by_type) & {"TextGenerate", "ComfySwitchNode", "ResolutionSelector", "H3CharacterSheetDesigner", "SaveAnimatedWEBP"}
    encoder = prompt[by_type["TextEncodeQwenImage21"]]["inputs"]
    latent = prompt[by_type["EmptyLatentImage"]]["inputs"]
    sampler = prompt[by_type["KSampler"]]["inputs"]
    assert encoder["prompt"] == ["15", 0]
    assert prompt[by_type["PreviewAny"]]["inputs"] == {"source": ["15", 0]}
    assert latent["width"] == ["15", 1] and latent["height"] == ["15", 2]
    assert sampler["latent_image"] == [by_type["EmptyLatentImage"], 0]
    assert encoder["images.image_1"] == ["15", 3]
    assert encoder["images.image_2"] == ["4", 0]
    assert sum(k.startswith("images.") for k in encoder) == 2
    assert sampler["cfg"] == 1 and sampler["sampler_name"] == "euler" and sampler["scheduler"] == "simple"
    raw = prompt["15"]["inputs"]["state_json"]
    assert nodes[15]["widgets_values"] == [raw, True, "none"]
    assert nodes[15]["size"] == [870, 1100]
    assert prompt["15"]["inputs"]["use_layout_image"] is True
    assert prompt["15"]["inputs"]["style"] == "none"
    result = compile_state(raw)
    assert (report["nodes"], report["links"]) == (5, 6)
    assert sum(node["type"] == "MarkdownNote" for node in graph["nodes"]) == 1
    assert len(graph["definitions"]["subgraphs"]) == 1
    state = json.loads(raw)
    assert state["views"] == list(PRESETS["five"]) and state["size"]["body_height"] == 1120
    assert (result["width"], result["height"]) == (2816, 1280)
    assert sampler["steps"] == 30 and encoder["resolution"] == 1024
    assert prompt[by_type["UNETLoader"]]["inputs"]["unet_name"] == "qwen\\qwen_image_2.1_int8_convrot.safetensors"


def test_builder_outputs_only_standard_template(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["workflow.py", "--source", str(TEMPLATE), "--out", str(tmp_path)])
    workflow_main()
    assert [path.name for path in tmp_path.iterdir()] == [TEMPLATE.name]
    graph = json.loads((tmp_path / TEMPLATE.name).read_text(encoding="utf-8"))
    assert api_prompt(graph) == api_prompt(json.loads(TEMPLATE.read_text(encoding="utf-8")))


def test_default_state_matches_standard_five_views():
    state = json.loads(DEFAULT_STATE_JSON)
    assert state["views"] == list(PRESETS["five"])
    result = compile_state(DEFAULT_STATE_JSON)
    assert (result["width"], result["height"]) == (2816, 1280)


def test_graph_checker_catches_broken_links():
    graph = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    bad = copy.deepcopy(graph); bad["links"][0][4] = 10000
    with pytest.raises((ValueError, IndexError)): validate_graph(bad)
    bad = copy.deepcopy(graph); bad["nodes"][0]["outputs"][0]["links"].append(99999)
    with pytest.raises(ValueError): validate_graph(bad)
    bad = copy.deepcopy(graph); bad["links"].append(bad["links"][0])
    with pytest.raises(ValueError): validate_graph(bad)
    bad = copy.deepcopy(graph); bad["definitions"]["subgraphs"][0]["links"][0]["target_slot"] = 10000
    with pytest.raises((ValueError, IndexError)): validate_graph(bad)
