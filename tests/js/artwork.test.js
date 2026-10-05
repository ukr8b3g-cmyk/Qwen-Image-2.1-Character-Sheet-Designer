import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import test from 'node:test';
import {ATLAS_SIZE, ATLAS_URL, ARTWORK_RECTS, createArtwork} from '../../web/artwork.js';
import {USE_RASTER_ATLAS} from '../../web/artwork_config.js';
import {VIEW_IDS} from '../../web/state.js';

class Element {
  constructor(tag) { this.tagName=tag; this.children=[]; this.dataset={}; this.attributes={}; this.events={}; }
  setAttribute(name,value) { this.attributes[name]=value; }
  append(...children) { this.children.push(...children); }
  addEventListener(name,fn) { this.events[name]=fn; }
}

test('original H3 bitmap is bundled byte-for-byte and enabled by default',()=>{
  assert.equal(USE_RASTER_ATLAS,true);
  const bytes=readFileSync(new URL('../../web/assets/mannequin-atlas.png',import.meta.url));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),'7213405d101a6ccc0152304680ab5a1b4f17ba456086f3469b41be1319b2b8f6');
  assert.equal(bytes.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
  assert.deepEqual([bytes.readUInt32BE(16),bytes.readUInt32BE(20)],ATLAS_SIZE);
  assert.equal(new URL(ATLAS_URL).pathname.endsWith('/web/assets/mannequin-atlas.png'),true);
});

test('all seven raster crops use explicit source clipping and unique local IDs',()=>{
  const previous=globalThis.document;
  globalThis.document={createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)};
  try {
    const ids=new Set();
    for (const view of VIEW_IDS) for(let copy=0;copy<2;copy++) {
      const frame=createArtwork(view,'<same id>');
      assert.equal(frame.dataset.artworkSource,'upstream-raster');
      assert.equal(frame.dataset.artwork,view);
      const [svg]=frame.children, [defs,image]=svg.children, [clip]=defs.children, [rect]=clip.children;
      const crop=ARTWORK_RECTS[view];
      assert.equal(svg.attributes.viewBox,crop.join(' '));
      assert.equal(svg.attributes.overflow,'hidden');
      assert.equal(svg.attributes.preserveAspectRatio,'xMidYMid meet');
      assert.equal(clip.attributes.clipPathUnits,'userSpaceOnUse');
      assert.deepEqual(['x','y','width','height'].map(k=>Number(rect.attributes[k])),crop);
      assert.equal(image.attributes['clip-path'],`url(#${clip.id})`);
      assert.equal(image.attributes.href,ATLAS_URL);
      assert.deepEqual(['width','height'].map(k=>Number(image.attributes[k])),ATLAS_SIZE);
      assert.match(clip.id,/^[A-Za-z0-9_-]+$/); assert(!ids.has(clip.id)); ids.add(clip.id);
      assert(crop[0]>=0 && crop[1]>=0 && crop[0]+crop[2]<=ATLAS_SIZE[0] && crop[1]+crop[3]<=ATLAS_SIZE[1]);
      image.events.error();
      assert.equal(frame.dataset.artworkSource,'upstream-svg-fallback');
      assert.match(frame.innerHTML,/<svg/);
    }
  } finally { globalThis.document=previous; }
});

test('all seven crop rectangles match the approved original H3 layout',()=>{
  assert.deepEqual(ARTWORK_RECTS,{
    face_front:[0,75,470,560], face_left:[1010,35,140,205],
    body_front:[495,20,350,625], body_left:[904,20,350,625],
    body_back:[55,625,350,625], hands:[415,755,445,400], feet:[860,820,380,340],
  });
});

test('three full bodies retain the same crop scale',()=>{
  for (const view of ['body_front','body_left','body_back']) assert.deepEqual(ARTWORK_RECTS[view].slice(2),[350,625]);
});
