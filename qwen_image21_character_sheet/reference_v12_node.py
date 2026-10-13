"""Additive V1.2 Designer; previous node contracts are unchanged."""
import numpy as np
import torch

from .compiler import STYLE_PROMPTS, StateValidationError
from .multi_layout_image import render_layout_image
from .multi_reference_compiler import parse_multi_state
from .node import runtime_max_resolution
from .reference_v12_compiler import DEFAULT_V12_STATE_JSON, compile_output_plan_v12


class QwenImage21CharacterSheetDesignerReferenceV12:
    CATEGORY = 'Qwen/CharacterSheet'
    DESCRIPTION = 'V1.2 selects references per output. Connect prompt, reference_plan and layout_image to Qwen 2.1 Sheet Encode; fan out images to matching named inputs. Manual size applies to each independent image.'
    RETURN_TYPES = ('STRING', 'INT', 'INT', 'IMAGE', 'STRING', 'STRING')
    RETURN_NAMES = ('prompt', 'width', 'height', 'layout_image', 'filename_suffix', 'reference_plan')
    OUTPUT_IS_LIST = (True,) * 6
    FUNCTION = 'compile'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'state_json': ('STRING', {'default': DEFAULT_V12_STATE_JSON, 'multiline': True, 'dynamicPrompts': False})},
                'optional': {'character_image': ('IMAGE',), 'reference_image_1': ('IMAGE',),
                             'reference_image_2': ('IMAGE',), 'reference_image_3': ('IMAGE',),
                             'use_layout_image': ('BOOLEAN', {'default': False}),
                             'style': (list(STYLE_PROMPTS), {'default': 'none'}),
                             'batch_out': ('BOOLEAN', {'default': False, 'label_on': 'Batch Out ON', 'label_off': 'Batch Out OFF'})}}

    @classmethod
    def VALIDATE_INPUTS(cls, state_json, use_layout_image=False, style='none', batch_out=False):
        try:
            compile_output_plan_v12(state_json, strict=False, max_resolution=runtime_max_resolution(),
                                    use_layout_image=use_layout_image, style=style, batch_out=batch_out)
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json, character_image=None, reference_image_1=None, reference_image_2=None,
                reference_image_3=None, use_layout_image=False, style='none', batch_out=False):
        presence = {name: value is not None for name, value in (
            ('character_image', character_image), ('reference_image_1', reference_image_1),
            ('reference_image_2', reference_image_2), ('reference_image_3', reference_image_3))}
        plan = compile_output_plan_v12(state_json, max_resolution=runtime_max_resolution(),
                                      use_layout_image=use_layout_image, style=style,
                                      batch_out=batch_out, reference_presence=presence)
        images = [None] * plan['count']
        if use_layout_image:
            state = parse_multi_state(state_json, max_resolution=runtime_max_resolution())
            for index, item in enumerate(plan['items']):
                image = render_layout_image(item['layout'], clothing_mode=state['clothing_mode'])
                images[index] = torch.from_numpy(np.asarray(image, dtype=np.float32) / 255.0).unsqueeze(0)
        return ([i['prompt'] for i in plan['items']], [i['width'] for i in plan['items']],
                [i['height'] for i in plan['items']], images,
                [i['filename_suffix'] for i in plan['items']], [i['reference_plan_json'] for i in plan['items']])
