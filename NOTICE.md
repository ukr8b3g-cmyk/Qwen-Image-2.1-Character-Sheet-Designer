# Source provenance

UI, state handling, layout mathematics, validation rules, and test oracle originate from the user's H3 Character Sheet Designer repository:

https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer

Pinned distribution commit: bf792c652a9f50e895409e49fce667fef0f73c25.
The original source files used during implementation were verified against Git blob IDs, recorded in manifest.json. Files in tests/upstream are regression/test material, not registered ComfyUI extensions. The SVG artwork is the upstream fallback artwork with a Qwen-specific DOM namespace. The original 1254×1254 bitmap is bundled unchanged at web/assets/mannequin-atlas.png (Git blob 35dd5fabbe138b7b181b89d55432a6e53d0e9c34) and enabled by default. The SVG artwork is used only if that local bitmap cannot load in the UI. The bitmap is also used to render the layout_image output, which can be connected as a generation reference.

The isolated test excerpt in tests/upstream/core_empty_latent.py comes from ComfyUI comfy/sample.py at f1072eb0350638a3390ddb6afbcaa8c6b237c6fd:

https://github.com/Comfy-Org/ComfyUI

The MIT grant in LICENSE covers only original code and documentation for which ukr8b3g-cmyk holds the applicable rights; it does not relicense third-party material. Preserve applicable upstream notices and licensing when redistributing. No model weights, font files, or reference-image bytes are included.

## Additional Reference functionality

The additional Reference UI, state handling, layout code and six PNGs under `web/assets/multi_reference/` adapt the owner's H3 enhancements with Qwen-specific prompting and encoding. The original registered node, workflow and artwork remain available for compatibility. Independent node IDs, routes and DOM namespaces are used.

Detailed local source snapshots and development records are retained locally and are not included in the public distribution. Public CPU/GPU validation scope is summarized in `verification/release_v141.json` and `verification/gpu_summary_v141.json`. Model weights and user reference-image bytes are not bundled.

## License scope and retained upstream terms

Original code and documentation are licensed as described in [LICENSE](LICENSE). The H3 provenance above identifies the source of UI code, state handling, layout mathematics, validation, test-oracle code and artwork; provenance alone does not establish permission for every included asset. Owner-authored H3 code and documentation are covered only to the extent the owner holds the applicable rights. Preserve any applicable original third-party terms.

### Images and artwork excluded from MIT

The MIT grant does not cover `web/assets/mannequin-atlas.png`, the six PNGs under `web/assets/multi_reference/`, SVG fallback artwork (including H3-derived artwork in `web/avatar.js` and `tests/upstream/web/avatar.js`), verification screenshots, or images/screenshots embedded in or linked from documentation. It also does not cover user-provided references or generated outputs. Display/layout source code is distinct from rights in the depicted artwork. This update does not establish a separate image license or a complete chain of rights; confirm applicable rights before reuse or redistribution.

### ComfyUI test excerpt: GPL, not MIT

`tests/upstream/core_empty_latent.py` contains an isolated `fix_empty_latent_channels` excerpt from [ComfyUI comfy/sample.py at f1072eb0350638a3390ddb6afbcaa8c6b237c6fd](https://github.com/Comfy-Org/ComfyUI/blob/f1072eb0350638a3390ddb6afbcaa8c6b237c6fd/comfy/sample.py). Its upstream source blob is `4ebad9666c6bd12a8b54c4ea2775d74a7712b19c`. The test copy adds an explanatory module docstring and supplies dependencies from its test environment; it is not a full Core installation.

The [upstream LICENSE at that commit](https://github.com/Comfy-Org/ComfyUI/blob/f1072eb0350638a3390ddb6afbcaa8c6b237c6fd/LICENSE) contains the GNU General Public License, version 3. The excerpt retains the applicable upstream GPL terms and is expressly excluded from this repository's MIT grant. Test-only placement does not remove upstream licensing obligations. Preserve the upstream terms and source attribution when redistributing it; the GPL text is included verbatim in [LICENSES/ComfyUI-GPL-3.0.txt](LICENSES/ComfyUI-GPL-3.0.txt). This notice does not claim that the entire repository or a combined distribution is exclusively MIT-licensed.

### External components and provenance records

ComfyUI, Qwen models, dependencies and external services retain their own licenses and terms. The MIT grant does not extend to those components or guarantee rights in generated content.

`manifest.json` is preserved as the existing distribution/verification snapshot. Its recorded hashes are not a claim to describe the LICENSE, README or NOTICE after this licensing-documentation update. Runtime code, tests, workflows, images and that manifest are unchanged by this update. Package metadata changes are limited to the PublisherId entry in pyproject.toml; names and versions are unchanged.

