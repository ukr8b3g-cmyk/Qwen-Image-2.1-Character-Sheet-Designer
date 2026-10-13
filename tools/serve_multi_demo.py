"""Loopback-only Multi Reference UI harness; simulated host, no GPU/model load."""
import argparse
from pathlib import Path
import sys
from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.serve_demo import make_app as make_legacy_app
from qwen_image21_character_sheet import multi_preview


def make_app():
    app = make_legacy_app()
    multi_preview.runtime_max_resolution = lambda: 16384
    app.router.add_post(multi_preview.PREVIEW_PATH, multi_preview.preview)
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8197)
    args = parser.parse_args()
    print(f'Open http://127.0.0.1:{args.port}/tests/browser/multi_index.html')
    web.run_app(make_app(), host='127.0.0.1', port=args.port, access_log=None)
