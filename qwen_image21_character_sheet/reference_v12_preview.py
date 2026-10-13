"""Independent V1.2 preview route; no image data or inference in requests."""
from .compiler import STATE_MAX_BYTES, StateValidationError, decode_json
from .node import runtime_max_resolution
from .reference_v12_compiler import compile_output_preview_v12

PREVIEW_PATH = '/qwen_image21_character_sheet_designer/reference_v12_preview'


def compile_preview_request(body, *, max_resolution):
    if len(body) > 3 * STATE_MAX_BYTES:
        raise StateValidationError('Preview request exceeds 192 KiB.', 'request_too_large')
    envelope = decode_json(body.decode('utf-8'), byte_limit=3 * STATE_MAX_BYTES)
    if type(envelope) is not dict or 'state_json' not in envelope or set(envelope) - {'state_json', 'use_layout_image', 'style', 'reference_presence', 'batch_out'}:
        raise StateValidationError('Invalid preview request.', 'invalid_request')
    return compile_output_preview_v12(envelope['state_json'], max_resolution=max_resolution,
        use_layout_image=envelope.get('use_layout_image', False), style=envelope.get('style', 'none'),
        reference_presence=envelope.get('reference_presence'), batch_out=envelope.get('batch_out', False))


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
    flag = '_qwen_image21_reference_v12_preview_registered'
    if not getattr(instance, flag, False):
        instance.routes.post(PREVIEW_PATH)(preview)
        setattr(instance, flag, True)
    return True
