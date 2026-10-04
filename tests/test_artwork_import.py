import hashlib
from pathlib import Path
import pytest
from tools import import_h3_artwork as m


def test_wrong_artwork_leaves_destination_untouched(tmp_path):
    source=tmp_path/'wrong.png';source.write_bytes(b'not the atlas')
    root=tmp_path/'pack'
    with pytest.raises(ValueError):m.import_artwork(source,root)
    assert not root.exists()


def test_explicit_verified_local_copy_only(tmp_path,monkeypatch):
    data=b'local-fixture-not-real-png'
    monkeypatch.setattr(m,'EXPECTED_GIT_BLOB',hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest())
    source=tmp_path/'h3/web/assets/mannequin-atlas.png';source.parent.mkdir(parents=True);source.write_bytes(data)
    root=tmp_path/'qwen';m.import_artwork(tmp_path/'h3',root)
    assert (root/'web/assets/mannequin-atlas.png').read_bytes()==data
    assert 'true' in (root/'web/artwork_config.js').read_text()
    m.import_artwork(tmp_path/'h3',root)  # idempotent for verified bytes
    (root/'web/assets/mannequin-atlas.png').write_bytes(b'other work')
    with pytest.raises(ValueError):m.import_artwork(tmp_path/'h3',root)
    assert (root/'web/assets/mannequin-atlas.png').read_bytes()==b'other work'
