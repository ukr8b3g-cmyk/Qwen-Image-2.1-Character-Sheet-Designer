"""Copy the pinned H3 UI bitmap locally. No network and no model downloads."""
from pathlib import Path
import argparse
import hashlib
import os
import tempfile

EXPECTED_GIT_BLOB = "35dd5fabbe138b7b181b89d55432a6e53d0e9c34"


def import_artwork(source: Path, root: Path) -> None:
    if source.is_dir():
        source = source / "web" / "assets" / "mannequin-atlas.png"
    data = source.read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if actual != EXPECTED_GIT_BLOB:
        raise ValueError("The bitmap differs from the pinned H3 asset; no files were changed.")
    destination = root / "web" / "assets" / "mannequin-atlas.png"
    if destination.exists() and destination.read_bytes() != data:
        raise ValueError("A different destination bitmap already exists; refusing to overwrite it.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    (root / "web" / "artwork_config.js").write_text(
        "// Pinned H3 bitmap imported locally; no external image requests.\n"
        "export const USE_RASTER_ATLAS = true;\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="H3-Character-Sheet-Designer directory, or the atlas PNG")
    args = parser.parse_args()
    try:
        import_artwork(args.source, Path(__file__).resolve().parents[1])
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Artwork import failed: {exc}\n")
    print("Verified H3 UI bitmap copied. Reload the browser. Generation behavior is unchanged.")
