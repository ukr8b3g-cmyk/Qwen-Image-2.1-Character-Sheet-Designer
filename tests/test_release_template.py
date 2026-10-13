import json
from pathlib import Path

from tools.workflow import validate_graph

ROOT = Path(__file__).resolve().parents[1]


def test_reference_v12_template_named_images_and_paired_wiring():
    graph = json.loads((ROOT / 'workflows/QwenImage21_Character_Sheet_Designer_Reference_V12_template.json').read_text(encoding='utf-8'))
    report = validate_graph(graph)
    assert (report['nodes'], report['links']) == (8, 13)
    assert len(graph['definitions']['subgraphs']) == 1
    nodes = {node['id']: node for node in graph['nodes']}
    links = {row[0]: row for row in graph['links']}
    titles = {1: 'Character Image', 15: 'Reference Image 1', 16: 'Reference Image 2', 17: 'Reference Image 3'}
    designer = nodes[18]
    subgraph = graph['definitions']['subgraphs'][0]
    encoder = next(node for node in subgraph['nodes'] if node['type'] == 'TextEncodeQwenImage21')
    subgraph_node = nodes[20]
    assert designer['type'] == 'QwenImage21CharacterSheetDesignerReferenceV12'
    assert encoder['type'] == 'TextEncodeQwenImage21'
    for index, (node_id, title) in enumerate(titles.items()):
        assert nodes[node_id]['type'] == 'LoadImage'
        assert nodes[node_id]['title'] == title
        assert nodes[node_id]['mode'] == (0 if index == 0 else 4)
        designer_input = designer['inputs'][index]
        assert links[designer_input['link']][1:3] == [node_id, 0]
        encoder_input = next(item for item in subgraph_node['inputs'] if item['name'] == f'images.image_{index + 2}')
        assert links[encoder_input['link']][1:3] == [node_id, 0]
        inner_port = next(item for item in encoder['inputs'] if item['name'] == f'images.image_{index + 2}')
        inner_link = next(item for item in subgraph['links'] if item['id'] == inner_port['link'])
        assert inner_link['origin_id'] == subgraph['inputNode']['id']
        assert subgraph['inputs'][inner_link['origin_slot']]['name'] == f'images.image_{index + 2}'
    sampler = next(node for node in subgraph['nodes'] if node['type'] == 'KSampler')
    assert sampler['widgets_values'][2:] == [30, 1, 'euler', 'simple', 1]
    assert subgraph_node['widgets_values_named']['steps'] == 30
    assert subgraph_node['widgets_values_named']['cfg'] == 1
    assert designer['widgets_values'][1:] == [False, 'none', False]
    assert nodes[19]['type'] == 'SaveImageAdvanced'
    assert nodes[19]['widgets_values'] == ['qwen21_character_sheet_multi', 'png', '8-bit', 'sRGB']
