"""ComfyUI adapter; preview availability is not an execution prerequisite."""
import importlib
from .compiler import DEFAULT_STATE_JSON, StateValidationError, compile_state


def runtime_max_resolution() -> int:
    maximum = importlib.import_module("nodes").MAX_RESOLUTION
    if type(maximum) is not int or maximum < 32:
        raise RuntimeError("ComfyUI nodes.MAX_RESOLUTION must be an integer of at least 32.")
    return maximum


class QwenImage21CharacterSheetDesigner:
    CATEGORY = "Qwen/CharacterSheet"
    DESCRIPTION = (
        "Design a static character sheet from one reference image. Connect prompt to "
        "TextEncodeQwenImage21 and width/height to EmptyLatentImage. Connect the reference "
        "directly to the encoder. Layout is semantic guidance, not a hard mask."
    )
    RETURN_TYPES = ("STRING", "INT", "INT")
    RETURN_NAMES = ("prompt", "width", "height")
    FUNCTION = "compile"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"state_json": ("STRING", {
            "default": DEFAULT_STATE_JSON, "multiline": True, "dynamicPrompts": False,
        })}}

    @classmethod
    def VALIDATE_INPUTS(cls, state_json):
        try:
            compile_state(state_json, max_resolution=runtime_max_resolution())
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json):
        result = compile_state(state_json, max_resolution=runtime_max_resolution())
        return result["prompt"], result["width"], result["height"]
