// Test harness adapter: exact upstream SVG fallback, not the unavailable atlas.
import {avatarSVG} from './avatar.js';
export function createArtwork(view, id) {
 const frame=document.createElement('span');frame.className='h3-artwork';frame.innerHTML=avatarSVG(view,id);return frame;
}
