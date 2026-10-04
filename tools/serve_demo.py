"""Serve the real Designer UI/preview in a simulated host, on loopback only."""
import argparse
from pathlib import Path
import sys
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from qwen_image21_character_sheet import preview as p
from tests.upstream.h3_compiler import compile_state as h3_compile


def make_app():
    app=web.Application(client_max_size=196608)
    # Standalone harness limit, not read from a running ComfyUI instance.
    p.runtime_max_resolution=lambda:16384
    app.router.add_post(p.PREVIEW_PATH,p.preview)
    async def h3(request):
        body=await request.json()
        try:return web.json_response(h3_compile(body["state_json"]))
        except ValueError:return web.json_response({"error":{"code":"invalid_state","message":"Invalid H3 test state"}},status=400)
    app.router.add_post('/h3_character_sheet_designer/preview',h3)
    app.router.add_static('/web/',ROOT/'web')
    app.router.add_static('/tests/',ROOT/'tests')
    async def home(request):return web.HTTPFound('/tests/browser/index.html')
    app.router.add_get('/',home)
    return app


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8197);args=parser.parse_args()
    web.run_app(make_app(),host='127.0.0.1',port=args.port,access_log=None)
