"""Build and validate the supplied GUI workflow template; no Comfy imports."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NODE_TYPE = "QwenImage21CharacterSheetDesigner"
TEMPLATE_NAME = "QwenImage21_Character_Sheet_Designer_wf.json"


def link_rows(graph: dict) -> list:
    return [[link[k] for k in ("id", "origin_id", "origin_slot", "target_id", "target_slot", "type")]
            if isinstance(link, dict) else link for link in graph["links"]]


def validate_scope(graph: dict) -> dict:
    nodes = graph["nodes"]
    lookup = {n["id"]: n for n in nodes}
    if len(lookup) != len(nodes):
        raise ValueError("Duplicate node ID")
    links = {l[0]: l for l in link_rows(graph)}
    if len(links) != len(graph["links"]):
        raise ValueError("Duplicate link ID")
    targets = set()
    for link_id, origin, out_slot, target, in_slot, kind in link_rows(graph):
        source = lookup[origin]["outputs"][out_slot]
        dest = lookup[target]["inputs"][in_slot]
        if (target, in_slot) in targets:
            raise ValueError("Multiple links to one input")
        targets.add((target, in_slot))
        if (kind != "*" and source["type"] not in (kind, "*")) or (kind != "*" and dest["type"] not in (kind, "*")):
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
    for _, source, _, target, _, _ in link_rows(graph):
        ancestors[target].add(source)
    pending = set(lookup)
    order = []
    while pending:
        ready = sorted(n for n in pending if not ancestors[n] & pending)
        if not ready:
            raise ValueError("Workflow contains a cycle")
        order.extend(ready); pending.difference_update(ready)
    return {"nodes": len(nodes), "links": len(links), "topological_order": order}


def validate_graph(graph: dict) -> dict:
    report = validate_scope(graph)
    subgraphs = graph.get("definitions", {}).get("subgraphs", [])
    definitions = {item["id"]: item for item in subgraphs}
    if len(definitions) != len(subgraphs):
        raise ValueError("Duplicate subgraph ID")
    for definition in subgraphs:
        scope = copy.deepcopy(definition)
        scope["nodes"].extend([
            {"id": definition["inputNode"]["id"], "inputs": [],
             "outputs": [{"type": port["type"], "links": port["linkIds"]} for port in definition["inputs"]]},
            {"id": definition["outputNode"]["id"], "outputs": [],
             "inputs": [{"type": port["type"], "link": port["linkIds"][0]} for port in definition["outputs"]]},
        ])
        validate_scope(scope)
    if subgraphs:
        report["subgraphs"] = {item["id"]: {"nodes": len(item["nodes"]), "links": len(item["links"])} for item in subgraphs}
    return report


def api_prompt(graph: dict) -> dict:
    """Static export of these flat or single-level subgraph templates."""
    validate_graph(graph)
    nodes = {node["id"]: node for node in graph["nodes"]}
    links = {row[0]: row for row in link_rows(graph)}
    definitions = {item["id"]: item for item in graph.get("definitions", {}).get("subgraphs", [])}
    result = {}
    ui_only = {"control_after_generate", "upload"}

    def root_output(node_id, slot):
        node = nodes[node_id]
        if node["type"] not in definitions:
            return [str(node_id), slot]
        definition = definitions[node["type"]]
        output = definition["outputs"][slot]
        source = next(row for row in link_rows(definition) if row[0] == output["linkIds"][0])
        return [f"{node_id}:{source[1]}", source[2]]

    def inputs_for(node, scope_links, resolve):
        if node.get("mode", 0) != 0:
            raise ValueError("Bypassed/muted nodes are not supported in this template exporter")
        inputs = {k: v for k, v in node.get("widgets_values_named", {}).items() if k not in ui_only}
        for inp in node.get("inputs", []):
            if inp.get("link") is not None:
                row = scope_links[inp["link"]]
                inputs[inp["name"]] = resolve(row[1], row[2])
        return inputs

    for node_id, node in nodes.items():
        if node["type"] == "MarkdownNote":
            continue
        if node["type"] not in definitions:
            result[str(node_id)] = {"class_type": node["type"], "inputs": inputs_for(node, links, root_output)}
            continue
        definition = definitions[node["type"]]
        external = inputs_for(node, links, root_output)
        inner_links = {row[0]: row for row in link_rows(definition)}

        def inner_output(origin, slot):
            if origin == definition["inputNode"]["id"]:
                return external[definition["inputs"][slot]["name"]]
            return [f"{node_id}:{origin}", slot]

        for child in definition["nodes"]:
            if child["type"] in definitions:
                raise ValueError("Nested subgraphs are not supported in this template exporter")
            result[f"{node_id}:{child['id']}"] = {"class_type": child["type"], "inputs": inputs_for(child, inner_links, inner_output)}
    return result


def build(source: Path) -> dict:
    """Keep the supplied subgraph, loaders and generation settings."""
    payload = source.read_bytes()
    graph = json.loads(payload)
    validate_graph(graph)
    designer = next(node for node in graph["nodes"] if node["type"] == NODE_TYPE)
    state = designer["widgets_values"][0]
    if state != designer["widgets_values_named"]["state_json"]:
        raise ValueError("Conflicting saved Designer values")
    designer["widgets_values"] = [state, True, "none"]
    designer["widgets_values_named"].update(use_layout_image=True, style="none")
    designer["size"] = [870, 1100]
    # The compiler assigns image_1 to layout and image_2 to character appearance.
    nodes = {node["id"]: node for node in graph["nodes"]}
    guide = next(row for row in graph["links"] if row[1:3] == [designer["id"], 3])
    character = next(row for row in graph["links"] if nodes[row[1]]["type"] == "LoadImage")
    for row, output_name in ((guide, "images.image_1"), (character, "images.image_2")):
        target = next(node for node in graph["nodes"] if node["id"] == row[3])
        index = next(i for i, port in enumerate(target["inputs"]) if port["name"] == output_name)
        row[4] = index
        target["inputs"][index]["link"] = row[0]
    graph["extra"]["qwen21_designer"].update(
        template_kind="standard_five_view", source_state_preserved=True,
        source_sha256=hashlib.sha256(payload).hexdigest())
    validate_graph(graph)
    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "workflows")
    args = parser.parse_args()
    graph = build(args.source)
    args.out.mkdir(parents=True, exist_ok=True)
    name = TEMPLATE_NAME
    (args.out / name).write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: validate_graph(graph)}, indent=2))


if __name__ == "__main__":
    main()
