import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from qwen_image21_character_sheet import compiler as q
from qwen_image21_character_sheet import preview as p
from qwen_image21_character_sheet import node as n


def body(raw=q.DEFAULT_STATE_JSON):
    return json.dumps({"state_json":raw}, ensure_ascii=True).encode()


async def with_server(action):
    app = web.Application(client_max_size=p.HTTP_MAX_BYTES + 4096)
    app.router.add_post(p.PREVIEW_PATH, p.preview)
    async with TestClient(TestServer(app)) as client:
        return await action(client)


def test_live_http_contract_and_queue_compile_same(monkeypatch):
    monkeypatch.setitem(sys.modules, "nodes", SimpleNamespace(MAX_RESOLUTION=16384))
    async def checks(client):
        cases = [
            (body(),"application/json",200,None),
            (body(),"text/plain",415,"invalid_content_type"),
            (b"{}","application/json",400,"invalid_request"),
            (b'{"state_json":null}',"application/json",400,"invalid_type"),
            (b'{"state_json":"{", "extra":0}',"application/json",400,"invalid_request"),
            (b'{"state_json":"x","state_json":"y"}',"application/json",400,"duplicate_key"),
            (b"\xff","application/json",400,"invalid_utf8"),
            (body("x" * (q.STATE_MAX_BYTES+1)),"application/json",413,"state_too_large"),
            (b" "*(p.HTTP_MAX_BYTES+1),"application/json",413,"request_too_large"),
        ]
        for data, content_type, status, code in cases:
            response=await client.post(p.PREVIEW_PATH, data=data, headers={"Content-Type":content_type})
            assert response.status==status
            payload=await response.json()
            if code:
                assert payload["error"]["code"]==code
            else:
                assert payload==q.compile_state(q.DEFAULT_STATE_JSON)
                assert n.QwenImage21CharacterSheetDesigner().compile(q.DEFAULT_STATE_JSON)==(payload["prompt"],payload["width"],payload["height"])
        async def chunks():
            for _ in range(p.HTTP_MAX_BYTES // 4096 + 1):
                yield b" "*4096
        response=await client.post(p.PREVIEW_PATH,data=chunks(),headers={"Content-Type":"application/json"})
        assert response.status==413
        assert (await response.json())["error"]["code"]=="request_too_large"
        data=body(); data += b" "*(p.HTTP_MAX_BYTES-len(data))
        response=await client.post(p.PREVIEW_PATH,data=data,headers={"Content-Type":"application/json"})
        assert response.status==200
    asyncio.run(with_server(checks))


def test_state_transport_exact_limit():
    s=q.DEFAULT_STATE_JSON
    padded=s+" "*(q.STATE_MAX_BYTES-len(s))
    assert p.compile_preview_request(body(padded),max_resolution=16384)==q.compile_state(s)
    with pytest.raises(q.StateValidationError) as exc:
        p.compile_preview_request(b" "*(p.HTTP_MAX_BYTES+1),max_resolution=16384)
    assert exc.value.code=="request_too_large"


def test_runtime_limit_not_cached(monkeypatch):
    core=SimpleNamespace(MAX_RESOLUTION=4096);monkeypatch.setitem(sys.modules,"nodes",core)
    cls=n.QwenImage21CharacterSheetDesigner
    assert cls.VALIDATE_INPUTS(q.DEFAULT_STATE_JSON) is True
    core.MAX_RESOLUTION=2048
    assert isinstance(cls.VALIDATE_INPUTS(q.DEFAULT_STATE_JSON), str)
    core.MAX_RESOLUTION=16384
    assert cls().compile(q.DEFAULT_STATE_JSON)[1:]==(2208,1280)
    for value in (True,None,31):
        core.MAX_RESOLUTION=value
        with pytest.raises(RuntimeError):n.runtime_max_resolution()


def test_core_unavailable_http_error_redacted(monkeypatch):
    monkeypatch.setattr(p,"runtime_max_resolution",lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_SAMPLE")))
    async def check(client):
        response=await client.post(p.PREVIEW_PATH,data=body(),headers={"Content-Type":"application/json"})
        assert response.status==500
        text=await response.text()
        assert "PRIVATE_SAMPLE" not in text
        assert json.loads(text)["error"]["code"]=="internal_error"
    asyncio.run(with_server(check))


def test_register_routes_idempotent_and_h3_untouched(monkeypatch):
    calls=[]
    routes=SimpleNamespace(post=lambda path: lambda handler:calls.append((path,handler)))
    instance=SimpleNamespace(routes=routes, _h3_character_sheet_designer_route_registered=True)
    monkeypatch.setitem(sys.modules,"server",SimpleNamespace(PromptServer=SimpleNamespace(instance=instance)))
    assert p.register_routes() is True and p.register_routes() is True
    assert calls==[(p.PREVIEW_PATH,p.preview)]
    assert instance._h3_character_sheet_designer_route_registered is True


# Core f1072eb nodes.py: load_custom_node uses module_path.replace(".", "_x_").
# A raw dotted folder name is not the actual Core Python import contract.
@pytest.mark.parametrize("pack_name",["q21_test_pack",str(Path(__file__).resolve().parents[1]).replace(".","_x_")])
def test_root_pack_only_registers_qwen(monkeypatch,pack_name):
    monkeypatch.setitem(sys.modules,"server",SimpleNamespace(PromptServer=SimpleNamespace(instance=None)))
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location(pack_name,root/"__init__.py",submodule_search_locations=[str(root)])
    module=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,pack_name,module)
    spec.loader.exec_module(module)
    assert set(module.NODE_CLASS_MAPPINGS)=={"QwenImage21CharacterSheetDesigner"}
    cls=module.NODE_CLASS_MAPPINGS["QwenImage21CharacterSheetDesigner"]
    assert cls.RETURN_TYPES==("STRING","INT","INT")
    assert cls.RETURN_NAMES==("prompt","width","height")
    assert cls.FUNCTION=="compile"
    assert list(cls.INPUT_TYPES()["required"])==["state_json"]
    assert cls.INPUT_TYPES()["required"]["state_json"][1]["dynamicPrompts"] is False
    assert module.WEB_DIRECTORY=="./web"
