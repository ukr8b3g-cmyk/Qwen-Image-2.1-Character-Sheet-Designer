"""Record payload hashes and test scope. Does not perform or imply a git commit."""
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
        entries.append({'path':relative.as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'bytes':path.stat().st_size,'purpose':purpose(relative)})
    old=json.loads((ROOT/'manifest.json').read_text()) if (ROOT/'manifest.json').exists() else {}
    data={'schema_version':1,'created_utc':now,'target_repository':'ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer',
          'target_base_commit':None,'target_state':'Empty remote at inspection; uncommitted local implementation',
          'sources':extra_sources if extra_sources is not None else old.get('sources',[]),
          'results':json.loads((ROOT/'verification/results.json').read_text()),'files':entries,
          'manifest_self_hash':'excluded to avoid recursive hashing'}
    (ROOT/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return data


if __name__=='__main__':
    print(f"Manifest written: {len(build()['files'])} files")
