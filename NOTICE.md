# Source provenance

UI, state handling, layout mathematics, validation rules, and test oracle originate from the user's H3 Character Sheet Designer repository:

https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer

Pinned distribution commit: bf792c652a9f50e895409e49fce667fef0f73c25.
The original source files used during implementation were verified against Git blob IDs, recorded in manifest.json. Files in tests/upstream are regression/test material, not registered ComfyUI extensions. The SVG artwork is the upstream fallback artwork with a Qwen-specific DOM namespace. The original 1254×1254 bitmap is bundled unchanged at web/assets/mannequin-atlas.png (Git blob 35dd5fabbe138b7b181b89d55432a6e53d0e9c34) and enabled by default. The SVG artwork is used only if that local bitmap cannot load. The artwork is UI-only and is never a generation input.

The isolated test excerpt in tests/upstream/core_empty_latent.py comes from ComfyUI comfy/sample.py at f1072eb0350638a3390ddb6afbcaa8c6b237c6fd:

https://github.com/Comfy-Org/ComfyUI

This implementation does not assign a new license to upstream material. Preserve applicable upstream notices and licensing when redistributing. No model weights, font files, or reference-image bytes are included.
