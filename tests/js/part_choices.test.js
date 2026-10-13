import assert from 'node:assert/strict';
import test from 'node:test';
import {DEFAULT_JSON} from '../../web/state.js';
import {DEFAULT_MULTI_JSON, parseMultiState, serializeMultiState, MultiReferenceController} from '../../web/multi_state.js';

const tick = () => new Promise(resolve => setTimeout(resolve, 0));
function preview(raw) {
  const state = parseMultiState(raw);
  return {width: 1024, height: 1024, max_resolution: 16384, prompt: 'current',
    layout: {canvas: [1024, 1024], feet_y: null, panels: state.views.map((id, i) => ({id, rect: [i / state.views.length, 0, 1 / state.views.length, 1]}))}};
}
for (const clothing of ['reference', 'pants', 'skirt_robe']) for (const hand of ['reference', 'bare', 'gloved']) for (const footwear of ['reference', 'shod', 'unshod']) {
  test(`part choice roundtrip: ${clothing}/${hand}/${footwear}`, () => {
    const value = {...JSON.parse(DEFAULT_MULTI_JSON), clothing_type: clothing, hand_state: hand, footwear_state: footwear};
    assert.deepEqual(parseMultiState(serializeMultiState(value)), value);
  });
}
test('old state keeps its keys and hand setting', () => {
  for (const hand of ['reference', 'bare', 'gloved']) {
    const value = {...JSON.parse(DEFAULT_MULTI_JSON), hand_state: hand};
    assert.deepEqual(parseMultiState(JSON.stringify(value)), value);
  }
});
test('each control persists only its part value and preserves view, size and reference choices', async () => {
  const controller = new MultiReferenceController({raw: DEFAULT_MULTI_JSON, requestPreview: async raw => preview(raw)});
  await tick();
  const before = structuredClone(controller.state);
  controller.setClothingType('skirt_robe'); controller.setHandState('bare'); controller.setFootwearState('unshod');
  for (const field of ['views', 'size', 'reference_roles', 'part_prompts', 'clothing_mode']) assert.deepEqual(controller.state[field], before[field]);
  const saved = controller.raw; controller.restore(DEFAULT_MULTI_JSON); controller.restore(saved);
  assert.equal(controller.state.clothing_type, 'skirt_robe'); assert.equal(controller.state.hand_state, 'bare'); assert.equal(controller.state.footwear_state, 'unshod');
  controller.preset('clothing'); assert.equal(controller.state.clothing_type, 'skirt_robe'); assert.equal(controller.state.footwear_state, 'unshod');
  controller.dispose();
});
test('first part-choice edit migrates an old state without changing the saved JSON on load', async () => {
  const controller = new MultiReferenceController({raw: DEFAULT_JSON, requestPreview: async raw => preview(raw)});
  await tick(); assert.equal(controller.raw, DEFAULT_JSON);
  controller.setFootwearState('shod'); assert.equal(controller.state.schema_version, 3); assert.equal(controller.state.footwear_state, 'shod');
  controller.dispose();
});
for (const field of ['clothing_type', 'footwear_state']) for (const value of ['unknown', null, 1, [], {}]) {
  test(`invalid part choice: ${field}/${JSON.stringify(value)}`, () => {
    assert.throws(() => parseMultiState(JSON.stringify({...JSON.parse(DEFAULT_MULTI_JSON), [field]: value})));
  });
}
