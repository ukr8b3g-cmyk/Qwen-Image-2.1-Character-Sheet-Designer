import test from 'node:test';
import assert from 'node:assert/strict';
import {installOptionalOutputs} from '../../web/optional_outputs.js';

const names = ['prompt','width','height','layout_image','filename_suffix','reference_plan','sheet_plan','view_records'];
function fixture() {
  const drawn = [], ports = names.map(() => ({style: {}, attrs: {}, getAttribute(k) { return this.attrs[k] ?? null; }, setAttribute(k,v) { this.attrs[k]=v; }, removeAttribute(k) { delete this.attrs[k]; }}));
  const outputs = names.map(name => ({name, links: [], draw() { drawn.push(this.name); }}));
  const node = {outputs, properties: {}, isOutputConnected(index) {return !!this.outputs[index].links.length;}, getOutputOnPos(index) {return this.outputs[index];}, getSlotInPosition(index) {return {output:this.outputs[index],slot:index};}};
  const before = JSON.stringify(outputs), root = {closest() {return {querySelectorAll() {return ports;}};}};
  const ui = installOptionalOutputs(node, root, fn => fn());
  return {node, ui, drawn, ports, before};
}
test('Only unconnected auxiliary outputs are hidden; IDs, order and serialization stay unchanged', () => {
  const {node,ui,drawn,ports,before}=fixture();
  node.outputs.forEach(output => output.draw());
  assert.deepEqual(drawn,['prompt','width','height','layout_image','reference_plan']);
  assert.equal(JSON.stringify(node.outputs),before);
  assert.equal(node.getOutputOnPos(4),undefined); assert.equal(node.getSlotInPosition(7),null);
  assert.equal(node.getSlotInPosition(5).slot,5);
  assert.equal(ports[4].style.visibility,'hidden'); assert.equal(ports[5].style.visibility,undefined);
  ui.dispose();
});
test('Existing connections remain visible and retain their original slot indexes', () => {
  const {node,ui,drawn,ports}=fixture();node.outputs[6].links.push(42); ui.update();
  node.outputs[6].draw(); assert.deepEqual(drawn,['sheet_plan']);
  assert.equal(node.getSlotInPosition(6).slot,6); assert.equal(ports[6].style.visibility,undefined);
  node.outputs[6].links.length=0;ui.update();assert.equal(node.getOutputOnPos(6),undefined);ui.dispose();
});
test('Context menu reveals auxiliary outputs without extra widgets; the choice survives saved properties', () => {
  const {node,ui,drawn}=fixture(), options=[];node.getExtraMenuOptions(null,options);options[0].callback();
  assert.equal(node.properties.qwen_show_auxiliary_outputs,true);
  node.outputs.forEach(output=>output.draw());assert.deepEqual(drawn,names);
  assert.equal(node.getSlotInPosition(7).slot,7); assert.equal(JSON.parse(JSON.stringify(node.properties)).qwen_show_auxiliary_outputs,true);
  ui.dispose();
});
test('Reconfigured slots are wrapped once and removal restores only owned presentation', () => {
  const {node,ui,ports}=fixture(), previous=node.outputs[4], original=previous.draw;
  const next={name:'filename_suffix',links:[],draw(){throw new Error('Hidden slot drawn');}};
  node.outputs[4]=next;ui.update();assert.notEqual(previous.draw,original);next.draw();
  const wrapper=next.draw;ui.update();assert.equal(next.draw,wrapper);
  ui.dispose();assert.equal(Object.hasOwn(node,'getExtraMenuOptions'),false);assert.equal(ports[4].style.visibility,undefined);
});
