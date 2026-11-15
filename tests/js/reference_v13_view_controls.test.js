import assert from 'node:assert/strict';
import test from 'node:test';
import {DEFAULT_MULTI_JSON, MULTI_VIEW_IDS, MultiReferenceController, effectiveViews} from '../../web/multi_state.js';

const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test('current Designer validates eleven preview views without losing the thirteen saved selections or prompts', async () => {
  const current = new MultiReferenceController({raw: DEFAULT_MULTI_JSON, viewOptions: true, requestPreview: async raw => {
    const views = effectiveViews(JSON.parse(raw));
    return {width: 1024, height: 1024, layout: {canvas: [1024, 1024], feet_y: null,
      panels: views.map((id, index) => ({id, rect: [index / views.length, 0, 1 / views.length, 1]}))}};
  }});
  try {
    current.preset('detail');
    current.setClothingType('none');
    current.setViewPrompt('body_left', 'Sitting in left profile.');
    current.setViewPrompt('face_front', '');
    const saved = current.raw;
    current.restore(DEFAULT_MULTI_JSON);
    current.restore(saved);
    await tick();
    assert.deepEqual(current.state.views, MULTI_VIEW_IDS);
    assert.equal(current.isCurrentPreview, true);
    assert.equal(current.preview.layout.panels.length, 11);
    assert.throws(() => current.preset('clothing'), {code: 'noEffectiveViews'});
    assert.equal(current.raw, saved);
    current.setClothingType('reference');
    await tick();
    assert.equal(current.preview.layout.panels.length, 13);
    current.setViewPrompt('body_left', null);
    assert.deepEqual(current.state.view_prompts, {face_front: ''});
  } finally {
    current.dispose();
  }
});
