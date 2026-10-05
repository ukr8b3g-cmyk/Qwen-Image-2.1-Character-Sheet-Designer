/** UI display of the same atlas crops used by the backend layout_image output. */
import {VIEW_IDS} from './state.js';
import {avatarSVG} from './avatar.js';
import {USE_RASTER_ATLAS} from './artwork_config.js';
export const ATLAS_SIZE = Object.freeze([1254, 1254]);
export const ARTWORK_RECTS = Object.freeze({
  face_front: Object.freeze([0, 75, 470, 560]),
  face_left: Object.freeze([1010, 35, 140, 205]),
  body_front: Object.freeze([495, 20, 350, 625]),
  body_left: Object.freeze([904, 20, 350, 625]),
  body_back: Object.freeze([55, 625, 350, 625]),
  hands: Object.freeze([415, 755, 445, 400]),
  feet: Object.freeze([860, 820, 380, 340]),
});
export const ATLAS_URL = new URL('./assets/mannequin-atlas.png', import.meta.url).href;
let sequence = 0;
export function artworkRect(view) {
  if (!VIEW_IDS.includes(view)) throw new RangeError(`Unknown artwork view: ${view}`);
  return ARTWORK_RECTS[view];
}
export function createArtwork(view, idPrefix) {
  const rect = artworkRect(view);
  const frame = document.createElement('span');
  frame.className = 'q21-artwork'; frame.dataset.artwork = view;
  frame.setAttribute('aria-hidden', 'true');
  const fallback = () => {
    // Only trusted local SVG, with internally sanitized IDs; no user prompt HTML.
    frame.innerHTML = avatarSVG(view, idPrefix);
    frame.dataset.artworkSource = 'upstream-svg-fallback';
  };
  if (!USE_RASTER_ATLAS) { fallback(); return frame; }
  frame.dataset.artworkSource = 'upstream-raster';
  const ns = 'http://www.w3.org/2000/svg';
  const viewport = document.createElementNS(ns, 'svg');
  viewport.setAttribute('viewBox', rect.join(' '));
  viewport.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  viewport.setAttribute('overflow', 'hidden');
  viewport.setAttribute('aria-hidden', 'true');
  viewport.setAttribute('focusable', 'false');
  const clipId = `q21-atlas-${String(idPrefix ?? 'view').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 100)}-${++sequence}`;
  const defs = document.createElementNS(ns, 'defs');
  const clip = document.createElementNS(ns, 'clipPath');
  clip.id = clipId; clip.setAttribute('clipPathUnits', 'userSpaceOnUse');
  const clipRect = document.createElementNS(ns, 'rect');
  for (const [i, name] of ['x', 'y', 'width', 'height'].entries()) clipRect.setAttribute(name, String(rect[i]));
  clip.append(clipRect); defs.append(clip); viewport.append(defs);
  const image = document.createElementNS(ns, 'image');
  image.setAttribute('clip-path', `url(#${clipId})`);
  image.setAttribute('width', String(ATLAS_SIZE[0])); image.setAttribute('height', String(ATLAS_SIZE[1]));
  image.addEventListener('error', fallback, {once: true});
  image.setAttribute('href', ATLAS_URL); viewport.append(image); frame.append(viewport);
  return frame;
}
