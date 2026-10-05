"""ComfyUI adapter; preview availability is not an execution prerequisite."""
import importlib
import numpy as np
import torch
from .compiler import DEFAULT_STATE_JSON, STYLE_PROMPTS, StateValidationError, compile_state
from .layout_image import render_layout_image


def runtime_max_resolution() -> int:
    maximum = importlib.import_module("nodes").MAX_RESOLUTION
    if type(maximum) is not int or maximum < 32:
        raise RuntimeError("ComfyUI nodes.MAX_RESOLUTION must be an integer of at least 32.")
    return maximum


class QwenImage21CharacterSheetDesigner:
    CATEGORY = "Qwen/CharacterSheet"
    DESCRIPTION = (
        "Compile only the checked views as busts, full-body views and isolated hand/foot studies. Connect prompt to "
        "TextEncodeQwenImage21 and width/height to EmptyLatentImage. Connect the reference "
        "directly to the encoder. For layout guidance, enable use_layout_image and connect "
        "layout_image to image_1 and the character to image_2. Placement remains model guidance."
    )
    RETURN_TYPES = ("STRING", "INT", "INT", "IMAGE")
    RETURN_NAMES = ("prompt", "width", "height", "layout_image")
    FUNCTION = "compile"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"state_json": ("STRING", {
            "default": DEFAULT_STATE_JSON, "multiline": True, "dynamicPrompts": False,
        })}, "optional": {"use_layout_image": ("BOOLEAN", {
            "default": False,
            "tooltip": "Enable when image_1 is layout_image and image_2 is the character reference in TextEncodeQwenImage21.",
        }), "style": (list(STYLE_PROMPTS), {
            "default": "none",
            "tooltip": "Change only character rendering. None adds no style instruction; identity, outfit and layout are preserved.",
        })}}

    @classmethod
    def VALIDATE_INPUTS(cls, state_json, use_layout_image=False, style="none"):
        try:
            compile_state(state_json, max_resolution=runtime_max_resolution(), use_layout_image=use_layout_image, style=style)
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json, use_layout_image=False, style="none"):
        result = compile_state(state_json, max_resolution=runtime_max_resolution(), use_layout_image=use_layout_image, style=style)
        image = render_layout_image(result["layout"])
        layout_image = torch.from_numpy(np.asarray(image, dtype=np.float32) / 255.0).unsqueeze(0)
        return result["prompt"], result["width"], result["height"], layout_image
