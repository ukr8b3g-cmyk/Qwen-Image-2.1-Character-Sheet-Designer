import test from 'node:test';
import assert from 'node:assert/strict';
import {installAssemblyUI} from '../../web/sheet_assembly_ui.js';

class Element {
  constructor(tag) { this.tag = tag; this.style = {}; this.dataset = {}; this.children = []; this.events = {}; this.attrs = {}; this.hidden = false; }
  append(...items) { for (const item of items) { item.parent = this; this.children.push(item); } }
  remove() { this.parent.children = this.parent.children.filter(item => item !== this); }
  addEventListener(name, fn) { this.events[name] = fn; }
  removeEventListener(name) { delete this.events[name]; }
  setAttribute(name, value) { this.attrs[name] = value; }
  reportValidity() { return true; }
  getContext() { return {fillRect() {}, strokeRect() {}, fillText() {}}; }
}
function fixture(run) {
  const previous = globalThis.document;
  globalThis.document = {createElement: tag => new Element(tag)};
  try {
    const root = new Element('section'), head = new Element('div'), tag = new Element('span'), stage = new Element('div');
    stage.style.position = ''; head.append(tag); root.append(head, stage);
    root.querySelector = selector => ({'.q21-mr-preview-head': head, '.q21-mr-preview-tag': tag, '[data-preview-stage]': stage})[selector];
    const widgets = [{name: 'batch_out', value: false}, {name: 'sheet_size_mode', value: 'manual'}, {name: 'sheet_width', value: 864}, {name: 'sheet_height', value: 1536}];
    const node = {widgets, outputs: [{name: 'sheet_plan', links: []}]};
    const plan = {canvas: [2816, 1280], plan_hash: 'original', views: [{view_id: 'feet', bounds: [12, 12, 2700, 1200]}]};
    const designer = {ui: {root}, controller: {preview: {sheet_plan: plan}, isCurrentPreview: true}};
    const writes = [];
    const ui = installAssemblyUI(node, designer, (widget, value) => { writes.push([widget.name, value]); widget.value = value; });
    run({root, head, tag, stage, node, widgets, plan, ui, writes, toggle: head.children[1], overlay: stage.children[0]});
  } finally { globalThis.document = previous; }
}
test('Standard UI adds no root row, keeps Layout, hides only assembly widgets and preserves values', () => fixture(({root, toggle, overlay, widgets, tag}) => {
  assert.equal(root.children.length, 2);
  assert.equal(toggle.hidden, true); assert.equal(overlay.hidden, true); assert.equal(tag.hidden, false);
  assert.deepEqual(widgets.map(widget => widget.value), [false, 'manual', 864, 1536]);
  assert.equal(widgets[0].hidden, undefined);
  assert.ok(widgets.slice(1).every(widget => widget.hidden));
}));
test('Assembly is available only when linked, Batch Out ON and Layout visible', () => fixture(({node, widgets, ui, toggle, overlay, stage, tag}) => {
  node.outputs[0].links = [1]; ui.update(); assert.equal(toggle.hidden, true);
  widgets[0].value = true; ui.update(); assert.equal(toggle.hidden, false); assert.equal(tag.hidden, true);
  toggle.events.click(); assert.equal(overlay.hidden, false);
  stage.hidden = true; ui.update(); assert.equal(toggle.hidden, true); assert.equal(overlay.hidden, true);
  stage.hidden = false; ui.update(); assert.equal(overlay.hidden, true);
  toggle.events.click(); node.outputs[0].links = []; ui.update(); assert.equal(overlay.hidden, true);
}));
test('Auto display does not overwrite Manual dimensions; edit writes only its canonical widget', () => fixture(({node, widgets, ui, overlay, writes}) => {
  node.outputs[0].links = [1]; widgets[0].value = true; ui.update();
  const inputs = overlay.children[0].children.map(label => label.children[1]);
  inputs[0].value = 'auto'; inputs[0].events.change();
  assert.deepEqual(inputs.map(input => input.value), ['auto', '2816', '1280']);
  assert.equal(inputs[1].disabled, true); assert.equal(widgets[2].value, 864); assert.equal(widgets[3].value, 1536);
  inputs[0].value = 'manual'; inputs[0].events.change();
  assert.equal(inputs[1].value, '864'); assert.equal(inputs[2].value, '1536');
  inputs[1].value = '1024'; inputs[1].events.change();
  assert.equal(widgets[2].value, 1024); assert.equal(widgets[3].value, 1536);
  assert.deepEqual(writes, [['sheet_size_mode', 'auto'], ['sheet_size_mode', 'manual'], ['sheet_width', 1024]]);
}));
test('Composition preview uses server plan unchanged and never replaces the generation preview', () => fixture(({node, widgets, ui, toggle, overlay, plan}) => {
  node.outputs[0].links = [1]; widgets[0].value = true; ui.update(); toggle.events.click();
  const canvas = overlay.children[1].children[0];
  assert.equal(canvas.width, 2816); assert.equal(canvas.height, 1280);
  assert.equal(canvas.dataset.panelBounds, JSON.stringify(plan.views));
  assert.deepEqual(plan.canvas, [2816, 1280]);
}));
test('Removal restores widget visibility and removes only owned presentation', () => fixture(({root, head, stage, widgets, ui, tag}) => {
  ui.dispose(); assert.equal(root.children.length, 2); assert.equal(head.children.length, 1); assert.equal(stage.children.length, 0);
  assert.equal(tag.hidden, false); assert.equal(stage.style.position, '');
  assert.ok(widgets.slice(1).every(widget => widget.hidden === undefined));
}));
test('Enter and blur commit sizes, while invalid input cannot replace canonical values', () => fixture(({overlay, widgets, writes}) => {
  const width = overlay.children[0].children[1].children[1];
  assert.equal(width.required, true);
  width.value = '1024'; width.events.keydown({key: 'Enter'}); assert.equal(widgets[2].value, 1024);
  width.value = '768'; width.events.blur(); assert.equal(widgets[2].value, 768);
  width.reportValidity = () => false; width.value = ''; width.events.keydown({key: 'Enter'});
  assert.equal(widgets[2].value, 768); assert.equal(writes.length, 2);
}));
