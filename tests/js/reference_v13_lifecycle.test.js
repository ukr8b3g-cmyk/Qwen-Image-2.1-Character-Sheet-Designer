import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

if (process.argv.includes('--lifecycle-child')) {
  class Element {
    constructor(tag) { this.tag = tag; this.style = {}; this.dataset = {}; this.children = []; this.events = {}; this.attrs = {}; this.hidden = false; }
    append(...items) { for (const item of items) { item.parent = this; this.children.push(item); } }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(item => item !== this); }
    addEventListener(name, fn) { this.events[name] = fn; }
    removeEventListener(name) { delete this.events[name]; }
    setAttribute(name, value) { this.attrs[name] = value; }
    reportValidity() { return true; }
    getContext() { return {fillRect() {}, strokeRect() {}, fillText() {}}; }
  }
  let extension, serial = 0;
  const frames = new Map(), requests = [];
  const requestAnimationFrame = fn => { const id = ++serial; frames.set(id, fn); return id; };
  const cancelAnimationFrame = id => frames.delete(id);
  const context = vm.createContext({console, document: {createElement: tag => new Element(tag)}, window: {requestAnimationFrame, cancelAnimationFrame}, requestAnimationFrame, cancelAnimationFrame, setInterval, clearInterval, AbortController});
  const graph = {beforeChange() {}, afterChange() {}, _nodes: []};
  const app = {graph, canvas: {emitBeforeChange() {}, emitAfterChange() {}}, registerExtension(value) { extension = value; }};
  const api = {fetchApi: async (path, options) => { requests.push(JSON.parse(options.body)); return {ok: true, json: async () => ({})}; }};
  class Controller {
    constructor(args) { this.args = args; this.restores = 0; }
    syncFromSource() {}
    refreshPreview() { return this.args.requestPreview(this.args.readRaw()); }
    restore() { this.restores++; }
    dispose() { this.disposed = true; }
  }
  const fakeUi = () => {
    const root = new Element('section'), head = new Element('div'), tag = new Element('span'), stage = new Element('div');
    stage.style.position = ''; head.append(tag); root.append(head, stage);
    root.querySelector = selector => ({'.q21-mr-preview-head': head, '.q21-mr-preview-tag': tag, '[data-preview-stage]': stage})[selector];
    return {root, render() {}, setLocale() {}, dispose() { root.remove(); }};
  };
  const stubs = {
    '../../scripts/app.js': {app}, '../../scripts/api.js': {api},
    './state.js': {getLocale: () => 'en', subscribeLocale: () => () => {}},
    './multi_ui.js': {createDesignerUI: fakeUi, translations: {en: {fallback: 'fallback'}}},
    './multi_state.js': {MultiReferenceController: Controller, REFERENCE_INPUTS: ['reference_image_1', 'reference_image_2', 'reference_image_3']},
    './multi_profile.js': {PROFILE: {nodeType: 'legacy', extensionName: 'legacy'}},
  };
  const modules = new Map();
  async function moduleFor(name) {
    if (modules.has(name)) return modules.get(name);
    let module;
    if (stubs[name]) {
      const values = stubs[name];
      module = new vm.SyntheticModule(Object.keys(values), function() { for (const [key, value] of Object.entries(values)) this.setExport(key, value); }, {context, identifier: name});
    } else {
      module = new vm.SourceTextModule(readFileSync(new URL(`../../web/${name.slice(2)}`, import.meta.url), 'utf8'), {context, identifier: name});
    }
    modules.set(name, module); await module.link(moduleFor); return module;
  }
  await (await moduleFor('./qwen_image21_character_sheet_designer_reference_v13.js')).evaluate();
  const integration = modules.get('./multi_integration.js').namespace;
  const names = ['prompt', 'width', 'height', 'layout_image', 'filename_suffix', 'reference_plan', 'sheet_plan', 'view_records'];
  function nodeFixture(saved) {
    const ports = names.map(() => ({style: {}, attrs: {}, getAttribute(key) { return this.attrs[key] ?? null; }, setAttribute(key, value) { this.attrs[key] = value; }, removeAttribute(key) { delete this.attrs[key]; }}));
    const node = {
      type: 'QwenImage21CharacterSheetDesignerReferenceV13', graph, properties: saved?.properties ?? {}, inputs: [], size: [1060, 1460],
      outputs: names.map(name => ({name, links: name === 'sheet_plan' ? [99] : [], draw() { return this.name; }})),
      widgets: [{name: 'state_json', value: saved?.raw ?? '{"schema_version":3}', options: {}}, {name: 'style', value: 'none', options: {}}, {name: 'use_layout_image', value: false}, {name: 'batch_out', value: true}, {name: 'sheet_size_mode', value: 'manual'}, {name: 'sheet_width', value: 1536}, {name: 'sheet_height', value: 864}],
      addDOMWidget(name, type, element, options) { element.closest = () => ({querySelectorAll: () => ports}); const widget = {name, type, element, options}; this.widgets.push(widget); return widget; },
      removeWidget(widget) { this.widgets.splice(this.widgets.indexOf(widget), 1); },
      setDirtyCanvas() {}, setSize(value) { this.size = value; },
      getOutputOnPos(index) { return this.outputs[index]; }, getSlotInPosition(index) { return {output: this.outputs[index], slot: index}; },
      isOutputConnected(index) { return !!this.outputs[index].links.length; },
      added: 0, removed: 0, onAdded() { this.added++; return 'added'; }, onRemoved() { this.removed++; return 'removed'; },
    };
    graph._nodes.push(node); return {node, ports};
  }
  const values = node => node.widgets.filter(widget => !widget.name.startsWith('q21_mr_designer_ui')).map(({name, value}) => [name, value]);
  function checkInstalled(node, hidden = true) {
    const designer = integration.getDesigner(node); assert.ok(designer);
    assert.equal(node.widgets.filter(widget => widget.name.startsWith('q21_mr_designer_ui')).length, 1);
    assert.equal(node.widgets.filter(widget => widget.name === 'state_json').length, 1);
    const head = designer.ui.root.querySelector('.q21-mr-preview-head');
    const toggles = head.children.filter(element => element.dataset.sheetAssemblyToggle !== undefined);
    assert.equal(toggles.length, 1); assert.equal(toggles[0].hidden, false);
    const menu = []; node.getExtraMenuOptions(null, menu); assert.equal(menu.length, 1);
    assert.equal(node.getOutputOnPos(4) === undefined, hidden);
    assert.equal(node.getOutputOnPos(6), node.outputs[6]); assert.equal(node.getSlotInPosition(6).slot, 6);
    assert.ok(node.widgets.filter(widget => widget.name.startsWith('sheet_')).every(widget => widget.hidden === true));
    assert.equal(frames.size, 2); return {designer, menu, toggle: toggles[0]};
  }
  const scenario = process.argv.at(-1), {node, ports} = nodeFixture();
  const original = JSON.stringify(values(node));
  if (scenario === 'legacy') {
    node.type = 'legacy'; const legacy = integration.createExtension(app, api);
    legacy.nodeCreated(node); assert.ok(integration.getDesigner(node)); assert.equal(frames.size, 1);
    node.onRemoved(); assert.equal(frames.size, 0); node.onAdded();
    assert.ok(integration.getDesigner(node)); assert.equal(frames.size, 1); assert.equal(node.getExtraMenuOptions, undefined);
    node.onRemoved(); assert.equal(frames.size, 0);
  } else if (scenario === 'fallback') {
    delete node.addDOMWidget; extension.nodeCreated(node);
    assert.equal(integration.getDesigner(node), undefined); assert.equal(node.getExtraMenuOptions, undefined); assert.equal(frames.size, 0);
  } else {
    extension.nodeCreated(node); assert.equal(node.onAdded(), 'added'); checkInstalled(node);
    if (scenario === 'readd' || scenario === 'refresh') {
      for (let cycle = 0; cycle < 3; cycle++) {
        const old = integration.getDesigner(node); assert.equal(node.onRemoved(), 'removed'); node.graph = null;
        assert.equal(frames.size, 0); assert.equal(node.getExtraMenuOptions, undefined); assert.equal(ports[4].style.visibility, undefined);
        node.graph = graph; assert.equal(node.onAdded(), 'added');
        const {designer} = checkInstalled(node); assert.notEqual(designer, old); assert.ok(old.controller.disposed);
        extension.afterConfigureGraph(); assert.equal(designer.controller.restores, 1);
        assert.equal(node.added, cycle + 2); assert.equal(node.removed, cycle + 1);
      }
      if (scenario === 'refresh') {
        node.widgets.find(widget => widget.name === 'sheet_width').value = 1664;
        for (const [id, callback] of [...frames]) { frames.delete(id); callback(); }
        assert.equal(requests.length, 1); assert.equal(requests[0].sheet_width, 1664); assert.equal(frames.size, 2);
        node.widgets.find(widget => widget.name === 'sheet_width').value = 1536;
      }
    } else if (scenario === 'reload') {
      const {menu} = checkInstalled(node); menu[0].callback(); checkInstalled(node, false);
      const saved = JSON.parse(JSON.stringify({properties: node.properties, raw: node.widgets.find(widget => widget.name === 'state_json').value}));
      node.onRemoved(); graph._nodes.length = 0;
      const restored = nodeFixture(saved).node; extension.nodeCreated(restored); restored.onAdded();
      const {menu: newMenu} = checkInstalled(restored, false); newMenu[0].callback(); checkInstalled(restored);
      assert.equal(JSON.stringify(values(restored)), original); restored.onRemoved();
    } else if (scenario === 'repeat') {
      extension.nodeCreated(node); extension.nodeCreated(node); node.onAdded(); checkInstalled(node);
    }
    if (scenario !== 'reload') node.onRemoved();
    assert.equal(frames.size, 0);
  }
  assert.equal(JSON.stringify(values(node)), original);
  console.log(JSON.stringify({scenario, passed: true, activeFrames: frames.size}));
} else {
  for (const [scenario, name] of [
    ['initial', 'V1.3 first installation keeps one extra UI and stable outputs'],
    ['readd', 'Three same-object remove/readd cycles restore both extra UIs and preserve values'],
    ['refresh', 'Readded V1.3 observes sheet-size changes once and uses current preview values'],
    ['reload', 'Fresh node from serialized values restores auxiliary visibility and assembly controls'],
    ['repeat', 'Repeated nodeCreated and onAdded do not duplicate menus, UI or animation loops'],
    ['legacy', 'Shared integration retains legacy installation and readd behavior'],
    ['fallback', 'Unavailable base DOM UI does not install V1.3 extras'],
  ]) {
    test(name, () => {
      const output = execFileSync(process.execPath, ['--experimental-vm-modules', fileURLToPath(import.meta.url), '--lifecycle-child', scenario], {encoding: 'utf8'});
      assert.equal(JSON.parse(output).passed, true);
    });
  }
}
