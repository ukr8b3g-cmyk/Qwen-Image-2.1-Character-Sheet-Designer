import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_MULTI_JSON, parseMultiState, MultiReferenceController, REFERENCE_INPUTS} from '../../web/multi_state.js';
import {previewRequester} from '../../web/multi_integration.js';

test('old two-reference state remains raw until edit, then persists the third role', () => {
  const state = JSON.parse(DEFAULT_MULTI_JSON); delete state.reference_roles.reference_image_3;
  state.reference_roles.reference_image_2 = 'clothing_back';
  const raw = JSON.stringify(state);
  const controller = new MultiReferenceController({raw, requestPreview: async () => {throw Error('No preview needed');}});
  assert.equal(controller.raw, raw);
  assert.equal(controller.state.reference_roles.reference_image_3, 'same_character');
  controller.setReferenceRole('reference_image_3', 'face');
  const saved = controller.raw;
  controller.restore(raw); assert.equal(controller.raw, raw);
  controller.restore(saved);
  assert.equal(controller.state.reference_roles.reference_image_2, 'clothing_back');
  assert.equal(controller.state.reference_roles.reference_image_3, 'face');
  assert.deepEqual(controller.state.size, state.size);
  assert.deepEqual(REFERENCE_INPUTS, ['reference_image_1','reference_image_2','reference_image_3']);
  controller.dispose();
});

test('third-reference presence is sent independently and invalid roles remain invalid', async () => {
  let body;
  const presence = {character_image:true, reference_image_1:false, reference_image_2:false, reference_image_3:true};
  const request = previewRequester({fetchApi:async (_,options)=>{body=JSON.parse(options.body); return {ok:true,json:async()=>({})};}}, undefined, undefined, ()=>presence);
  await request(DEFAULT_MULTI_JSON);
  assert.deepEqual(body.reference_presence,presence);
  for (const bad of [null, false, 'unknown']) {
    const state=JSON.parse(DEFAULT_MULTI_JSON); state.reference_roles.reference_image_3=bad;
    assert.throws(()=>parseMultiState(JSON.stringify(state)));
  }
});
