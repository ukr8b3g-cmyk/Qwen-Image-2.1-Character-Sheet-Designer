import copy
import json
from pathlib import Path
import pytest
from qwen_image21_character_sheet.compiler import compile_state
from tools.workflow import validate_graph,api_prompt

ROOT=Path(__file__).resolve().parents[1]
PATHS=[p for p in (ROOT/"workflows").glob("*.json") if not p.name.endswith(".api.json")]


@pytest.mark.parametrize("path",PATHS)
def test_actual_saved_workflows(path):
    graph=json.loads(path.read_text());report=validate_graph(graph)
    assert (report["nodes"],report["links"])==(12,15)
    nodes={n["id"]:n for n in graph["nodes"]}
    assert set(nodes)=={4,15,20,477,478,479,480,481,482,484,485,495}
    assert not set(n["type"] for n in nodes.values())&{"TextGenerate","ComfySwitchNode","ResolutionSelector","H3CharacterSheetDesigner","SaveAnimatedWEBP"}
    prompt=api_prompt(graph)
    saved=json.loads(path.with_suffix('.api.json').read_text())
    assert prompt==saved
    assert prompt["485"]["inputs"]["prompt"]==["15",0]
    assert prompt["495"]["inputs"]["source"]==["15",0]
    assert prompt["480"]["inputs"]["width"]==["15",1]
    assert prompt["480"]["inputs"]["height"]==["15",2]
    assert prompt["482"]["inputs"]["latent_image"]==["480",0]
    assert prompt["485"]["inputs"]["images.image_1"]==["4",0]
    assert sum(k.startswith("images.") for k in prompt["485"]["inputs"])==1
    assert not nodes[485]["outputs"][2]["links"]
    assert prompt["485"]["inputs"]["resolution"]==1024
    assert prompt["482"]["inputs"]["steps"]==25
    assert prompt["482"]["inputs"]["cfg"]==1
    assert prompt["482"]["inputs"]["sampler_name"]=="euler"
    assert prompt["482"]["inputs"]["scheduler"]=="simple"
    raw=prompt["15"]["inputs"]["state_json"]
    assert nodes[15]["widgets_values"]==[raw]
    result=compile_state(raw)
    if "Comparison" in path.name:
        assert (result["width"],result["height"])==(1344,768)
        assert nodes[482]["widgets_values_named"]["control_after_generate"]=="fixed"
    else:
        state=json.loads(raw)
        assert state["views"]==["face_front","face_left","body_front","body_left","body_back"]
        assert state["size"]["body_height"]==1120
        assert (result["width"],result["height"])==(2816,1280)
    # Final prompt preview depends only on Designer, never on a PE or model branch.
    assert prompt["495"]["inputs"]=={"source":["15",0]}
    assert "models" in nodes[478]["properties"]  # supplied model metadata retained


def test_graph_checker_catches_broken_links():
    graph=json.loads(PATHS[0].read_text())
    bad=copy.deepcopy(graph);bad["links"][0][4]=10000
    with pytest.raises((ValueError,IndexError)):validate_graph(bad)
    bad=copy.deepcopy(graph);bad["nodes"][0]["outputs"][0]["links"].append(99999)
    with pytest.raises(ValueError):validate_graph(bad)
    bad=copy.deepcopy(graph);bad["links"].append(bad["links"][0])
    with pytest.raises(ValueError):validate_graph(bad)
