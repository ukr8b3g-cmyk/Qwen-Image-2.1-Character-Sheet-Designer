"""CPU tensor-shape check of an isolated Core function, not real model validation."""
from types import SimpleNamespace
import pytest
import torch
from tests.upstream import core_empty_latent as core


@pytest.mark.parametrize('width,height',[(1344,768),(2816,1280),(2240,1280)])
def test_empty_latent_channels_and_spatial_factor(monkeypatch,width,height):
    def repeat(t,count,dim):
        counts=[1]*t.ndim;counts[dim]=(count+t.shape[dim]-1)//t.shape[dim]
        return t.repeat(*counts).narrow(dim,0,count)
    def upscale(t,w,h,method,crop):
        assert method=='nearest-exact' and crop=='disabled'
        return torch.nn.functional.interpolate(t,size=(h,w),mode='nearest-exact')
    monkeypatch.setattr(core,'torch',torch,raising=False)
    monkeypatch.setattr(core,'comfy',SimpleNamespace(utils=SimpleNamespace(repeat_to_batch_size=repeat,common_upscale=upscale)),raising=False)
    fmt=SimpleNamespace(latent_channels=64,spacial_downscale_ratio=16,latent_dimensions=2,fix_empty_latent=lambda x:x)
    model=SimpleNamespace(get_model_object=lambda key:fmt)
    source=torch.zeros((1,4,height//8,width//8),device='cpu')
    result=core.fix_empty_latent_channels(model,source,8)
    assert tuple(result.shape)==(1,64,height//16,width//16)
    assert result.device.type=='cpu' and torch.count_nonzero(result)==0
    # Missing spatial metadata does not authorize claiming correct final dimensions.
    unchanged_spatial=core.fix_empty_latent_channels(model,source,None)
    assert tuple(unchanged_spatial.shape)==(1,64,height//8,width//8)
