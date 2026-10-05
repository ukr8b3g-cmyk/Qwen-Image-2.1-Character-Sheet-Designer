import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
import {DEFAULT_JSON, parseState, serializeState, DesignerController, StateError, getLocale, validatePreview} from '../../web/state.js';
import {createExtension, NODE_TYPE, graphTransaction, previewRequester} from '../../web/integration.js';
import {PROFILE} from '../../web/profile.js';
import {avatarSVG} from '../../web/avatar.js';
import {artworkRect} from '../../web/artwork.js';
const cases=JSON.parse(readFileSync(new URL('../fixtures/state_cases.json',import.meta.url),'utf8'));
for (const c of cases) test(`Python/JS acceptance parity: ${c.id}`,()=>{
  if(c.valid) assert.deepEqual(parseState(c.raw,c.max_resolution),c.normalized);
  else assert.throws(()=>parseState(c.raw,c.max_resolution));
});
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
function preview(raw){
 const state=parseState(raw);
 return {width:1344,height:768,max_resolution:16384,layout:{canvas:[1344,768],feet_y:null,
  panels:state.views.map((id,i)=>({id,rect:[i/state.views.length,0,1/state.views.length,1]}))}};
}
function make(raw=DEFAULT_JSON,options={}) {return new DesignerController({raw,requestPreview:async s=>preview(s),...options});}
test('Qwen identity and route are independent of H3',()=>{
 assert.equal(NODE_TYPE,'QwenImage21CharacterSheetDesigner');
 assert.equal(PROFILE.previewPath,'/qwen_image21_character_sheet_designer/preview');
 assert.equal(createExtension({},{}).name,'qwen21.CharacterSheetDesigner');
 assert.equal(createExtension({},{}).nodeCreated({type:'H3CharacterSheetDesigner'}),undefined);
});
test('v1 restores without migration; real part edit moves to v2',async()=>{
 const c=make(); assert.equal(c.raw,DEFAULT_JSON);
 c.setPartPrompt('hands',' \n\t');assert.equal(c.state.schema_version,1);
 c.setPartPrompt('hands','革手袋🧤\n  ');assert.equal(c.state.schema_version,2);
 assert.equal(c.state.part_prompts.hands,'革手袋🧤\n  ');
 const saved=c.raw;c.preset('single');assert.equal(c.state.part_prompts.hands,'革手袋🧤\n  ');
 c.restore(saved);assert.equal(c.raw,saved);c.dispose();
});
test('invalid restore keeps original, does not fall back or migrate',()=>{
 const c=make('{broken'); assert.equal(c.raw,'{broken');assert.equal(c.state,null);
 c.restore(DEFAULT_JSON);assert.equal(c.raw,DEFAULT_JSON);assert.equal(c.state.schema_version,1);c.dispose();
});
test('canonical source updates synchronously, preview never writes it',async()=>{
 let canonical=DEFAULT_JSON;const commits=[];
 const c=make(DEFAULT_JSON,{readRaw:()=>canonical,writeRaw:v=>canonical=v,onCommit:(...args)=>commits.push(args)});
 c.toggle('feet');const saved=canonical;assert(parseState(saved).views.includes('feet'));
 await tick();assert.equal(canonical,saved);assert.equal(commits.length,1);
 canonical=DEFAULT_JSON;assert.equal(c.syncFromSource(),true);assert.equal(c.state.views.length,4);c.dispose();
});
test('late preview response cannot replace newer state/preview',async()=>{
 const requests=[];const c=make(DEFAULT_JSON,{requestPreview:raw=>new Promise(resolve=>requests.push({raw,resolve}))});
 c.toggle('feet');assert.equal(requests.length,2);
 requests[1].resolve(preview(requests[1].raw));await tick();const current=c.preview;
 requests[0].resolve(preview(requests[0].raw));await tick();assert.equal(c.preview,current);assert.equal(c.previewRaw,c.raw);c.dispose();
});
test('manual mode requires current preview, manual dimensions remain on view changes',async()=>{
 const c=make();assert.throws(()=>c.setMode('manual'),StateError);await tick();
 c.setMode('manual');c.setSize('manual_width','2240');c.toggle('feet');
 assert.equal(c.state.size.manual_width,2240);assert.equal(c.state.size.manual_height,768);
 assert.throws(()=>c.setSize('manual_height','768.0'));c.dispose();
});
test('last view protection and per-instance isolation',()=>{
 const a=make(),b=make();a.preset('single');assert.throws(()=>a.toggle('body_front'));
 a.setPartPrompt('face','青い目');assert.equal(b.state.schema_version,1);a.dispose();b.dispose();
});
test('failed and timed out preview leaves canonical state valid',async()=>{
 const c=make(DEFAULT_JSON,{requestPreview:()=>new Promise(()=>{}),timeoutMs:5});
 await new Promise(r=>setTimeout(r,15));assert.equal(c.raw,DEFAULT_JSON);assert.equal(c.previewError.code,'timeout');c.dispose();
});
test('balanced transaction callbacks and propagated errors',()=>{
 const calls=[];const node={graph:{beforeChange:()=>calls.push('before'),afterChange:()=>calls.push('after')}};
 assert.throws(()=>graphTransaction(node,()=>{throw Error('test')},{emitBeforeChange:()=>calls.push('canvas before'),emitAfterChange:()=>calls.push('canvas after')}));
 assert.deepEqual(calls,['canvas before','before','after','canvas after']);
});
test('locale uses only primary ja and safe English fallback',()=>{
 for(const [value,expected] of [['ja-JP','ja'],['JA_jp','ja'],['en','en'],['zh-CN','en'],[null,'en']])
 assert.equal(getLocale({extensionManager:{setting:{get:()=>value}}}),expected);
 assert.equal(getLocale({extensionManager:{setting:{get:()=>{throw Error()}}}}),'en');
});
test('preview rejects bad geometry and mismatched canvas',()=>{
 const state=parseState(DEFAULT_JSON),p=preview(DEFAULT_JSON);p.layout.canvas=[1,2];assert.throws(()=>validatePreview(p,state));
 p.layout.canvas=[1344,768];p.layout.panels[0].rect=[0,0,Infinity,1];assert.throws(()=>validatePreview(p,state));
});
test('request uses exact Qwen endpoint and strict envelope',async()=>{
 let seen;const fn=previewRequester({fetchApi:async(...args)=>{seen=args;return {ok:true,json:async()=>({test:true})}}});
 assert.deepEqual(await fn(DEFAULT_JSON),{test:true});assert.equal(seen[0],PROFILE.previewPath);
 assert.deepEqual(JSON.parse(seen[1].body),{state_json:DEFAULT_JSON});
});
test('preview follows the layout-reference widget without changing saved state',async()=>{
 let enabled=true,seen;
 const fn=previewRequester({fetchApi:async(_,args)=>{seen=JSON.parse(args.body);return {ok:true,json:async()=>({})}}},()=>enabled);
 await fn(DEFAULT_JSON);assert.deepEqual(seen,{state_json:DEFAULT_JSON,use_layout_image:true});
 enabled=false;await fn(DEFAULT_JSON);assert.deepEqual(seen,{state_json:DEFAULT_JSON});
});
test('local artwork IDs are safe, distinct and all seven views are supported',()=>{
 for(const view of parseState(serializeState({...parseState(DEFAULT_JSON),views:['face_front','face_left','body_front','body_left','body_back','hands','feet']})).views){
  const a=avatarSVG(view,'<script>"'),b=avatarSVG(view,'<script>"');
  assert(!a.includes('<script>'));assert.notEqual(a,b);assert.equal(artworkRect(view).length,4);
 }
 assert.throws(()=>avatarSVG('unknown'));assert.throws(()=>artworkRect('unknown'));
});
