/** v3 adapter; legacy controllers keep their seven-view contract. */
import {
  normalizeState, parseJSONStrict, StateError, validatePreview,
  VIEW_IDS, parseState, serializeState, migratePartState,
  validateSize, validatePartPrompt, PART_IDS, PRESETS,
} from './state.js';
/** One persistent value, with separate advisory preview and request identity. */
export class DesignerController {
  constructor({raw, requestPreview, transaction = fn => fn(), onChange = () => {}, onCommit = () => {}, timeoutMs = 15000, readRaw = null, writeRaw = null, adapter = null}) {
    this.adapter = adapter; this.viewIds = adapter?.viewIds ?? VIEW_IDS; this.presets = adapter?.presets ?? PRESETS;
    this.parseState = adapter?.parse ?? parseState; this.serializeState = adapter?.serialize ?? serializeState;
    this.readRaw = readRaw; this.writeRaw = writeRaw; this._raw = raw; this.observedRaw = raw; this.state = null; this.error = null; this.preview = null; this.previewRaw = null;
    this.pending = false; this.previewError = null; this.maxResolution = Infinity;
    this.generation = 0; this.requestNumber = 0; this.disposed = false;
    this.requestPreview = requestPreview; this.transaction = transaction; this.onChange = onChange; this.onCommit = onCommit; this.timeoutMs = timeoutMs;
    this.restore(raw, false);
  }
  // Embedded integrations can retain their official widget as the sole value owner.
  // The controller caches parsed/preview state only; raw always reads that source.
  get raw() { return this.readRaw ? this.readRaw() : this._raw; }
  set raw(value) { if (this.writeRaw) this.writeRaw(value); else this._raw = value; }
  syncFromSource() {
    if (!this.disposed && this.raw !== this.observedRaw) { this.restore(this.raw); return true; }
    return false;
  }
  get isCurrentPreview() { return !this.pending && !this.previewError && this.preview !== null && this.previewRaw === this.raw; }
  emit(reason) { if (!this.disposed) this.onChange(this, reason); }
  invalidate() { this.generation++; this.requestNumber++; this.abort?.abort(); this.abort = null; clearTimeout(this.timer); this.pending = false; }
  restore(raw, notify = true) {
    if (this.disposed) return;
    this.invalidate(); this.observedRaw = raw; if (this.raw !== raw) this.raw = raw; this.previewRaw = null; this.previewError = null;
    try { this.state = this.parseState(raw, this.maxResolution); this.error = null; }
    catch (error) { this.state = null; this.error = error; }
    if (notify) this.emit('restore');
    if (this.state) void this.refreshPreview();
  }
  commit(next) {
    if (this.disposed) return false;
    this.syncFromSource();
    const raw = this.serializeState(next, this.maxResolution);
    if (raw === this.raw) return false;
    const previous = this.raw;
    this.transaction(() => {
      this.invalidate(); this.observedRaw = raw; this.raw = raw; this.state = this.parseState(raw, this.maxResolution); this.error = null; this.previewError = null; this.previewRaw = null;
      this.onCommit(raw, previous);
    });
    this.emit('commit'); void this.refreshPreview(); return true;
  }
  change(mutator) {
    this.syncFromSource();
    if (!this.state || this.disposed) return false;
    const next = this.adapter?.migrate ? this.adapter.migrate(this.state) : structuredClone(this.state);
    mutator(next); return this.commit(next);
  }
  toggle(view) {
    this.syncFromSource();
    if (!this.viewIds.includes(view)) fail('views');
    if (this.state?.views.length === 1 && this.state.views[0] === view) fail('lastView');
    return this.change(next => { next.views = next.views.includes(view) ? next.views.filter(id => id !== view) : [...next.views, view]; });
  }
  preset(name) { if (!this.presets[name]) fail('views'); return this.change(next => { next.views = [...this.presets[name]]; }); }
  setMode(mode) {
    this.syncFromSource();
    if (mode === this.state?.size.mode) return false;
    if (mode === 'manual') {
      if (!this.isCurrentPreview) fail('updating');
      return this.change(next => { next.size.mode = 'manual'; next.size.manual_width = this.preview.width; next.size.manual_height = this.preview.height; });
    }
    if (mode !== 'auto') fail('mode');
    return this.change(next => { next.size.mode = 'auto'; });
  }
  setSize(field, text) {
    if (!['body_height', 'manual_width', 'manual_height'].includes(field)) fail('keys', field);
    if (typeof text !== 'string' || !/^\d+$/.test(text.trim())) fail('size', field);
    const value = validateSize(Number(text.trim()), field, this.maxResolution);
    return this.change(next => { next.size[field] = value; });
  }
  setPartPrompt(part, text) {
    this.syncFromSource();
    if (!PART_IDS.includes(part)) fail('parts');
    validatePartPrompt(text);
    if (!this.state || this.disposed) return false;
    if (text === this.state.part_prompts?.[part]) return false;
    // Opening an empty editor is not a schema migration or an Undo entry.
    if (!text.trim() && !this.state.part_prompts?.[part]) return false;
    const next = this.adapter?.migrate ? this.adapter.migrate(this.state) : migratePartState(this.state);
    if (text.trim()) next.part_prompts[part] = text;
    else delete next.part_prompts[part];
    return this.commit(next);
  }
  applyRaw(raw) { return this.commit(this.parseState(raw, this.maxResolution)); }
  async refreshPreview() {
    if (this.syncFromSource()) return;
    if (this.disposed || !this.state) return;
    this.abort?.abort(); clearTimeout(this.timer);
    const abort = new AbortController(); this.abort = abort;
    const generation = this.generation, request = ++this.requestNumber, raw = this.raw, state = this.state;
    const current = () => !this.disposed && this.generation === generation && this.requestNumber === request && this.raw === raw;
    this.pending = true; this.previewError = null; this.emit('pending');
    try {
      const timeout = new Promise((_, reject) => { this.timer = setTimeout(() => { abort.abort(); reject(new StateError('timeout')); }, this.timeoutMs); });
      const result = await Promise.race([this.requestPreview(raw, abort.signal), timeout]);
      if (!current()) return;
      this.preview = validatePreview(result, state); this.previewRaw = raw;
      if (Number.isSafeInteger(result.max_resolution) && result.max_resolution >= 32) this.maxResolution = result.max_resolution;
      this.pending = false; this.previewError = null; this.emit('preview');
    } catch (error) {
      if (!current()) return;
      this.pending = false; this.previewError = error; this.emit('preview-error');
    } finally { if (current()) { clearTimeout(this.timer); this.abort = null; } }
  }
  dispose() { this.invalidate(); this.disposed = true; this.onChange = () => {}; this.onCommit = () => {}; this.requestPreview = null; this.preview = null; this.state = null; }
}


export const MULTI_VIEW_IDS = Object.freeze([
  'face_front', 'face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'face_back',
  'body_front', 'body_left', 'body_back', 'clothing_front', 'clothing_back', 'hands', 'feet',
]);
export const REFERENCE_INPUTS = Object.freeze(['reference_image_1', 'reference_image_2', 'reference_image_3']);
export const HAND_STATES = Object.freeze(['reference', 'bare', 'gloved']);
export const CLOTHING_MODES = Object.freeze(['worn', 'garment']);
export const CLOTHING_TYPES = Object.freeze(['reference', 'pants', 'skirt_robe']);
export const FOOTWEAR_STATES = Object.freeze(['reference', 'shod', 'unshod']);
export const MULTI_MIRRORED_VIEWS = Object.freeze(['face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'body_left']);
export const REFERENCE_ROLES = Object.freeze([
  'same_character', 'face', 'head', 'clothing', 'clothing_front', 'clothing_back', 'hands', 'footwear',
]);
export const MULTI_PRESETS = Object.freeze({
  ...PRESETS, detail: [...MULTI_VIEW_IDS], head: MULTI_VIEW_IDS.slice(0, 6),
  clothing: ['clothing_front', 'clothing_back'],
});
export const DEFAULT_MULTI_JSON = JSON.stringify({
  schema_version: 3, views: PRESETS.five,
  size: {mode: 'auto', body_height: 1120, manual_width: 2208, manual_height: 1280},
  part_prompts: {}, reference_roles: Object.fromEntries(REFERENCE_INPUTS.map(input => [input, 'same_character'])),
  hand_state: 'reference', clothing_mode: 'worn',
});
const fail = (code, detail = '') => { throw new StateError(code, detail); };
function keys(value, expected, path) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('object', path);
  const actual = Object.keys(value);
  if (actual.length !== expected.length || actual.some(key => !expected.includes(key))) fail('keys', path);
}
export function normalizeMultiState(state, maxResolution = Infinity) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) fail('object', 'state');
  if ([1, 2].includes(state.schema_version)) return normalizeState(state, maxResolution);
  if (state.schema_version !== 3) fail('version');
  state = {...state, hand_state: Object.hasOwn(state, 'hand_state') ? state.hand_state : 'reference',
    clothing_mode: Object.hasOwn(state, 'clothing_mode') ? state.clothing_mode : 'worn'};
  const choices = Object.fromEntries(['clothing_type', 'footwear_state'].filter(key => Object.hasOwn(state, key)).map(key => [key, state[key]]));
  keys(state, ['schema_version', 'views', 'size', 'part_prompts', 'reference_roles', 'hand_state', 'clothing_mode', ...Object.keys(choices)], 'state');
  if (Object.hasOwn(choices, 'clothing_type') && !CLOTHING_TYPES.includes(choices.clothing_type)) fail('clothingType');
  if (Object.hasOwn(choices, 'footwear_state') && !FOOTWEAR_STATES.includes(choices.footwear_state)) fail('footwearState');
  if (!HAND_STATES.includes(state.hand_state)) fail('handState');
  if (!CLOTHING_MODES.includes(state.clothing_mode)) fail('clothingMode');
  if (!Array.isArray(state.views) || !state.views.length || state.views.some(view => !MULTI_VIEW_IDS.includes(view))) fail('views');
  keys(state.size, ['mode', 'body_height', 'manual_width', 'manual_height'], 'size');
  if (!['auto', 'manual'].includes(state.size.mode)) fail('mode');
  const normalized = {
    schema_version: 3, views: MULTI_VIEW_IDS.filter(view => state.views.includes(view)),
    size: {mode: state.size.mode,
      body_height: validateSize(state.size.body_height, 'body_height', maxResolution),
      manual_width: validateSize(state.size.manual_width, 'manual_width', maxResolution),
      manual_height: validateSize(state.size.manual_height, 'manual_height', maxResolution)},
    part_prompts: {},
  };
  const prompts = state.part_prompts;
  if (!prompts || typeof prompts !== 'object' || Array.isArray(prompts)) fail('object', 'part_prompts');
  if (Object.keys(prompts).some(part => !PART_IDS.includes(part))) fail('parts');
  for (const part of PART_IDS) if (Object.hasOwn(prompts, part)) {
    const text = validatePartPrompt(prompts[part]);
    if (text.trim()) normalized.part_prompts[part] = text;
  }
  const roles = state.reference_roles;
  keys(roles, roles && Object.hasOwn(roles, 'reference_image_3') ? REFERENCE_INPUTS : REFERENCE_INPUTS.slice(0, -1), 'reference_roles');
  normalized.reference_roles = {};
  for (const input of REFERENCE_INPUTS) {
    const role = input === 'reference_image_3' && !Object.hasOwn(roles, input) ? 'same_character' : roles[input];
    if (!REFERENCE_ROLES.includes(role)) fail('roles', input);
    normalized.reference_roles[input] = role;
  }
  normalized.hand_state = state.hand_state;
  normalized.clothing_mode = state.clothing_mode;
  Object.assign(normalized, choices);
  return normalized;
}
export function migrateMultiState(state) {
  const next = normalizeMultiState(state);
  if (next.schema_version < 3) return {
    ...next, schema_version: 3, part_prompts: next.part_prompts ?? {},
    reference_roles: Object.fromEntries(REFERENCE_INPUTS.map(input => [input, 'same_character'])),
    hand_state: 'reference', clothing_mode: 'worn',
  };
  return next;
}
export const parseMultiState = (raw, max) => normalizeMultiState(parseJSONStrict(raw), max);
export const serializeMultiState = (state, max) => JSON.stringify(normalizeMultiState(state, max));
export class MultiReferenceController extends DesignerController {
  constructor(options) {
    super({...options, adapter: {
      parse: parseMultiState, serialize: serializeMultiState, migrate: migrateMultiState,
      viewIds: MULTI_VIEW_IDS, presets: MULTI_PRESETS,
    }});
  }
  setMode(mode, output = null) {
    if (mode !== 'manual' || !output) return super.setMode(mode);
    this.syncFromSource();
    if (mode === this.state?.size.mode) return false;
    if (!this.isCurrentPreview) fail('updating');
    validateSize(output.width, 'manual_width', this.maxResolution);
    validateSize(output.height, 'manual_height', this.maxResolution);
    return this.change(next => { next.size.mode = 'manual'; next.size.manual_width = output.width; next.size.manual_height = output.height; });
  }
  setReferenceRole(input, role) {
    if (!REFERENCE_INPUTS.includes(input) || !REFERENCE_ROLES.includes(role)) fail('roles');
    return this.change(next => { next.reference_roles[input] = role; });
  }
  setHandState(value) {
    if (!HAND_STATES.includes(value)) fail('handState');
    return this.change(next => { next.hand_state = value; });
  }
  setClothingMode(value) {
    if (!CLOTHING_MODES.includes(value)) fail('clothingMode');
    return this.change(next => { next.clothing_mode = value; });
  }
  setClothingType(value) {
    if (!CLOTHING_TYPES.includes(value)) fail('clothingType');
    return this.change(next => { next.clothing_type = value; });
  }
  setFootwearState(value) {
    if (!FOOTWEAR_STATES.includes(value)) fail('footwearState');
    return this.change(next => { next.footwear_state = value; });
  }
}
