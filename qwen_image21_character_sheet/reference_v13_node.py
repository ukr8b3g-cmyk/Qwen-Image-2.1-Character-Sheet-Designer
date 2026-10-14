"""Composition-ready Designer; V1.2's existing six output slots stay intact."""
import json

from .reference_v12_node import QwenImage21CharacterSheetDesignerReferenceV12
from .node import runtime_max_resolution
from .sheet_plan import make_sheet_plan, serialize_sheet_plan
from .reference_v12_compiler import compile_output_plan_v12
from .compiler import StateValidationError


class QwenImage21CharacterSheetDesignerReferenceV13(QwenImage21CharacterSheetDesignerReferenceV12):
    DESCRIPTION = 'Generate independent views with Batch Out ON, then connect decoded images, view_records and sheet_plan to Sheet Assemble. Generation dimensions and sheet canvas dimensions are separate.'
    RETURN_TYPES = QwenImage21CharacterSheetDesignerReferenceV12.RETURN_TYPES + ('STRING', 'STRING')
    RETURN_NAMES = QwenImage21CharacterSheetDesignerReferenceV12.RETURN_NAMES + ('sheet_plan', 'view_records')
    OUTPUT_IS_LIST = QwenImage21CharacterSheetDesignerReferenceV12.OUTPUT_IS_LIST + (False, True)

    @classmethod
    def INPUT_TYPES(cls):
        inputs = super().INPUT_TYPES()
        inputs['optional']['batch_out'][1]['default'] = True
        inputs['optional'].update(
            sheet_size_mode=(['auto', 'manual'], {'default': 'auto', 'tooltip': 'Sheet canvas only. Generation sizes remain in the Designer Output size controls.'}),
            sheet_width=('INT', {'default': 1536, 'min': 32, 'max': runtime_max_resolution(), 'step': 32}),
            sheet_height=('INT', {'default': 864, 'min': 32, 'max': runtime_max_resolution(), 'step': 32}))
        return inputs

    @classmethod
    def VALIDATE_INPUTS(cls, state_json, use_layout_image=False, style='none', batch_out=True,
                        sheet_size_mode='auto', sheet_width=1536, sheet_height=864):
        try:
            compile_output_plan_v12(state_json, strict=False, max_resolution=runtime_max_resolution(),
                                    use_layout_image=use_layout_image, style=style, batch_out=batch_out)
            make_sheet_plan(state_json, sheet_size_mode=sheet_size_mode, sheet_width=sheet_width,
                            sheet_height=sheet_height, max_resolution=runtime_max_resolution())
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json, character_image=None, reference_image_1=None, reference_image_2=None,
                reference_image_3=None, use_layout_image=False, style='none', batch_out=True,
                sheet_size_mode='auto', sheet_width=1536, sheet_height=864):
        sheet = make_sheet_plan(state_json, sheet_size_mode=sheet_size_mode, sheet_width=sheet_width,
                                sheet_height=sheet_height, max_resolution=runtime_max_resolution())
        outputs = super().compile(state_json, character_image, reference_image_1, reference_image_2,
                                  reference_image_3, use_layout_image, style, batch_out)
        records = []
        if batch_out:
            for view, prompt, width, height in zip(sheet['views'], outputs[0], outputs[1], outputs[2], strict=True):
                records.append(json.dumps({'schema_version': 1, 'view_id': view['view_id'],
                    'sheet_plan_hash': sheet['plan_hash'], 'width': width, 'height': height, 'prompt': prompt},
                    ensure_ascii=False, separators=(',', ':')))
        return (*outputs, serialize_sheet_plan(sheet), records)
