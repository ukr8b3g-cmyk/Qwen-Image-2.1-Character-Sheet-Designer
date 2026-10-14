"""Independent V1.3 preview route; no image data or inference in requests."""
from .compiler import STATE_MAX_BYTES, StateValidationError, decode_json
from .node import runtime_max_resolution
import json
from .reference_v12_preview import compile_preview_request as compile_v12_request
from .sheet_plan import make_sheet_plan

PREVIEW_PATH = '/qwen_image21_character_sheet_designer/reference_v13_preview'


def compile_preview_request(body, *, max_resolution):
    if len(body) > 3 * STATE_MAX_BYTES:
        raise StateValidationError('Preview request exceeds 192 KiB.', 'request_too_large')
    envelope = decode_json(body.decode('utf-8'), byte_limit=3 * STATE_MAX_BYTES)
    sheet_keys = {'sheet_size_mode', 'sheet_width', 'sheet_height'}
    if type(envelope) is not dict:
        raise StateValidationError('Invalid preview request.', 'invalid_request')
    from_options = {key: envelope[key] for key in sheet_keys if key in envelope}
    base = {key: value for key, value in envelope.items() if key not in sheet_keys}
    result = compile_v12_request(json.dumps(base).encode('utf-8'), max_resolution=max_resolution)
    result['sheet_plan'] = make_sheet_plan(envelope['state_json'], max_resolution=max_resolution, **from_options)
    return result


async def preview(request):
    from aiohttp import web

    if request.content_type != 'application/json':
        return web.json_response({'error': {'code': 'invalid_content_type', 'message': 'Use application/json.'}}, status=415)
    body = bytearray()
    async for chunk in request.content.iter_chunked(4096):
        body.extend(chunk)
        if len(body) > 3 * STATE_MAX_BYTES:
            return web.json_response({'error': {'code': 'request_too_large', 'message': 'Preview request exceeds 192 KiB.'}}, status=413)
    try:
        result = compile_preview_request(bytes(body), max_resolution=runtime_max_resolution())
    except UnicodeDecodeError:
        return web.json_response({'error': {'code': 'invalid_utf8', 'message': 'Use UTF-8.'}}, status=400)
    except StateValidationError as exc:
        return web.json_response({'error': {'code': exc.code, 'message': str(exc)}}, status=400)
    return web.json_response(result)


def register_routes():
    try:
        from server import PromptServer
    except ModuleNotFoundError as exc:
        if exc.name == 'server':
            return False
        raise
    instance = getattr(PromptServer, 'instance', None)
    if instance is None:
        return False
    flag = '_qwen_image21_reference_v13_preview_registered'
    if not getattr(instance, flag, False):
        instance.routes.post(PREVIEW_PATH)(preview)
        setattr(instance, flag, True)
    return True
