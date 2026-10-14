export const SHEET_FIELDS = ['sheet_size_mode', 'sheet_width', 'sheet_height'];

export function installAssemblyUI(node, designer, writeValue) {
  const root = designer.ui.root;
  const head = root.querySelector('.q21-mr-preview-head');
  const tag = root.querySelector('.q21-mr-preview-tag');
  const stage = root.querySelector('[data-preview-stage]');
  if (!head || !stage || !tag) return null;
  const widgets = SHEET_FIELDS.map(name => node.widgets.find(widget => widget.name === name));
  if (widgets.some(widget => !widget)) return null;
  const hidden = widgets.map(widget => widget.options?.hidden ?? widget.hidden);
  widgets.forEach(widget => { widget.hidden = true; });
  const toggle = document.createElement('button');
  toggle.type = 'button'; toggle.className = 'q21-mr-tab'; toggle.hidden = true;
  toggle.dataset.sheetAssemblyToggle = '';
  toggle.title = 'Preview the assembled sheet / 合成先の配置を確認';
  head.append(toggle);
  const overlay = document.createElement('div');
  overlay.hidden = true; overlay.dataset.sheetAssembly = '';
  overlay.style.cssText = 'position:absolute;inset:0;padding:12px;display:flex;flex-direction:column;gap:8px;background:var(--q21-mr-panel);z-index:1';
  const controls = document.createElement('div');
  controls.className = 'q21-mr-controls'; controls.style.flexShrink = '0';
  const inputs = widgets.map((widget, index) => {
    const label = document.createElement('label');
    label.className = 'q21-mr-number-field'; label.style.flex = '1';
    const text = document.createElement('span');
    text.textContent = ['Sheet canvas / 合成サイズ', 'Width / 幅', 'Height / 高さ'][index];
    text.style.cssText = 'font-size:14px;color:var(--q21-mr-muted)';
    const input = document.createElement(index === 0 ? 'select' : 'input');
    input.className = 'q21-mr-select'; input.dataset.sheetField = widget.name;
    if (index === 0) {
      for (const mode of ['auto', 'manual']) {
        const option = document.createElement('option');
        option.value = mode; option.textContent = mode === 'auto' ? 'Auto' : 'Manual'; input.append(option);
      }
    } else {
      input.type = 'number'; input.min = 32; input.step = 32; input.required = true;
      if (widget.options?.max) input.max = widget.options.max;
    }
    const commit = () => {
      if (index && !input.reportValidity()) return;
      writeValue(widget, index ? Number(input.value) : input.value);
      update();
    };
    input.addEventListener('change', commit);
    if (index) {
      input.addEventListener('blur', commit);
      input.addEventListener('keydown', event => { if (event.key === 'Enter') commit(); });
    }
    label.append(text, input); controls.append(label); return input;
  });
  const holder = document.createElement('div');
  holder.style.cssText = 'flex:1;min-height:0;display:flex;align-items:center;justify-content:center';
  const canvas = document.createElement('canvas');
  canvas.style.cssText = 'display:block;max-width:100%;max-height:100%;object-fit:contain';
  holder.append(canvas);
  const hint = document.createElement('small');
  hint.textContent = 'Sheet canvas only. Output size still controls each generated image. / 合成先のみ。生成サイズは上のOutput size。';
  hint.style.fontSize = '12px'; overlay.append(controls, holder, hint);
  const previousPosition = stage.style.position;
  const content = [...stage.children].map(element => [element, element.inert]);
  stage.style.position = 'relative'; stage.append(overlay);
  let active = false, rendered;
  const show = value => {
    active = value; overlay.hidden = !value; toggle.setAttribute('aria-pressed', String(value));
    content.forEach(([element, inert]) => { element.inert = value || inert; });
  };
  const onToggle = () => { show(!active); update(); };
  const onTab = event => { if (event.target.closest('[data-tab]')) { show(false); update(); } };
  toggle.addEventListener('click', onToggle); head.addEventListener('click', onTab);
  function update() {
    const linked = node.outputs?.find(output => output.name === 'sheet_plan')?.links?.length > 0;
    const batch = node.widgets.find(widget => widget.name === 'batch_out')?.value === true;
    const available = linked && batch && !stage.hidden;
    toggle.hidden = !available; tag.hidden = available;
    if (!available) show(false);
    toggle.textContent = active ? 'Layout / レイアウト' : 'Assembly / 合成';
    toggle.setAttribute('aria-pressed', String(active));
    const plan = designer.controller.preview?.sheet_plan;
    inputs.forEach((input, i) => {
      input.disabled = i > 0 && widgets[0].value === 'auto';
      const value = i > 0 && widgets[0].value === 'auto' && plan ? plan.canvas[i - 1] : widgets[i].value;
      if (document.activeElement !== input) input.value = String(value);
    });
    if (!active || !plan) return;
    overlay.style.opacity = designer.controller.isCurrentPreview ? '1' : '.5';
    if (rendered !== plan.plan_hash) {
      rendered = plan.plan_hash;
      const [width, height] = plan.canvas; canvas.width = width; canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'white'; ctx.fillRect(0, 0, width, height);
      ctx.strokeStyle = '#222'; ctx.lineWidth = 1;
      ctx.font = `${Math.max(12, Math.round(Math.min(width, height) / 45))}px sans-serif`;
      for (const view of plan.views) {
        const [left, top, right, bottom] = view.bounds;
        ctx.strokeRect(left + .5, top + .5, right - left - 1, bottom - top - 1);
        ctx.fillStyle = '#243844'; ctx.fillText(view.view_id, left + 6, top + 24, right - left - 12);
      }
      canvas.dataset.planHash = plan.plan_hash;
      canvas.dataset.panelBounds = JSON.stringify(plan.views);
      canvas.setAttribute('aria-label', `Sheet canvas ${width} × ${height} · ${plan.views.length} views`);
    }
  }
  update();
  return {update, dispose() {
    show(false);
    head.removeEventListener('click', onTab); toggle.removeEventListener('click', onToggle);
    toggle.remove(); overlay.remove(); tag.hidden = false; stage.style.position = previousPosition;
    widgets.forEach((widget, i) => { widget.hidden = hidden[i]; });
  }};
}
