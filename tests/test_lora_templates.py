"""Validate the external model-only LoRA route across subgraph boundaries."""
import copy
import json
from pathlib import Path

import pytest

from tools.workflow import api_prompt, validate_graph

ROOT = Path(__file__).resolve().parents[1]


def template(turbo):
    suffix = '_Turbo' if turbo else ''
    return json.loads((ROOT / ('workflows/QwenImage21_Character_Sheet_Designer_Reference_V13_template'+suffix+'.json')).read_text(encoding='utf-8'))


@pytest.mark.parametrize('turbo', [False, True])
def test_lora_is_between_loader_and_cache_with_independent_source(turbo):
    graph = template(turbo)
    report = validate_graph(graph)
    assert report['execution_order']
    lora = next(n for n in graph['nodes'] if n['type'] == 'Power Lora Loader (rgthree)')
    assert not any(isinstance(w, dict) and 'lora' in w for w in lora['widgets_values'])
    assert next(i for i in lora['inputs'] if i['name'] == 'clip')['link'] is None
    assert all(n['mode'] == 4 for n in graph['nodes'] if n.get('title', '').startswith('Reference Image'))
    active = copy.deepcopy(graph)
    for n in active['nodes']: n['mode'] = 0
    api = api_prompt(active)
    bytype = {n['class_type']: (key, n) for key, n in api.items()}
    loader_key, _ = bytype['UNETLoader']
    lora_key, lora_api = bytype['Power Lora Loader (rgthree)']
    cache_key, cache = bytype['QwenImage21Cache']
    assert lora_api['inputs']['model'] == [loader_key, 0]
    assert cache['inputs']['model'] == [lora_key, 0]
    consumer = bytype['CFGGuider' if turbo else 'KSampler'][1]
    assert consumer['inputs']['model'] == [cache_key, 0]
    assert bytype['QwenImage21CharacterSheetEncode'][1]['inputs']['clip'] == [bytype['CLIPLoader'][0], 0]


@pytest.mark.parametrize('turbo', [False, True])
def test_real_feedback_cycle_is_rejected_after_expansion(turbo):
    graph = template(turbo)
    definition = graph['definitions']['subgraphs'][0]
    output = definition['outputs'][1]
    link = next(l for l in definition['links'] if l['id'] == output['linkIds'][0])
    old = next(n for n in definition['nodes'] if n['id'] == link['origin_id'])
    old['outputs'][link['origin_slot']]['links'].remove(link['id'])
    cache = next(n for n in definition['nodes'] if n['type'] == 'QwenImage21Cache')
    link['origin_id'] = cache['id']
    link['origin_slot'] = 0
    cache['outputs'][0]['links'].append(link['id'])
    with pytest.raises(ValueError, match='Expanded workflow contains a cycle'):
        validate_graph(graph)


@pytest.mark.parametrize('turbo', [False, True])
def test_lora_port_disconnect_is_detected(turbo):
    graph = template(turbo)
    lora = next(n for n in graph['nodes'] if n['type'] == 'Power Lora Loader (rgthree)')
    lora['inputs'][0]['link'] = None
    with pytest.raises(ValueError, match='Asymmetric link references'):
        validate_graph(graph)
