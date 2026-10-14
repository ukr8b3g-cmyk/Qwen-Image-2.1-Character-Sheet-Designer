"""Validate whole lists before binding images to views and assembling on CPU."""
import json

import torch
import torch.nn.functional as F

from .common.state import StateValidationError, decode_json
from .sheet_plan import parse_sheet_plan, contain_bounds
from .node import runtime_max_resolution


class QwenImage21CharacterSheetAssemble:
    CATEGORY = 'Qwen/CharacterSheet'
    DESCRIPTION = 'Batch Out ON, one image per view, batch size 1. Validates full lists without repeating missing elements. Guarantees panel placement and declared view correspondence, not generated anatomy or camera correctness.'
    RETURN_TYPES = ('IMAGE', 'STRING')
    RETURN_NAMES = ('sheet', 'assembly_info')
    FUNCTION = 'assemble'
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'view_records': ('STRING', {'forceInput': True}),
                             'sheet_plan': ('STRING', {'forceInput': True})}}

    def assemble(self, images, view_records, sheet_plan):
        if len(sheet_plan) != 1:
            raise StateValidationError('Connect exactly one whole-sheet plan.', 'sheet_plan_count')
        plan = parse_sheet_plan(sheet_plan[0], max_resolution=runtime_max_resolution())
        count = len(plan['views'])
        if len(images) != count or len(view_records) != count:
            raise StateValidationError('Image and view-record counts must exactly match the sheet plan. Use Batch Out ON; missing entries are never repeated.', 'sheet_view_count')
        expected = {view['view_id'] for view in plan['views']}
        bound = {}
        for image, raw in zip(images, view_records, strict=True):
            record = decode_json(raw)
            if type(record) is not dict or set(record) != {'schema_version', 'view_id', 'sheet_plan_hash', 'width', 'height', 'prompt'}:
                raise StateValidationError('Invalid view record.', 'invalid_view_record')
            view = record['view_id']
            if type(record['schema_version']) is not int or record['schema_version'] != 1 or type(view) is not str or view not in expected or view in bound:
                raise StateValidationError('Unknown or duplicate view ID.', 'invalid_view_record')
            if record['sheet_plan_hash'] != plan['plan_hash']:
                raise StateValidationError('View belongs to a different sheet plan.', 'sheet_plan_mismatch')
            if type(record['prompt']) is not str or any(type(record[k]) is not int or record[k] < 1 for k in ('width', 'height')):
                raise StateValidationError('Invalid recorded generation dimensions or prompt.', 'invalid_view_record')
            if not isinstance(image, torch.Tensor) or image.ndim != 4 or image.shape[0] != 1 or image.shape[-1] not in (3, 4) or not image.is_floating_point():
                raise StateValidationError('Each view needs one floating-point RGB or RGBA IMAGE with batch size 1.', 'invalid_view_image')
            if list(image.shape[1:3]) != [record['height'], record['width']]:
                raise StateValidationError('Image dimensions disagree with its view record.', 'view_image_mismatch')
            if not bool(torch.isfinite(image).all()) or bool((image < 0).any()) or bool((image > 1).any()):
                raise StateValidationError('View IMAGE values must be finite and within 0 to 1.', 'invalid_view_image')
            bound[view] = (image, record)
        width, height = plan['canvas']
        canvas = torch.ones((1, height, width, 3), dtype=torch.float32, device='cpu')
        placements = []
        for view in plan['views']:
            image, record = bound[view['view_id']]
            box = contain_bounds(view['bounds'], record['width'], record['height'])
            left, top, right, bottom = box
            source = image.detach().to(device='cpu', dtype=torch.float32)
            if source.shape[-1] == 4:
                alpha = source[..., 3:4]
                source = source[..., :3] * alpha + (1 - alpha)
            source = source.permute(0, 3, 1, 2)
            resized = F.interpolate(source, size=(bottom - top, right - left), mode='bilinear', align_corners=False, antialias=True).permute(0, 2, 3, 1)
            canvas[:, top:bottom, left:right] = resized
            placements.append({'view_id': view['view_id'], 'panel_bounds': view['bounds'], 'image_bounds': box,
                               'source_size': [record['width'], record['height']], 'generation_prompt': record['prompt']})
        info = {'schema_version': 1, 'method': 'assembled_independent_views', 'sheet_plan_hash': plan['plan_hash'],
                'canvas': plan['canvas'], 'views': placements,
                'guarantee': 'Declared view-to-panel placement only. Image content and upstream provenance are not classified.'}
        return canvas, json.dumps(info, ensure_ascii=False, separators=(',', ':'))
