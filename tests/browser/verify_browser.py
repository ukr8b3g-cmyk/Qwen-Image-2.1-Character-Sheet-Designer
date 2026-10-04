"""Real Chromium and DOM; compiler binding and simulated ComfyUI host. HTTP is tested separately."""
import argparse
import json
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tests.browser.offline_bundle import html
from qwen_image21_character_sheet.compiler import compile_state
from tests.upstream.h3_compiler import compile_state as h3_compile


def run(url, executable):
    checks=[];errors=[]
    def check(name,value):
        if not value:raise AssertionError(name)
        checks.append({"name":name,"status":"pass"})
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={"width":1000,"height":1150},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        def preview_rpc(path,raw):
            try:
                result=(h3_compile if path.startswith('/h3_') else compile_state)(raw)
                return {"status":200,"data":result}
            except ValueError as exc:
                return {"status":400,"data":{"error":{"code":getattr(exc,'code','invalid_state'),"message":str(exc)}}}
        page.expose_function('__previewRPC',preview_rpc)
        page.set_content(html());page.wait_for_function('window.harness?.getDesigner(harness.qwen)?.controller.isCurrentPreview')
        q=page.locator('[data-node="1"]')
        check('seven cards / five restored panels',q.locator('[data-view]').count()==7 and q.locator('[data-panel]').count()==5)
        check('preserved 2816x1280 five-view state',page.evaluate('harness.getDesigner(harness.qwen).controller.preview.width')==2816)
        check('one canonical and one nonserialized widget',page.evaluate('harness.qwen.widgets.length===2 && harness.serialize()[0].widgets_values.length===1 && harness.qwen.widgets[0].name==="state_json"'))
        check('no canonical getter/setter replacement',page.evaluate('Object.getOwnPropertyDescriptor(harness.qwen.widgets[0],"value").set === harness.qwen.originalDescriptor.set'))
        check('H3 and Qwen independent extension records',page.evaluate('harness.getDesigner(harness.h3)===undefined && harness.getH3(harness.qwen)===undefined && !!harness.getH3(harness.h3)'))
        check('separate stylesheet namespaces',page.locator('link[data-q21-character-sheet]').count()==1 and page.locator('link[data-h3-character-sheet]').count()==1)
        page.screenshot(path=str(ROOT/'verification/ui_ja.png'),full_page=False)
        before=page.evaluate('harness.qwen.widgets[0].value')
        q.locator('[data-view="hands"]').click();check('view commit before preview',page.evaluate('JSON.parse(harness.payload()[1].inputs.state_json).views.includes("hands")'))
        page.evaluate('harness.undo()');check('undo canonical restoration',page.evaluate('harness.qwen.widgets[0].value')==before)
        page.evaluate('harness.redo()');check('redo canonical restoration',page.evaluate('JSON.parse(harness.qwen.widgets[0].value).views.includes("hands")'))
        q.locator('[data-tab="parts"]').click();q.locator('[data-part-select]').select_option('back_clothing')
        literal='背中に白い三日月 🌙\n  <Subject 1> <script>alert(1)</script>  '
        q.locator('[data-part-prompt]').fill(literal)
        check('Japanese, emoji, newlines and markup saved literally',page.evaluate('JSON.parse(harness.qwen.widgets[0].value).part_prompts.back_clothing')==literal)
        check('user text not executed as HTML',q.locator('script').count()==0)
        check('modeled queue payload latest raw',page.evaluate('harness.payload()[1].inputs.state_json===harness.qwen.widgets[0].value'))
        saved=page.evaluate('harness.saveRestore(harness.qwen)');check('save/load has only state_json',len(saved['widgets_values'])==1)
        page.evaluate('harness.setLocale("en")');check('English locale',q.locator('section').get_attribute('lang')=='en')
        page.screenshot(path=str(ROOT/'verification/ui_parts_en.png'),full_page=False)
        page.evaluate('harness.setLocale("ja-JP")');check('Japanese language subtag',q.locator('section').get_attribute('lang')=='ja')
        q.locator('[data-tab="layout"]').click()
        page.wait_for_function('harness.getDesigner(harness.qwen).controller.isCurrentPreview')
        q.locator('[data-mode="manual"]').click()
        width=q.locator('[data-field="manual_width"]');width.fill('2240');width.press('Enter')
        check('manual numeric commit',page.evaluate('JSON.parse(harness.qwen.widgets[0].value).size.manual_width')==2240)
        width.fill('2241');width.press('Enter')
        check('invalid numeric draft preserves canonical and shows error',page.evaluate('JSON.parse(harness.qwen.widgets[0].value).size.manual_width')==2240 and width.get_attribute('aria-invalid')=='true')
        width.press('Escape');q.locator('[data-view="feet"]').click()
        check('manual dimensions retained after view change',page.evaluate('JSON.parse(harness.qwen.widgets[0].value).size.manual_width')==2240)
        for i in range(5):
            page.evaluate('harness.remove(harness.qwen);harness.readd(harness.qwen)')
        page.wait_for_function('harness.getDesigner(harness.qwen).controller.isCurrentPreview')
        check('five remove/re-add cycles no duplicate DOM widgets',page.evaluate('harness.qwen.widgets.length===2') and q.locator('section.q21-designer').count()==1)
        check('prior hooks still invoked',page.evaluate('harness.qwen.priorRemoved===5 && harness.qwen.priorConfigured>0'))
        check('setter receiver and return retained',page.evaluate('harness.qwen.widgets[0].options.setValue(harness.qwen.widgets[0].value)==="official-setter"'))
        page.evaluate('harness.qwen.widgets[0].value="{broken";harness.qwen.onConfigure({})')
        check('invalid saved JSON not replaced',page.evaluate('harness.qwen.widgets[0].value')=='{broken' and q.locator('.q21-json-editor').is_visible())
        q.locator('.q21-json-editor textarea').fill(before);q.locator('.q21-apply').click()
        page.wait_for_function('harness.getDesigner(harness.qwen).controller.isCurrentPreview')
        check('explicit JSON repair recovers',page.evaluate('harness.qwen.widgets[0].value')==before)
        page.evaluate('window.previewFailure=true')
        page.evaluate('harness.getDesigner(harness.qwen).controller.refreshPreview()')
        page.wait_for_function('!!harness.getDesigner(harness.qwen).controller.previewError')
        check('API failure retains raw and exposes raw editor',page.evaluate('harness.qwen.widgets[0].value')==before and q.locator('.q21-json-editor').is_visible())
        page.evaluate('window.previewFailure=false')
        page.evaluate('harness.getDesigner(harness.qwen).controller.refreshPreview()')
        page.wait_for_function('harness.getDesigner(harness.qwen).controller.isCurrentPreview')
        page.evaluate('window.brokenNode=harness.add("QwenImage21CharacterSheetDesigner",harness.qwen.widgets[0].value,{throwDOM:true})')
        check('partial insertion rollback restores native input',page.evaluate('brokenNode.widgets.length===1 && !brokenNode.widgets[0].hidden && !brokenNode.widgets[0].element.hidden && !harness.getDesigner(brokenNode)'))
        check('no JavaScript runtime errors',errors==[])
        browser.close()
    return {"status":"pass","scope":"Real Chromium offline harness with real compiler via binding; simulated ComfyUI host/transport, no real Queue or GPU", "checks":checks,"page_errors":errors}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',default='http://127.0.0.1:8197/tests/browser/index.html');parser.add_argument('--chromium',default='/usr/bin/chromium');args=parser.parse_args()
    result=run(args.url,args.chromium)
    (ROOT/'verification/browser_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
