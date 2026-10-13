import {createExtension as createLegacy, getDesigner as getLegacy} from '../../web/integration.js';
import {createExtension, getDesigner} from '../../web/multi_integration.js';
import {DEFAULT_JSON} from '../../web/state.js';
import {DEFAULT_MULTI_JSON} from '../../web/multi_state.js';

// This host double is intentionally separate from actual Frontend acceptance.
let locale = 'ja', nextId = 0, before = null;
const undoStack = [], redoStack = [], settings = new EventTarget();
const graph = {_nodes: [], beforeChange() {}, afterChange() {}};
const snapshot = () => graph._nodes.map(n => ({id:n.id, values:n.widgets.slice(0,3).map(w=>w.value)}));
const app = {graph, ui:{settings}, extensionManager:{setting:{get:()=>locale}}, canvas:{
  emitBeforeChange() { before=snapshot(); },
  emitAfterChange() { if(before) {undoStack.push(before);redoStack.length=0;before=null;} },
}};
const api = {fetchApi:(path, options)=>fetch(path, options)};
const oldExtension = createLegacy(app, api), extension = createExtension(app, api);
class Node {
  constructor(type, raw, legacy=false) {
    this.id=++nextId;this.type=this.comfyClass=type;this.graph=graph;this.size=legacy?[870,1100]:[1060,1350];
    this.inputs=['character_image','reference_image_1','reference_image_2'].map((name,i)=>({name,link:i===0?1:null}));
    this.host=document.createElement('article');this.host.className=`host${legacy?' legacy':''}`;
    const title=document.createElement('div');title.className='node-title';title.textContent=type;
    this.surface=document.createElement('div');this.surface.className='surface';this.host.append(title,this.surface);
    const text=document.createElement('textarea');text.className='native';text.value=raw;this.surface.append(text);
    const canonical={name:'state_json',element:text,options:{},hidden:false};
    canonical.options.setValue=value=>{text.value=value;};
    Object.defineProperty(canonical,'value',{get:()=>text.value,set:value=>canonical.options.setValue(value)});
    this.widgets=[canonical,{name:'use_layout_image',value:false,options:{}},{name:'style',value:'none',options:{}}];
  }
  addDOMWidget(name,type,element,options) {
    const widget={name,type,element,options};this.widgets.push(widget);this.surface.append(element);return widget;
  }
  removeWidget(widget) {widget.onRemove?.();this.widgets.splice(this.widgets.indexOf(widget),1);widget.element?.remove();}
  setSize(size) {this.size=size;this.host.style.width=`${size[0]}px`;this.surface.style.height=`${size[1]}px`;}
  setDirtyCanvas() {}
  isInputConnected(slot) {return this.inputs[slot]?.link!=null;}
}
function add(type,raw,legacy=false) {
  const node=new Node(type,raw,legacy);graph._nodes.push(node);document.querySelector('#nodes').append(node.host);
  oldExtension.nodeCreated(node);extension.nodeCreated(node);node.onAdded?.();return node;
}
function restore(rows) {
  for(const row of rows) {const n=graph._nodes.find(n=>n.id===row.id);row.values.forEach((v,i)=>{n.widgets[i].value=v;});n.onConfigure?.({});}
  oldExtension.afterConfigureGraph();extension.afterConfigureGraph();
}
function undo() {const row=undoStack.pop();if(row){redoStack.push(snapshot());restore(row);}}
function redo() {const row=redoStack.pop();if(row){undoStack.push(snapshot());restore(row);}}
function setLocale(value) {locale=value;settings.dispatchEvent(new Event('Comfy.Locale.change'));}
const multi=add('QwenImage21CharacterSheetDesignerMultiReference',DEFAULT_MULTI_JSON);
const legacy=add('QwenImage21CharacterSheetDesigner',DEFAULT_JSON,true);
document.querySelector('#undo').onclick=undo;document.querySelector('#redo').onclick=redo;
document.querySelector('#ja').onclick=()=>setLocale('ja');document.querySelector('#en').onclick=()=>setLocale('en');
document.querySelector('#layout').onclick=()=>{multi.widgets[1].value=!multi.widgets[1].value;getDesigner(multi).sync();};
for(const [id,slot] of [['extra1',1],['extra2',2]]) document.querySelector(`#${id}`).onclick=()=>{multi.inputs[slot].link=multi.inputs[slot].link==null?slot+1:null;getDesigner(multi).sync();};
window.multiHarness={app,api,graph,multi,legacy,add,undo,redo,setLocale,getDesigner,getLegacy,snapshot};
