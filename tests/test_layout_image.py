import copy
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from qwen_image21_character_sheet.compiler import DEFAULT_STATE, VIEW_IDS, compile_state
from qwen_image21_character_sheet.layout_image import ATLAS_CROPS, render_layout_image
from qwen_image21_character_sheet.node import QwenImage21CharacterSheetDesigner

ROOT=Path(__file__).resolve().parents[1]


def test_backend_and_frontend_use_the_same_atlas_crops():
    source=(ROOT/'web/artwork.js').read_text(encoding='utf-8')
    crops={name:tuple(int(v) for v in values.split(',')) for name,values in
           re.findall(r'(\w+): Object\.freeze\(\[([\d, ]+)\]\)',source)}
    assert crops==ATLAS_CROPS


@pytest.mark.parametrize('views',[[v] for v in VIEW_IDS]+[list(VIEW_IDS),list(VIEW_IDS[:5])])
@pytest.mark.parametrize('size',[
    {'mode':'auto','body_height':672,'manual_width':1344,'manual_height':768},
    {'mode':'manual','body_height':1120,'manual_width':512,'manual_height':768},
])
def test_layout_image_is_opaque_and_artwork_stays_inside_selected_panels(views,size):
    state=copy.deepcopy(DEFAULT_STATE);state.update(views=views,size=size)
    result=compile_state(json.dumps(state))
    image=render_layout_image(result['layout'])
    assert image.mode=='RGB' and image.size==(result['width'],result['height'])
    pixels=np.asarray(image)
    occupied=np.any(pixels<250,axis=-1)
    panels=np.zeros(occupied.shape,dtype=bool)
    for panel in result['layout']['panels']:
        x,y,w,h=panel['rect'];width,height=image.size
        left,top=round(x*width),round(y*height)
        right,bottom=round((x+w)*width),round((y+h)*height)
        assert occupied[top:bottom,left:right].any(),panel['id']
        panels[top:bottom,left:right]=True
    assert not occupied[~panels].any()
    assert np.all(pixels[0,0]==255)


def test_node_appends_standard_cpu_image_and_keeps_existing_outputs(monkeypatch):
    monkeypatch.setitem(sys.modules,'nodes',SimpleNamespace(MAX_RESOLUTION=16384))
    state=copy.deepcopy(DEFAULT_STATE)
    state['size'].update(mode='manual',manual_width=512,manual_height=256)
    raw=json.dumps(state)
    for guided in (False,True):
        result=compile_state(raw,use_layout_image=guided)
        outputs=QwenImage21CharacterSheetDesigner().compile(raw,guided)
        assert outputs[:3]==(result['prompt'],512,256)
        tensor=outputs[3]
        assert tensor.shape==(1,256,512,3) and tensor.dtype==torch.float32
        assert tensor.device.type=='cpu' and not tensor.requires_grad
        assert float(tensor.min())>=0 and float(tensor.max())==1
        expected=np.asarray(render_layout_image(result['layout']),dtype=np.float32)/255
        np.testing.assert_array_equal(tensor[0].numpy(),expected)


@pytest.mark.parametrize('bits', range(1, 128))
def test_every_selected_panel_has_a_complete_black_frame(bits):
    state=copy.deepcopy(DEFAULT_STATE)
    state['views']=[view for index,view in enumerate(VIEW_IDS) if bits & (1 << index)]
    state['size'].update(mode='manual',manual_width=512,manual_height=256)
    result=compile_state(json.dumps(state),use_layout_image=True)
    pixels=np.asarray(render_layout_image(result['layout']))
    assert len(result['layout']['panels'])==len(state['views'])
    for panel in result['layout']['panels']:
        x,y,w,h=panel['rect']
        left,top=round(x*512),round(y*256)
        right,bottom=round((x+w)*512),round((y+h)*256)
        assert np.all(pixels[top,left:right]==0),panel['id']
        assert np.all(pixels[bottom-1,left:right]==0),panel['id']
        assert np.all(pixels[top:bottom,left]==0),panel['id']
        assert np.all(pixels[top:bottom,right-1]==0),panel['id']
