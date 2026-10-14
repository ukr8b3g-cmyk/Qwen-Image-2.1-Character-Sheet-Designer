const OPTIONAL = new Set(['filename_suffix', 'sheet_plan', 'view_records']);
const PROPERTY = 'qwen_show_auxiliary_outputs';

export function installOptionalOutputs(node, root, change) {
  const drawings = new Map(), elements = new Map(), methods = new Map();
  const hidden = output => OPTIONAL.has(output?.name) && !node.properties?.[PROPERTY] &&
    !(node.isOutputConnected?.(node.outputs.indexOf(output)) ?? output.links?.length);
  for (const name of ['getOutputOnPos', 'getSlotInPosition']) {
    const original = node[name];
    if (typeof original !== 'function') continue;
    methods.set(name, Object.getOwnPropertyDescriptor(node, name));
    Object.defineProperty(node, name, {configurable: true, writable: true, value: function(...args) {
      const result = original.apply(this, args);
      return hidden(result?.output ?? result) ? (name === 'getSlotInPosition' ? null : undefined) : result;
    }});
  }
  const menu = node.getExtraMenuOptions;
  methods.set('getExtraMenuOptions', Object.getOwnPropertyDescriptor(node, 'getExtraMenuOptions'));
  Object.defineProperty(node, 'getExtraMenuOptions', {configurable: true, writable: true, value: function(canvas, options) {
    const result = menu?.call(this, canvas, options);
    options.push({content: node.properties?.[PROPERTY] ? '補助出力を隠す / Hide auxiliary outputs' : '補助出力を表示 / Show auxiliary outputs',
      callback: () => change(() => {
        node.properties ??= {};
        node.properties[PROPERTY] = !node.properties[PROPERTY];
        update(); node.setDirtyCanvas?.(true, true);
      })});
    return result;
  }});
  function restore(object, name, descriptor) {
    if (descriptor) Object.defineProperty(object, name, descriptor);
    else delete object[name];
  }
  function update() {
    for (const [output, saved] of drawings) {
      if (!node.outputs.includes(output)) { restore(output, 'draw', saved.descriptor); drawings.delete(output); }
    }
    for (const output of node.outputs) {
      if (!OPTIONAL.has(output.name) || drawings.has(output) || typeof output.draw !== 'function') continue;
      const original = output.draw;
      drawings.set(output, {descriptor: Object.getOwnPropertyDescriptor(output, 'draw')});
      Object.defineProperty(output, 'draw', {configurable: true, writable: true, value: function(...args) {
        if (!hidden(this)) return original.apply(this, args);
      }});
    }
    const ports = root.closest?.('.lg-node')?.querySelectorAll('.lg-slot--output');
    if (ports?.length === node.outputs.length) {
      ports.forEach((element, index) => {
        if (!elements.has(element)) elements.set(element, {visibility: element.style.visibility, pointerEvents: element.style.pointerEvents, aria: element.getAttribute('aria-hidden')});
        const saved = elements.get(element), hide = hidden(node.outputs[index]);
        element.style.visibility = hide ? 'hidden' : saved.visibility;
        element.style.pointerEvents = hide ? 'none' : saved.pointerEvents;
        if (hide) element.setAttribute('aria-hidden', 'true');
        else if (saved.aria == null) element.removeAttribute('aria-hidden');
        else element.setAttribute('aria-hidden', saved.aria);
      });
    }
  }
  update();
  return {update, dispose() {
    for (const [output, saved] of drawings) restore(output, 'draw', saved.descriptor);
    for (const [name, descriptor] of methods) restore(node, name, descriptor);
    for (const [element, saved] of elements) {
      element.style.visibility = saved.visibility; element.style.pointerEvents = saved.pointerEvents;
      if (saved.aria == null) element.removeAttribute('aria-hidden'); else element.setAttribute('aria-hidden', saved.aria);
    }
    drawings.clear(); elements.clear();
  }};
}
