"""Select the planned images and delegate Qwen conditioning to ComfyUI Core."""
from .compiler import StateValidationError
from .reference_v12_plan import parse_reference_plan
from .reference_regions import crop_reference, parse_reference_regions

try:
    from comfy_extras.nodes_qwen import TextEncodeQwenImage21
except ModuleNotFoundError as exc:
    if exc.name not in ('comfy_extras', 'comfy_extras.nodes_qwen'):
        raise
    TextEncodeQwenImage21 = None


class QwenImage21CharacterSheetEncode:
    CATEGORY = 'Qwen/CharacterSheet'
    RETURN_TYPES = ('CONDITIONING', 'CONDITIONING')
    RETURN_NAMES = ('positive', 'negative')
    FUNCTION = 'encode'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'clip': ('CLIP',), 'prompt': ('STRING', {'forceInput': True}),
                             'negative_prompt': ('STRING', {'default': '', 'multiline': True}),
                             'reference_plan': ('STRING', {'forceInput': True}),
                             'resolution': ('INT', {'default': 1024, 'min': 0, 'max': 4096, 'step': 32})},
                'optional': {'vae': ('VAE',), 'layout_image': ('IMAGE',), 'character_image': ('IMAGE',),
                             'reference_image_1': ('IMAGE',), 'reference_image_2': ('IMAGE',), 'reference_image_3': ('IMAGE',),
                             'reference_regions': ('STRING', {'default': '{}', 'multiline': True,
                                 'tooltip': 'Optional crops by image source and view ID. [left, top, width, height], normalized 0–1. * applies to all views. Empty {} uses complete images.'})}}

    def encode(self, clip, prompt, negative_prompt, reference_plan, resolution=1024, vae=None,
               layout_image=None, character_image=None, reference_image_1=None, reference_image_2=None, reference_image_3=None,
               reference_regions='{}'):
        plan = parse_reference_plan(reference_plan)
        regions = parse_reference_regions(reference_regions)
        if TextEncodeQwenImage21 is None:
            raise RuntimeError('Qwen 2.1 Sheet Encode requires ComfyUI Core TextEncodeQwenImage21.')
        inputs = dict(layout_image=layout_image, character_image=character_image, reference_image_1=reference_image_1,
                      reference_image_2=reference_image_2, reference_image_3=reference_image_3)
        images = {}
        for index, entry in enumerate(plan['sources'], 1):
            value = inputs[entry['source']]
            if value is None:
                raise StateValidationError('Missing planned Encoder image: ' + entry['source'], 'reference_plan_mismatch')
            images[f'image_{index}'] = crop_reference(value, entry['source'], plan['view_ids'], regions)
        output = TextEncodeQwenImage21.execute(clip=clip, prompt=prompt, negative_prompt=negative_prompt,
                                               vae=vae, resolution=resolution, images=images)
        positive, negative, _latent = output.result
        return positive, negative
