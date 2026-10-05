"""Record source payload hashes with LF text endings and the latest test scope."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.git','__pycache__','.pytest_cache','node_modules','.venv'}


def purpose(path):
    first=path.parts[0]
    return {'web':'frontend','qwen_image21_character_sheet':'backend','tests':'test/fixture',
            'tools':'development utility','workflows':'workflow','docs':'documentation',
            'verification':'verification evidence'}.get(first,'package metadata/documentation')


def build(extra_sources=None):
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    entries=[]
    for path in sorted(ROOT.rglob('*')):
        relative=path.relative_to(ROOT)
        if not path.is_file() or any(p in EXCLUDE for p in relative.parts) or str(relative)=='manifest.json':continue
        payload=path.read_bytes()
        if b'\0' not in payload:
            payload=payload.replace(b'\r\n',b'\n')
        entries.append({'path':relative.as_posix(),'sha256':hashlib.sha256(payload).hexdigest(),
                        'bytes':len(payload),'purpose':purpose(relative)})
    old=json.loads((ROOT/'manifest.json').read_text()) if (ROOT/'manifest.json').exists() else {}
    data={'schema_version':1,'created_utc':now,'target_repository':'ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer',
          'target_base_commit':old.get('target_base_commit'),'target_state':'Verified source payload for publication',
          'text_hash_line_endings':'LF',
          'sources':extra_sources if extra_sources is not None else old.get('sources',[]),
          'results':json.loads((ROOT/'verification/black_frames.json').read_text()),'files':entries,
          'manifest_self_hash':'excluded to avoid recursive hashing'}
    (ROOT/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return data


if __name__=='__main__':
    print(f"Manifest written: {len(build()['files'])} files")
