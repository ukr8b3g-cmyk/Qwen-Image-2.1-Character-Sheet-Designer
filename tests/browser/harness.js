import {createExtension, getDesigner} from '../../web/integration.js';
import {DEFAULT_JSON} from '../../web/state.js';
import {createExtension as createH3, getDesigner as getH3} from '../upstream/web/integration.js';

// Host behavior is an explicit test double, not the real ComfyUI/Pinia runtime.
let locale='ja', nextId=0, snapshotBefore=null;
const undoStack=[],redoStack=[],trace=[];
const settings=new EventTarget();
const api={fetchApi:(path,options)=>fetch(path,options)};
const graph={_nodes:[],beforeChange(){trace.push('graph-before')},afterChange(){trace.push('graph-after')}};
const values=()=>graph._nodes.map(n=>({id:n.id,value:n.widgets[0].value}));
const app={graph,ui:{settings},extensionManager:{setting:{get:()=>locale},toast:{add:message=>trace.push({toast:message})}},canvas:{
 emitBeforeChange(){trace.push('canvas-before');snapshotBefore=values()},
 emitAfterChange(){trace.push('canvas-after');if(snapshotBefore){undoStack.push(snapshotBefore);redoStack.length=0;snapshotBefore=null}},
}};
const qext=createExtension(app,api),hext=createH3(app,api);
function restoreValues(items){for(const v of items){const node=graph._nodes.find(n=>n.id===v.id);if(node){node.widgets[0].value=v.value;node.onConfigure?.({});}}qext.afterConfigureGraph();hext.afterConfigureGraph();}
function undo(){const previous=undoStack.pop();if(previous){redoStack.push(values());restoreValues(previous)}}
function redo(){const next=redoStack.pop();if(next){undoStack.push(values());restoreValues(next)}}
function setLocale(value){locale=value;settings.dispatchEvent(new Event('Comfy.Locale.change'))}
class Node {
 constructor(type,raw=DEFAULT_JSON,{throwDOM=false}={}){
  this.id=++nextId;this.type=type;this.comfyClass=type;this.size=[870,930];this.graph=graph;
  this.host=document.createElement('article');this.host.className='host';this.host.dataset.node=String(this.id);
  const title=document.createElement('div');title.className='node-title';title.textContent=type;
  this.surface=document.createElement('div');this.surface.className='surface';this.host.append(title,this.surface);
  const text=document.createElement('textarea');text.className='native';text.value=raw;this.surface.append(text);
  let backing=raw;const widget={name:'state_json',element:text,hidden:false,options:{},callback(){return 'official-callback'}};
  widget.options.setValue=function(value){if(this!==widget.options)throw Error('Changed setter receiver');backing=value;text.value=value;return 'official-setter'};
  Object.defineProperty(widget,'value',{configurable:true,enumerable:true,get(){return backing},set(v){widget.options.setValue(v)}});
  this.originalDescriptor=Object.getOwnPropertyDescriptor(widget,'value');this.originalSetter=widget.options.setValue;
  text.addEventListener('input',()=>{widget.value=text.value});this.widgets=[widget];
  this.throwDOM=throwDOM;this.priorRemoved=0;this.priorConfigured=0;
  this.onRemoved=()=>{this.priorRemoved++;return 'prior-removed'};
  this.onConfigure=()=>{this.priorConfigured++;return 'prior-configure'};
 }
 addDOMWidget(name,type,element,options){
  const widget={name,type,element,options};this.widgets.push(widget);this.surface.append(element);
  // Simulate positional restoration during addDOMWidget; it must be ignored.
  options.setValue?.('NOT_CANONICAL_POSITIONAL_DATA');
  if(this.throwDOM)throw Error('Simulated partial widget insertion');
  return widget;
 }
 removeWidget(widget){widget.onRemove?.();this.widgets.splice(this.widgets.indexOf(widget),1);widget.element?.remove()}
 setDirtyCanvas(){}
 setSize(value){this.size=value}
 onWidgetChanged(name,next,previous,widget){trace.push({name,next,previous,canonical:widget===this.widgets[0]})}
}
function add(type='QwenImage21CharacterSheetDesigner',raw=DEFAULT_JSON,options){
 const node=new Node(type,raw,options);graph._nodes.push(node);document.querySelector('#nodes').append(node.host);
 qext.nodeCreated(node);hext.nodeCreated(node);node.onAdded?.();return node;
}
function remove(node){node.onRemoved?.();graph._nodes.splice(graph._nodes.indexOf(node),1);node.graph=null;node.host.remove()}
function readd(node){node.graph=graph;graph._nodes.push(node);document.querySelector('#nodes').append(node.host);node.onAdded?.()}
function payload(){return Object.fromEntries(graph._nodes.map(n=>[n.id,{class_type:n.type,inputs:{state_json:n.widgets[0].value}}]))}
function serialize(){return graph._nodes.map(n=>({id:n.id,type:n.type,widgets_values:n.widgets.filter(w=>w.serialize!==false&&w.options.serialize!==false).map(w=>w.value)}))}
function saveRestore(node){const saved=serialize().find(n=>n.id===node.id);node.widgets[0].value=saved.widgets_values[0];node.onConfigure?.(saved);return saved}
const initial=await fetch('/tests/fixtures/five_view_state.json').then(r=>r.text());
const qwen=add('QwenImage21CharacterSheetDesigner',initial.trim()),h3=add('H3CharacterSheetDesigner');
document.querySelector('#undo').onclick=undo;document.querySelector('#redo').onclick=redo;
document.querySelector('#ja').onclick=()=>setLocale('ja');document.querySelector('#en').onclick=()=>setLocale('en');
window.harness={app,api,graph,trace,qwen,h3,add,remove,readd,payload,serialize,saveRestore,undo,redo,setLocale,getDesigner,getH3};
