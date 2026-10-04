"""Dependency-free static ESM bundler for this offline browser test harness only.

Product sources are not changed. Chromium's environment blocks HTTP navigation;
preview HTTP is separately tested with aiohttp. Here a Python binding supplies
compiler results, while real Chromium runs the UI, hooks, DOM, and interactions.
"""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[2]
IMPORT=re.compile(r"^import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"];?\s*$",re.M)
EXPORT=re.compile(r"\bexport\s+(?:async\s+)?(?:const|let|class|function)\s+([A-Za-z_$][\w$]*)")


def html():
    modules=[];seen=set()
    def visit(path):
        path=path.resolve();key=path.relative_to(ROOT).as_posix()
        if key in seen:return key
        source=path.read_text(encoding='utf-8')
        if key=='tests/browser/harness.js':
            source=source.replace("const api={fetchApi:(path,options)=>fetch(path,options)};",'''const api={fetchApi:async(path,options)=>{
              const result=window.previewFailure
                ? {status:503,data:{error:{code:'unavailable',message:'Test unavailable'}}}
                : await window.__previewRPC(path,JSON.parse(options.body).state_json);
              return {ok:result.status<400,status:result.status,json:async()=>result.data};
            }};''')
            source=source.replace("const initial=await fetch('/tests/fixtures/five_view_state.json').then(r=>r.text());",'const initial='+json.dumps((ROOT/'tests/fixtures/five_view_state.json').read_text())+';')
        def replace_import(match):
            names,relative=match.groups()
            if not relative.startswith('.'):raise ValueError('Only relative test modules are supported')
            dependency=visit(path.parent/relative)
            names=re.sub(r'\s+as\s+',':',names)
            return f'const {{{names}}}=__modules[{json.dumps(dependency)}];'
        source=IMPORT.sub(replace_import,source)
        exported=EXPORT.findall(source)
        source=re.sub(r'\bexport\s+(?=(?:async\s+)?(?:const|let|class|function)\b)','',source)
        source=source.replace('import.meta.url',json.dumps(path.as_uri()))
        seen.add(key)
        modules.append(f'__modules[{json.dumps(key)}]=(()=>{{\n{source}\nreturn {{{",".join(exported)}}};\n}})();')
        return key
    visit(ROOT/'tests/browser/harness.js')
    page=(ROOT/'tests/browser/index.html').read_text()
    styles=(ROOT/'web/style.css').read_text()+'\n'+(ROOT/'tests/upstream/web/style.css').read_text()
    page=page.replace('</head>',f'<link data-q21-character-sheet><link data-h3-character-sheet><style>{styles}</style></head>')
    bundle='const __modules=Object.create(null);\n'+'\n'.join(modules)
    page=page.replace('<script type="module" src="./harness.js"></script>','<script>'+bundle.replace('</script','<\\/script')+'</script>')
    return page
