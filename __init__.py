"""Independent Qwen node pack: never re-register the H3 node or H3 route."""
from .qwen_image21_character_sheet.node import QwenImage21CharacterSheetDesigner
from .qwen_image21_character_sheet.preview import register_routes
from .qwen_image21_character_sheet.multi_reference_node import QwenImage21CharacterSheetDesignerMultiReference
from .qwen_image21_character_sheet.multi_preview import register_routes as register_multi_routes
from .qwen_image21_character_sheet.reference_v12_node import QwenImage21CharacterSheetDesignerReferenceV12
from .qwen_image21_character_sheet.sheet_encode import QwenImage21CharacterSheetEncode
from .qwen_image21_character_sheet.reference_v12_preview import register_routes as register_v12_routes

NODE_CLASS_MAPPINGS = {"QwenImage21CharacterSheetDesigner": QwenImage21CharacterSheetDesigner}
NODE_DISPLAY_NAME_MAPPINGS = {"QwenImage21CharacterSheetDesigner": "Qwen 2.1 Sheet Designer V1"}
NODE_CLASS_MAPPINGS["QwenImage21CharacterSheetDesignerMultiReference"] = QwenImage21CharacterSheetDesignerMultiReference
NODE_DISPLAY_NAME_MAPPINGS["QwenImage21CharacterSheetDesignerMultiReference"] = "Qwen 2.1 Sheet Designer Reference V1.1"
NODE_CLASS_MAPPINGS["QwenImage21CharacterSheetDesignerReferenceV12"] = QwenImage21CharacterSheetDesignerReferenceV12
NODE_DISPLAY_NAME_MAPPINGS["QwenImage21CharacterSheetDesignerReferenceV12"] = "Qwen 2.1 Sheet Designer Reference V1.2"
NODE_CLASS_MAPPINGS["QwenImage21CharacterSheetEncode"] = QwenImage21CharacterSheetEncode
NODE_DISPLAY_NAME_MAPPINGS["QwenImage21CharacterSheetEncode"] = "Qwen 2.1 Sheet Encode"
WEB_DIRECTORY = "./web"
register_routes()
register_multi_routes()
register_v12_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

from .qwen_image21_character_sheet.reference_v13_node import QwenImage21CharacterSheetDesignerReferenceV13
from .qwen_image21_character_sheet.sheet_assemble import QwenImage21CharacterSheetAssemble
from .qwen_image21_character_sheet.reference_v13_preview import register_routes as register_v13_routes

NODE_CLASS_MAPPINGS['QwenImage21CharacterSheetDesignerReferenceV13'] = QwenImage21CharacterSheetDesignerReferenceV13
NODE_DISPLAY_NAME_MAPPINGS['QwenImage21CharacterSheetDesignerReferenceV13'] = 'Qwen 2.1 Sheet Designer Reference V1.3'
NODE_CLASS_MAPPINGS['QwenImage21CharacterSheetAssemble'] = QwenImage21CharacterSheetAssemble
NODE_DISPLAY_NAME_MAPPINGS['QwenImage21CharacterSheetAssemble'] = 'Qwen 2.1 Sheet Assemble'
register_v13_routes()
