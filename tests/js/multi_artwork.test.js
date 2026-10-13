import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import test from 'node:test';
import {createArtwork} from '../../web/multi_artwork.js';
import {MULTI_VIEW_IDS, MULTI_MIRRORED_VIEWS} from '../../web/multi_state.js';

class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {}; this.events = {}; this.style = {}; this.classList = {add: value => this.className = value}; }
  setAttribute(k, v) { this.attributes[k] = v; }
  append(...items) { this.children.push(...items); }
  addEventListener(k, v) { this.events[k] = v; }
  remove() { this.removed = true; }
}
test('thirteen art cards use local assets, independent IDs, one mirror and name fallback', () => {
  const previous = globalThis.document, ids = new Set();
  globalThis.document = {createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag)};
  try {
    for (const view of MULTI_VIEW_IDS) for (let copy = 0; copy < 2; copy++) {
      const frame = createArtwork(view, '<same id>', {mirror: MULTI_MIRRORED_VIEWS.includes(view)});
      assert.equal(frame.className, 'q21-mr-artwork');
      assert.equal(frame.style.transform, MULTI_MIRRORED_VIEWS.includes(view) ? 'scaleX(-1)' : undefined);
      const child = frame.children[0];
      if (child.tagName === 'svg') {
        const clip = child.children[0].children[0], image = child.children[1];
        assert.match(clip.id, /^q21-mr-atlas-[A-Za-z0-9_-]+$/); assert(!ids.has(clip.id)); ids.add(clip.id);
        image.events.error();
      } else {
        assert(child.src.endsWith(`/assets/multi_reference/${view}.png`)); child.events.error();
      }
      assert.equal(frame.textContent, view); assert.equal(frame.dataset.artworkFallback, 'missing');
    }
  } finally { globalThis.document = previous; }
});
test('all six distributed PNG derivatives match the pinned source asset checksums', () => {
  const baseline = JSON.parse(readFileSync(new URL('../../tests/fixtures/public_source_contract.json', import.meta.url), 'utf8'));
  let count = 0;
  for (const row of baseline.files) if (row.group === 'h3' && /web\/assets\/(face_right|face_3q_left|face_3q_right|face_back|clothing_front|clothing_back)\.png$/.test(row.path)) {
    const name = row.path.split('/').at(-1), bytes = readFileSync(new URL(`../../web/assets/multi_reference/${name}`, import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), row.sha256); count++;
  }
  assert.equal(count, 6);
});
