"""Independent Qwen node pack: never re-register the H3 node or H3 route."""
from .qwen_image21_character_sheet.node import QwenImage21CharacterSheetDesigner
from .qwen_image21_character_sheet.preview import register_routes

NODE_CLASS_MAPPINGS = {"QwenImage21CharacterSheetDesigner": QwenImage21CharacterSheetDesigner}
NODE_DISPLAY_NAME_MAPPINGS = {"QwenImage21CharacterSheetDesigner": "Qwen Image 2.1 Character Sheet Designer"}
WEB_DIRECTORY = "./web"
register_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
