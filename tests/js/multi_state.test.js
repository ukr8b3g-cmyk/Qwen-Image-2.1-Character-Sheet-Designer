import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
import {DEFAULT_JSON} from '../../web/state.js';
import {DEFAULT_MULTI_JSON, MULTI_PRESETS, MULTI_VIEW_IDS, parseMultiState, migrateMultiState, serializeMultiState, MultiReferenceController} from '../../web/multi_state.js';
import {PROFILE} from '../../web/multi_profile.js';
import {NODE_TYPE, DEFAULT_NODE_SIZE, previewRequester, createExtension} from '../../web/multi_integration.js';

const cases = JSON.parse(readFileSync(new URL('../fixtures/multi_state_cases.json', import.meta.url), 'utf8'));
for (const item of cases) test(`Multi Python/JS parity: ${item.id}`, () => {
  if (item.valid) assert.deepEqual(migrateMultiState(parseMultiState(item.raw, item.max_resolution)), item.normalized);
  else assert.throws(() => parseMultiState(item.raw, item.max_resolution));
});
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
function preview(raw) {
  const state = parseMultiState(raw);
  return {width: 2816, height: 1280, max_resolution: 16384, prompt: 'current', layout: {canvas: [2816,1280], feet_y: null,
    panels: state.views.map((id, i) => ({id, rect: [i/state.views.length, 0, 1/state.views.length, 1]}))}};
}
function make(raw = DEFAULT_MULTI_JSON, options = {}) { return new MultiReferenceController({raw, requestPreview: async r => preview(r), ...options}); }

test('separate Qwen node, extension, route and size', () => {
  assert.equal(NODE_TYPE, 'QwenImage21CharacterSheetDesignerMultiReference');
  assert.deepEqual(DEFAULT_NODE_SIZE, [1060, 1350]);
  assert.equal(createExtension({}, {}).name, 'qwen21.CharacterSheetDesignerMultiReference');
  assert.equal(createExtension({}, {}).nodeCreated({type: 'QwenImage21CharacterSheetDesigner'}), undefined);
});

test('legacy loading/preview never migrates; the first edit persists v3', async () => {
  const controller = make(DEFAULT_JSON);
  await tick(); assert.equal(controller.raw, DEFAULT_JSON);
  controller.setPartPrompt('hands', ' \n '); assert.equal(controller.raw, DEFAULT_JSON);
  controller.toggle('face_back'); assert.equal(controller.state.schema_version, 3);
  assert.equal(controller.state.reference_roles.reference_image_2, 'same_character');
  controller.dispose();
});

test('all views, presets, part text and roles remain independent and persist', async () => {
  const controller = make();
  controller.setReferenceRole('reference_image_2', 'clothing_back');
  controller.setHandState('bare'); controller.setClothingMode('garment');
  controller.setPartPrompt('hands', '  silver ring; gloves\n星 {red|blue} ');
  controller.preset('detail'); assert.deepEqual(controller.state.views, MULTI_VIEW_IDS);
  controller.preset('head'); assert.deepEqual(controller.state.views, MULTI_PRESETS.head);
  controller.preset('clothing'); assert.deepEqual(controller.state.views, MULTI_PRESETS.clothing);
  const saved = controller.raw; controller.restore(saved);
  assert.equal(controller.state.part_prompts.hands, '  silver ring; gloves\n星 {red|blue} ');
  assert.equal(controller.state.reference_roles.reference_image_2, 'clothing_back');
  assert.equal(controller.state.hand_state, 'bare'); assert.equal(controller.state.clothing_mode, 'garment');
  controller.preset('single'); assert.throws(() => controller.toggle('body_front'));
  controller.dispose();
});

test('Auto→Manual copies current dimensions and rejects stale/error dimensions', async () => {
  const controller = make(); assert.throws(() => controller.setMode('manual'));
  await tick(); controller.setMode('manual');
  assert.equal(controller.state.size.manual_width, 2816); assert.equal(controller.state.size.manual_height, 1280);
  controller.setSize('manual_width', '896'); controller.preset('detail');
  assert.equal(controller.state.size.manual_width, 896);
  controller.setMode('auto'); controller.requestPreview = async () => { throw Error('offline'); };
  await controller.refreshPreview(); assert.throws(() => controller.setMode('manual'));
  controller.dispose();
});

test('reference presence refresh discards late answers even if JSON is unchanged', async () => {
  const pending = [], controller = make(DEFAULT_MULTI_JSON, {requestPreview: raw => new Promise(resolve => pending.push({raw, resolve}))});
  void controller.refreshPreview();
  pending[1].resolve({...preview(pending[1].raw), prompt: 'new presence'}); await tick();
  pending[0].resolve({...preview(pending[0].raw), prompt: 'old presence'}); await tick();
  assert.equal(controller.preview.prompt, 'new presence'); assert.equal(controller.isCurrentPreview, true);
  controller.dispose();
});

test('invalid JSON and preview failure preserve canonical state and allow retries', async () => {
  const controller = make('{broken'); assert.equal(controller.raw, '{broken'); assert.equal(controller.state, null);
  controller.restore(DEFAULT_MULTI_JSON); await tick();
  const saved = controller.raw; controller.requestPreview = async () => { throw Error('offline'); };
  await controller.refreshPreview(); assert.equal(controller.raw, saved); assert.equal(controller.isCurrentPreview, false);
  controller.requestPreview = async raw => preview(raw); await controller.refreshPreview(); assert.equal(controller.isCurrentPreview, true);
  controller.dispose();
});

test('preview envelope includes main connection and both extra slots with strict booleans', async () => {
  let seen;
  const presence = {character_image: true, reference_image_1: false, reference_image_2: true};
  const request = previewRequester({fetchApi: async (...args) => { seen = args; return {ok: true, json: async () => ({})}; }}, () => true, () => 'anime', () => presence);
  await request(DEFAULT_MULTI_JSON);
  assert.equal(seen[0], PROFILE.previewPath);
  assert.deepEqual(JSON.parse(seen[1].body), {state_json: DEFAULT_MULTI_JSON, use_layout_image: true, style: 'anime', reference_presence: presence, batch_out: false});
});

test('Batch Out preview uses its own widget and does not rewrite saved JSON', async () => {
  let body;
  const request = previewRequester({fetchApi: async (_, options) => { body = JSON.parse(options.body); return {ok: true, json: async () => ({})}; }}, undefined, undefined, undefined, () => true);
  await request(DEFAULT_MULTI_JSON);
  assert.equal(body.batch_out, true);
  assert.equal(body.state_json, DEFAULT_MULTI_JSON);
  assert.equal(Object.hasOwn(JSON.parse(body.state_json), 'batch_out'), false);
});
