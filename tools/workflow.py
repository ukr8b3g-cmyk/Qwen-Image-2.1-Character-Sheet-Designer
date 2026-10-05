"""Build and validate GUI workflows from the supplied saved graphs; no Comfy imports."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qwen_image21_character_sheet.compiler import compile_state

NODE_TYPE = "QwenImage21CharacterSheetDesigner"
QWEN_SOURCE_SHA256 = "cd738e78413f0ab03edc4822c2780cf7c9c62c343945f637d902daf8b59a12af"
H3_SOURCE_SHA256 = "ed15c3ab77107ce05909653ab41225b7fab422ae56d46455771179c46754fe22"


def validate_graph(graph: dict) -> dict:
    nodes = graph["nodes"]
    lookup = {n["id"]: n for n in nodes}
    if len(lookup) != len(nodes):
        raise ValueError("Duplicate node ID")
    links = {l[0]: l for l in graph["links"]}
    if len(links) != len(graph["links"]):
        raise ValueError("Duplicate link ID")
    targets = set()
    for link_id, origin, out_slot, target, in_slot, kind in graph["links"]:
        source = lookup[origin]["outputs"][out_slot]
        dest = lookup[target]["inputs"][in_slot]
        if (target, in_slot) in targets:
            raise ValueError("Multiple links to one input")
        targets.add((target, in_slot))
        if source["type"] != kind or dest["type"] not in (kind, "*"):
            raise ValueError("Incompatible link type")
        if link_id not in (source.get("links") or []) or dest.get("link") != link_id:
            raise ValueError("Asymmetric link references")
    for node in nodes:
        for i, inp in enumerate(node.get("inputs", [])):
            link_id = inp.get("link")
            if link_id is not None and (link_id not in links or links[link_id][3:5] != [node["id"], i]):
                raise ValueError("Dangling input link")
        for i, out in enumerate(node.get("outputs", [])):
            ids = out.get("links") or []
            if len(set(ids)) != len(ids):
                raise ValueError("Duplicate output link reference")
            for link_id in ids:
                if link_id not in links or links[link_id][1:3] != [node["id"], i]:
                    raise ValueError("Dangling output link")
    # Cycle check: do not rely on saved UI execution-order metadata.
    ancestors = {i: set() for i in lookup}
    for _, source, _, target, _, _ in graph["links"]:
        ancestors[target].add(source)
    pending = set(lookup)
    order = []
    while pending:
        ready = sorted(n for n in pending if not ancestors[n] & pending)
        if not ready:
            raise ValueError("Workflow contains a cycle")
        order.extend(ready); pending.difference_update(ready)
    return {"nodes": len(nodes), "links": len(links), "topological_order": order}


def api_prompt(graph: dict) -> dict:
    """Static export for this template, not a substitute for frontend graphToPrompt."""
    validate_graph(graph)
    result = {}
    links = {l[0]: l for l in graph["links"]}
    excluded = {"MarkdownNote"}
    ui_only = {"control_after_generate", "upload"}
    for node in graph["nodes"]:
        if node["type"] in excluded:
            continue
        if node.get("mode", 0) != 0:
            raise ValueError("Bypassed/muted nodes are not supported in this template exporter")
        inputs = {k: v for k, v in node.get("widgets_values_named", {}).items() if k not in ui_only}
        for inp in node.get("inputs", []):
            if inp.get("link") is not None:
                link = links[inp["link"]]
                inputs[inp["name"]] = [str(link[1]), link[2]]
        result[str(node["id"])] = {"class_type": node["type"], "inputs": inputs}
    return result


def build(qwen_source: Path, h3_source: Path) -> dict:
    qbytes, hbytes = qwen_source.read_bytes(), h3_source.read_bytes()
    if hashlib.sha256(qbytes).hexdigest() != QWEN_SOURCE_SHA256:
        raise ValueError("Qwen source differs from the verified supplied version")
    if hashlib.sha256(hbytes).hexdigest() != H3_SOURCE_SHA256:
        raise ValueError("H3 source differs from the verified supplied version (2)")
    q, h = json.loads(qbytes), json.loads(hbytes)
    validate_graph(q); validate_graph(h)
    qnodes = {n["id"]: n for n in q["nodes"]}
    hnodes = {n["id"]: n for n in h["nodes"]}
    nodes = [copy.deepcopy(qnodes[i]) for i in (477, 478, 479, 480, 481, 482, 484, 485, 495)]
    nodes.extend(copy.deepcopy(hnodes[i]) for i in (4, 15, 20))
    lookup = {n["id"]: n for n in nodes}
    for node in nodes:
        node["mode"] = 0
        node["flags"] = {}
        for inp in node.get("inputs", []):
            inp["link"] = None
        for out in node.get("outputs", []):
            out["links"] = []
    designer = lookup[15]
    designer["type"] = NODE_TYPE
    designer["properties"] = {"aux_id": "ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer", "Node name for S&R": NODE_TYPE}
    designer["outputs"].append({"name": "layout_image", "type": "IMAGE", "links": []})
    # Preserve the exact supplied five-view saved state, including inactive dimensions.
    state = designer["widgets_values"][0]
    if designer["widgets_values_named"]["state_json"] != state:
        raise ValueError("Conflicting saved Designer values")
    designer["widgets_values"] = [state, True]
    designer["widgets_values_named"]["use_layout_image"] = True
    designer["inputs"].append({"name": "use_layout_image", "type": "BOOLEAN", "widget": {"name": "use_layout_image"}, "link": None})
    compiled = compile_state(state)
    empty = lookup[480]
    empty["widgets_values"] = [compiled["width"], compiled["height"], 1]
    empty["widgets_values_named"] = {"width": compiled["width"], "height": compiled["height"], "batch_size": 1}
    # Layout canvas first, character appearance second; one image per input.
    lookup[485]["inputs"] = [i for i in lookup[485]["inputs"] if not i["name"].startswith("images.") or i["name"] == "images.image_1"]
    lookup[485]["inputs"].append({"name": "images.image_2", "type": "IMAGE", "link": None})
    lookup[485]["widgets_values"] = ["", "", 0]
    lookup[485]["widgets_values_named"] = {"prompt": "", "negative_prompt": "", "resolution": 0}
    preview = {"id": 496, "type": "PreviewImage", "size": [520, 300], "flags": {}, "order": 0, "mode": 0,
               "inputs": [{"name": "images", "type": "IMAGE", "link": None}], "outputs": [],
               "properties": {"cnr_id": "comfy-core", "Node name for S&R": "PreviewImage"}, "widgets_values": []}
    nodes.append(preview); lookup[496] = preview
    lookup[20]["widgets_values"][0] = "Qwen Image 2.1 Character Sheet Designer"
    lookup[20]["widgets_values_named"]["filename_prefix"] = lookup[20]["widgets_values"][0]
    # Keep the user's seed behavior in the main template; comparisons use a separate file.
    links = []
    def connect(source_id: int, out_name: str, target_id: int, in_name: str) -> None:
        source, dest = lookup[source_id], lookup[target_id]
        out_slot = next(i for i, p in enumerate(source["outputs"]) if p["name"] == out_name)
        in_slot = next(i for i, p in enumerate(dest["inputs"]) if p["name"] == in_name)
        if dest["inputs"][in_slot]["link"] is not None:
            raise ValueError("Attempt to overwrite input wiring")
        link_id = len(links) + 1
        kind = source["outputs"][out_slot]["type"]
        links.append([link_id, source_id, out_slot, target_id, in_slot, kind])
        source["outputs"][out_slot]["links"].append(link_id)
        dest["inputs"][in_slot]["link"] = link_id
    for edge in (
        (15, "prompt", 485, "prompt"), (15, "prompt", 495, "source"),
        (15, "width", 480, "width"), (15, "height", 480, "height"),
        (15, "layout_image", 485, "images.image_1"), (4, "IMAGE", 485, "images.image_2"),
        (15, "layout_image", 496, "images"), (478, "CLIP", 485, "clip"),
        (479, "VAE", 485, "vae"), (479, "VAE", 481, "vae"),
        (477, "MODEL", 484, "model"), (484, "MODEL", 482, "model"),
        (485, "positive", 482, "positive"), (485, "negative", 482, "negative"),
        (480, "LATENT", 482, "latent_image"), (482, "LATENT", 481, "samples"),
        (481, "IMAGE", 20, "images"),
    ):
        connect(*edge)
    positions = {15: [20, 80], 4: [930, 700], 477: [930, 80], 478: [930, 260], 479: [930, 440],
                 484: [1510, 80], 480: [1510, 250], 485: [1510, 430], 482: [2040, 80],
                 481: [2040, 650], 20: [2400, 80], 495: [2040, 780], 496: [930, 1370]}
    for n in nodes:
        n["pos"] = positions[n["id"]]
    graph = {"last_node_id": max(lookup), "last_link_id": len(links), "nodes": nodes, "links": links,
             "groups": [], "config": {}, "extra": {"ds": {"scale": 0.6, "offset": [30, 40]},
             "qwen21_designer": {"template_kind": "layout_and_character_reference", "source_state_preserved": True,
             "validation": "static_only; real ComfyUI and GPU validation required"}}, "version": 0.4}
    report = validate_graph(graph)
    for index, node_id in enumerate(report["topological_order"]):
        lookup[node_id]["order"] = index
    return graph


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--qwen", type=Path, required=True)
    p.add_argument("--h3", type=Path, required=True)
    p.add_argument("--out", type=Path, default=ROOT / "workflows")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    graph = build(args.qwen, args.h3)
    variants = {"QwenImage21_Character_Sheet_Designer.json": graph}
    compare = copy.deepcopy(graph)
    by_id = {n["id"]: n for n in compare["nodes"]}
    state = json.loads(by_id[15]["widgets_values"][0])
    state["views"] = ["face_front", "body_front", "body_left", "body_back"]
    state["size"] = {"mode": "manual", "body_height": 672, "manual_width": 1344, "manual_height": 768}
    raw = json.dumps(state, ensure_ascii=True, separators=(",", ":"))
    by_id[15]["widgets_values"] = [raw, True]
    by_id[15]["widgets_values_named"] = {"state_json": raw, "use_layout_image": True}
    by_id[480]["widgets_values"] = [1344, 768, 1]
    by_id[480]["widgets_values_named"].update(width=1344, height=768)
    by_id[482]["widgets_values"][1] = "fixed"
    by_id[482]["widgets_values_named"]["control_after_generate"] = "fixed"
    compare["extra"]["qwen21_designer"].update(template_kind="basic_four_view_comparison", source_state_preserved=False)
    variants["QwenImage21_Basic4_1344x768_Comparison.json"] = compare
    core = copy.deepcopy(graph)
    save = next(n for n in core["nodes"] if n["id"] == 20)
    save.update(type="SaveImage", outputs=[], widgets_values=["Qwen Image 2.1 Character Sheet Designer"],
                widgets_values_named={"filename_prefix": "Qwen Image 2.1 Character Sheet Designer"})
    save["properties"] = {"cnr_id": "comfy-core", "Node name for S&R": "SaveImage"}
    core["extra"]["qwen21_designer"]["template_kind"] = "layout_and_character_reference_core_saveimage"
    variants["QwenImage21_Character_Sheet_Designer_CoreSaveImage.json"] = core
    reports = {}
    for name, value in variants.items():
        reports[name] = validate_graph(value)
        (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.out / name.replace(".json", ".api.json")).write_text(json.dumps(api_prompt(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
