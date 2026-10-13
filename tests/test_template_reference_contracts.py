"""Routing regressions; direct-route failures are documented, not silently fixed."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from qwen_image21_character_sheet.multi_reference_compiler import DEFAULT_MULTI_STATE
from qwen_image21_character_sheet.reference_v12_compiler import compile_output_plan_v12
from qwen_image21_character_sheet import sheet_encode
from tools.workflow import validate_graph, api_prompt

ROOT=Path(__file__).resolve().parents[1]
DIRECT='QwenImage21_Character_Sheet_Designer_Reference_V12_template.json'
SHEET='QwenImage21_Character_Sheet_Designer_Reference_V12_Sheet_Encode_template.json'
SOURCES=('character_image','reference_image_1','reference_image_2','reference_image_3')

def output(views, roles, presence, guide, batch=False):
    state=deepcopy(DEFAULT_MULTI_STATE)
    state['views']=views
    state['reference_roles'].update(roles)
    return compile_output_plan_v12(json.dumps(state), reference_presence=presence,
        use_layout_image=guide, batch_out=batch)['items']

def encoded_sources(item, presence, guide, monkeypatch):
    sent=[]
    monkeypatch.setattr(sheet_encode,'TextEncodeQwenImage21',SimpleNamespace(execute=lambda **kw:
        (sent.append(kw) or SimpleNamespace(result=('positive','negative',None)))))
    images={s:s if presence.get(s) else None for s in SOURCES}
    images['layout_image']='layout_image' if guide else None
    sheet_encode.QwenImage21CharacterSheetEncode().encode('clip',item['prompt'],'',item['reference_plan_json'],**images)
    expected=[e['source'] for e in item['reference_plan']]
    assert list(sent[0]['images'].values())==expected
    assert list(sent[0]['images'])==['image_'+str(i) for i in range(1,len(expected)+1)]
    direct=([images['layout_image']] if guide else [])+[images[s] for s in SOURCES if images[s] is not None]
    return expected,direct

@pytest.mark.parametrize('guide,mask',itertools.product((False,True),range(8)))
def test_standard_same_character_direct_control(guide,mask,monkeypatch):
    presence={'character_image':True,**{s:bool(mask&(1<<i)) for i,s in enumerate(SOURCES[1:])}}
    item=output(['face_front','body_front','body_back'],{},presence,guide)[0]
    expected,direct=encoded_sources(item,presence,guide,monkeypatch)
    assert expected==direct

@pytest.mark.parametrize('guide,batch',itertools.product((False,True),repeat=2))
@pytest.mark.parametrize('views,roles',[
    (['feet'],{'reference_image_1':'footwear'}),
    (['face_front'],{'reference_image_1':'footwear','reference_image_2':'face'}),
    (['face_front'],{'reference_image_1':'face','reference_image_2':'face'}),
])
def test_dedicated_roles_sheet_matches_plan_direct_mismatch(guide,batch,views,roles,monkeypatch):
    presence={'character_image':True,**dict.fromkeys(roles,True)}
    item=output(views,roles,presence,guide,batch)[0]
    expected,direct=encoded_sources(item,presence,guide,monkeypatch)
    assert expected!=direct[:len(expected)]

@pytest.mark.parametrize('guide',(False,True))
def test_batch_views_reselect_refs_and_keep_numbering(guide,monkeypatch):
    roles={'reference_image_1':'footwear','reference_image_3':'face'}
    presence={'character_image':True,**dict.fromkeys(roles,True)}
    items=output(['face_front','body_front','feet'],roles,presence,guide,True)
    assert len(items)==3
    for item in items:encoded_sources(item,presence,guide,monkeypatch)
    assert 'character_image' not in [r['source'] for r in items[-1]['reference_plan']]

def load(name):
    return json.loads((ROOT/'workflows'/name).read_text(encoding='utf-8'))

def exported(graph):
    graph=deepcopy(graph)
    for node in graph['nodes']:node['mode']=0
    return api_prompt(graph)

def test_sheet_template_routes_plan_images_and_preserves_sampler():
    new,old=load(SHEET),load(DIRECT)
    validate_graph(new)
    api,prior=exported(new),exported(old)
    enc=api['20:7']
    assert enc['class_type']=='QwenImage21CharacterSheetEncode'
    for name,source in [('prompt',['18',0]),('reference_plan',['18',5]),('layout_image',['18',3]),
        ('character_image',['1',0]),('reference_image_1',['15',0]),('reference_image_2',['16',0]),('reference_image_3',['17',0])]:
        assert enc['inputs'][name]==source
    assert enc['inputs']['reference_regions']=='{}'
    for name in ('20:3','20:4','20:5','20:6','20:8','20:9','20:10','19'):
        assert api[name]==prior[name]
    assert api['20:9']['inputs']['positive']==['20:7',0]
    assert api['20:9']['inputs']['negative']==['20:7',1]
    assert api['20:8']['inputs']['width']==['18',1]
    assert api['20:8']['inputs']['height']==['18',2]
    assert [n for n in new['nodes'] if n['type']=='LoadImage']==[n for n in old['nodes'] if n['type']=='LoadImage']

def test_direct_template_is_retained_with_explicit_warning():
    graph=load(DIRECT);validate_graph(graph)
    assert exported(graph)['20:7']['class_type']=='TextEncodeQwenImage21'
    note=next(n for n in graph['nodes'] if n['type']=='MarkdownNote')['widgets_values'][0]
    assert 'Do not set dedicated roles' in note and 'Sheet Encode' in note
