# Source provenance

UI, state handling, layout mathematics, validation rules, and test oracle originate from the user's H3 Character Sheet Designer repository:

https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer

Pinned distribution commit: bf792c652a9f50e895409e49fce667fef0f73c25.
The original source files used during implementation were verified against Git blob IDs, recorded in manifest.json. Files in tests/upstream are regression/test material, not registered ComfyUI extensions. The SVG artwork is the upstream fallback artwork with a Qwen-specific DOM namespace. The original 1254×1254 bitmap is bundled unchanged at web/assets/mannequin-atlas.png (Git blob 35dd5fabbe138b7b181b89d55432a6e53d0e9c34) and enabled by default. The SVG artwork is used only if that local bitmap cannot load in the UI. The bitmap is also used to render the layout_image output, which can be connected as a generation reference.

The isolated test excerpt in tests/upstream/core_empty_latent.py comes from ComfyUI comfy/sample.py at f1072eb0350638a3390ddb6afbcaa8c6b237c6fd:

https://github.com/Comfy-Org/ComfyUI

The MIT grant in LICENSE covers original code and documentation and the bundled PNG/SVG assets listed below, to the extent ukr8b3g-cmyk holds the applicable rights; it does not relicense third-party material. Preserve applicable upstream notices and licensing when redistributing. No model weights, font files, or reference-image bytes are included.

## Additional Reference functionality

The additional Reference UI, state handling, layout code and six PNGs under `web/assets/multi_reference/` adapt the owner's H3 enhancements with Qwen-specific prompting and encoding. The original registered node, workflow and artwork remain available for compatibility. Independent node IDs, routes and DOM namespaces are used.

Detailed local source snapshots and development records are retained locally and are not included in the public distribution. Public CPU/GPU validation scope is summarized in `verification/release_v141.json` and `verification/gpu_summary_v141.json`. Model weights and user reference-image bytes are not bundled.

## License scope and retained upstream terms

Original code, documentation and the specifically listed bundled artwork are licensed as described in [LICENSE](LICENSE). The H3 provenance above identifies the source of UI code, state handling, layout mathematics, validation, test-oracle code and artwork. The maintainer's authorization for the listed artwork is recorded below. The grant applies only to the extent the maintainer holds the applicable rights. Preserve any applicable original third-party terms.

### Bundled PNG and SVG artwork covered by MIT

On 2026-10-14, the maintainer confirmed that the bundled artwork was created using GPT, confirmed permission to redistribute it, and authorized including the following PNG and SVG assets under the MIT License in [LICENSE](LICENSE):

- `web/assets/mannequin-atlas.png`
- `web/assets/multi_reference/clothing_back.png`
- `web/assets/multi_reference/clothing_front.png`
- `web/assets/multi_reference/face_3q_left.png`
- `web/assets/multi_reference/face_3q_right.png`
- `web/assets/multi_reference/face_back.png`
- `web/assets/multi_reference/face_right.png`
- SVG fallback artwork in `web/avatar.js` and its retained test-source copy in `tests/upstream/web/avatar.js`

This grant covers the listed bundled artwork to the extent the maintainer holds the applicable rights, including redistribution under the MIT terms. It replaces the earlier MIT exclusion for these specific assets. It does not relicense third-party material or establish rights in unrelated generated content.

### Other images and materials

Verification screenshots, other images/screenshots embedded in or linked from documentation, model weights, user-provided references and user-generated outputs are not included in this MIT grant. Display/layout source code remains distinct from rights in other depicted artwork.

### ComfyUI test excerpt: GPL, not MIT

`tests/upstream/core_empty_latent.py` contains an isolated `fix_empty_latent_channels` excerpt from [ComfyUI comfy/sample.py at f1072eb0350638a3390ddb6afbcaa8c6b237c6fd](https://github.com/Comfy-Org/ComfyUI/blob/f1072eb0350638a3390ddb6afbcaa8c6b237c6fd/comfy/sample.py). Its upstream source blob is `4ebad9666c6bd12a8b54c4ea2775d74a7712b19c`. The test copy adds an explanatory module docstring and supplies dependencies from its test environment; it is not a full Core installation.

The [upstream LICENSE at that commit](https://github.com/Comfy-Org/ComfyUI/blob/f1072eb0350638a3390ddb6afbcaa8c6b237c6fd/LICENSE) contains the GNU General Public License, version 3. The excerpt retains the applicable upstream GPL terms and is expressly excluded from this repository's MIT grant. Test-only placement does not remove upstream licensing obligations. Preserve the upstream terms and source attribution when redistributing it; the GPL text is included verbatim in [LICENSES/ComfyUI-GPL-3.0.txt](LICENSES/ComfyUI-GPL-3.0.txt). This notice does not claim that the entire repository or a combined distribution is exclusively MIT-licensed.

### External components and provenance records

ComfyUI, Qwen models, dependencies and external services retain their own licenses and terms. The MIT grant does not extend to those components or guarantee rights in generated content.

`manifest.json` is preserved as the historical distribution/verification snapshot; it is not a current Registry archive manifest. Registry preparation changes licensing documentation, packaging metadata, exclusion rules and publishing instructions/workflow without changing product runtime code, tests, workflow templates, artwork bytes or the v1.5.3 release tag. The package name and version remain unchanged. The manual Registry workflow pins the audited preparation commit and verifies its exact package file paths, byte counts and SHA256 hashes. Tests (including the GPL excerpt), development tools and verification screenshots are excluded from the Registry ZIP; the retained GPL license text remains included.

