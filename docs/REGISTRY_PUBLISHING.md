# Comfy Registry publication

## Package identity

- Node ID: `qwen-image21-character-sheet-designer`
- Version: `1.5.3`
- Publisher: `ukr8b3g-cmyk`
- Product release: [`v1.5.3`](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/releases/tag/v1.5.3)
- Product source: `3b86735a7075d234119a7037e32b5ac9e01476dd`

Registry preparation may add metadata, packaging rules, licensing documentation
and the publishing workflow after the release commit. The product code and
release tag remain unchanged. The workflow pins the exact audited preparation
commit; it never publishes an arbitrary branch tip.

## Installation and dependencies

After publication is confirmed, search for the node ID above in ComfyUI-Manager,
or use `comfy node install qwen-image21-character-sheet-designer@1.5.3`.
Restart ComfyUI and reload its browser frontend after installation.

This is a ComfyUI custom-node package, not a standalone Python application.
Python 3.10 or newer and an existing ComfyUI installation are required.
`dependencies = []` means no additional packages beyond the host installation:
the runtime uses ComfyUI's `torch`, `numpy`, `Pillow` and `aiohttp`, its server
API, and `comfy_extras.nodes_qwen`. Keep those dependencies managed by ComfyUI;
this package must not replace the user's CPU/CUDA-specific PyTorch installation.
Models and user reference images are not included. The README describes the
generation setup and workflow requirements.

## Archive boundary

The Registry ZIP retains every runtime Python module, browser JS/CSS module,
the seven local PNG assets, all six bundled workflow JSON templates, README,
user-facing docs, LICENSE, NOTICE and retained upstream license text.
The `.comfyignore` file excludes test fixtures and their GPL test excerpt,
development tools, verification outputs/screenshots, the historical manifest,
GitHub workflows and this maintainer-only publishing guide. It also excludes
common credential, cache and build-output paths. No force-included directories
are configured. Do not package a development working directory.

Review LICENSE and NOTICE for the exact scope and provenance. A repository-wide
MIT claim must not override retained third-party terms or asset exclusions.

## Manual-only workflow

1. Review the exact `publish_registry.yml` source commit, metadata assertions
   and audited path/byte-count/SHA256 manifest digest.
2. Keep the existing `REGISTRY_ACCESS_TOKEN` GitHub Actions secret scoped to
   this publisher. Do not print, copy, recreate or commit its value.
3. Run the workflow manually from `main` only after the package and rights
   review are complete. There is no push, tag, release or scheduled trigger.
4. The workflow checks out the pinned source with read-only repository
   permissions, installs official `comfy-cli==1.22.0`, and disables telemetry.
5. It runs the real `comfy node pack` and validates every archive path, byte
   count and SHA256 against the independently audited manifest.
6. Both the node and version API endpoints must return JSON HTTP 404. An
   existing or partially created node/version, authentication failure, timeout,
   unexpected HTTP status or non-JSON response stops publication.
7. It invokes publication once and checks the repacked ZIP against the audited
   ZIP. Never retry a failed publication blindly: the Registry can reserve the
   version before upload. Inspect the existing Registry entry and workflow log.
8. Verify the returned Registry node/version, publisher, repository, download
   availability and validation status before reporting success. A completed
   upload is not proof of approval or successful installation.

## Local verification

Use a clean checkout, keep generated logs and archives outside it, and run:

```sh
python -m pip install comfy-cli==1.22.0
comfy --skip-prompt --no-enable-telemetry env
comfy node pack
node --test tests/js/*.test.js
python -m pytest
```

Tests use CPU fixtures where supported; installed-Core integration tests may
require `QWEN_SHEET_TEST_COMFYUI_ROOT`. Do not describe skipped tests as passed.
Packing does not need model downloads, GPU execution or Registry credentials.
The canonical manifest is sorted `(path, uncompressed bytes, SHA256)` tuples,
JSON-encoded with `ensure_ascii=True` and `separators=(',', ':')`, UTF-8, with
no trailing newline. Its SHA256 is embedded in the manual workflow.

Official publishing reference: <https://docs.comfy.org/registry/publishing>
