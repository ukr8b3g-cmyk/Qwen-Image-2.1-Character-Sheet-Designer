import test from 'node:test';
import assert from 'node:assert/strict';
import {createDesignerUI} from '../../web/multi_ui.js';
import {DEFAULT_MULTI_JSON, MultiReferenceController} from '../../web/multi_state.js';

// DOM host double: exercise the real renderer without a ComfyUI server.
class Element {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {}; this.events = {}; this.hidden = false;
    this.style = {setProperty() {}};
    this.classList = {add: name => { this.className = `${this.className ?? ''} ${name}`; }, toggle() {}};
  }
  set textContent(text) { this.text = text; this.children = []; }
  get textContent() { return (this.text ?? '') + this.children.map(c => c.textContent).join(' '); }
  get options() { return this.children; }
  append(...items) { for (const item of items) { item.parent = this; this.children.push(item); } }
  prepend(...items) { for (const item of items) item.parent = this; this.children.unshift(...items); }
  replaceChildren(...items) { this.children = []; this.append(...items); }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.events[name] = callback; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(c => c !== this); }
  querySelectorAll(selector) {
    const matches = el => selector.startsWith('.') ? el.className?.split(' ').includes(selector.slice(1))
      : selector.startsWith('[data-') ? selector.slice(6, -1).replace(/-([a-z])/g, (_, c) => c.toUpperCase()) in el.dataset : false;
    return this.children.flatMap(c => [...(matches(c) ? [c] : []), ...c.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] ?? null; }
}
function fixture(options, run) {
  const previous = globalThis.document;
  globalThis.document = {createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag), querySelector: () => true};
  let ui;
  try {
    const state = {...JSON.parse(DEFAULT_MULTI_JSON), views: ['body_front', 'feet']};
    const p = {width: 1024, height: 1024, prompt: '', notices: [],
      layout: {canvas: [1024, 1024], feet_y: null, panels: state.views.map((id, i) => ({id, rect: [i / 2, 0, .5, 1]}))}};
    const controller = {state, raw: JSON.stringify(state), preview: p, isCurrentPreview: true, pending: false};
    ui = createDesignerUI({controller, ...options});
    run({ui, controller, alert: ui.root.querySelector('.q21-mr-error')});
  } finally { ui?.dispose(); globalThis.document = previous; }
}

for (const locale of ['ja', 'en']) for (const version of ['V1.1', 'V1.2', 'V1.3']) {
  test(`${version} ${locale} renders the matching encoder connection instructions`, () => fixture(
    {locale, perOutputReferences: version !== 'V1.1'}, ({ui}) => {
      const roles = ui.root.querySelectorAll('.q21-mr-reference-roles').find(box => box.querySelector('[data-reference-role]'));
      const hint = roles.querySelector('.q21-mr-part-hint').textContent;
      if (version === 'V1.1') { assert.match(hint, /image_2/); assert.doesNotMatch(hint, /Sheet Encode/); }
      else { assert.match(hint, /Sheet Encode/); assert.match(hint, /reference_plan/); assert.doesNotMatch(hint, /image_[2345]/); }
    }));
}

for (const locale of ['ja', 'en']) {
  test(`${locale} missing references are localized, aggregated and clear after connection`, () => fixture(
    {locale, perOutputReferences: true}, ({ui, controller, alert}) => {
      controller.preview.notices = ['missing_reference:feet']; ui.render();
      assert.equal(alert.hidden, false); assert.match(alert.textContent, locale === 'ja' ? /足/ : /Footwear/);
      assert.match(alert.textContent, /Sheet Encode/);
      controller.preview.notices = [];
      controller.preview.batch_plan = {enabled: true, items: [{notices: ['missing_reference:body_front']}, {notices: ['missing_reference:feet']}]};
      ui.render(); assert.equal(alert.hidden, false);
      assert.match(alert.textContent, locale === 'ja' ? /正面/ : /Front/);
      // A valid feet-only dedicated reference does not require a character image.
      controller.preview.batch_plan.items = [{notices: []}]; ui.render(); assert.equal(alert.hidden, true);
      controller.preview.notices = ['missing_character']; ui.render(); assert.equal(alert.hidden, false);
      controller.isCurrentPreview = false; ui.render(); assert.equal(alert.hidden, true);
    }));
}

test('large batch overview passes validation, gallery selection pins actual output sizes to Manual', async () => {
  const raw = JSON.stringify({...JSON.parse(DEFAULT_MULTI_JSON), views: ['face_front', 'feet']});
  const controller = new MultiReferenceController({raw, requestPreview: async () => ({
    width: 7104, height: 6144, max_resolution: 16384, overview_only: true,
    layout: {canvas: [7104, 6144], feet_y: null, panels: [{id: 'face_front', rect: [0, 0, .5, 1]}, {id: 'feet', rect: [.5, 0, .5, 1]}]},
    batch_plan: {enabled: true, items: [{width: 6144, height: 6144}, {width: 7104, height: 5184}]},
  })});
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(controller.isCurrentPreview, true);
  controller.setMode('manual', controller.preview.batch_plan.items[1]);
  assert.equal(controller.state.size.manual_width, 7104); assert.equal(controller.state.size.manual_height, 5184);
  const saved = controller.raw; controller.restore(saved, false); assert.equal(controller.raw, saved);
  controller.dispose();
});
