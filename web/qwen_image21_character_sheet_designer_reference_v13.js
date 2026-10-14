import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';
import {createExtension, getDesigner} from './multi_integration.js';

const profile = {
  nodeType: 'QwenImage21CharacterSheetDesignerReferenceV13',
  displayName: 'Qwen 2.1 Sheet Designer Reference V1.3',
  extensionName: 'qwen21.CharacterSheetDesignerReferenceV13',
  previewPath: '/qwen_image21_character_sheet_designer/reference_v13_preview',
  perOutputReferences: true, partChoices: true,
};
const fields = ['sheet_size_mode', 'sheet_width', 'sheet_height'];
const instances = new WeakMap();

app.registerExtension({
  name: profile.extensionName,
  nodeCreated(node) {
    if (node.comfyClass !== profile.nodeType && node.type !== profile.nodeType) return;
    const read = () => Object.fromEntries(fields.map(name => [name, node.widgets.find(w => w.name === name)?.value]));
    const proxy = {fetchApi(path, options) {
      return api.fetchApi(path, {...options, body: JSON.stringify({...JSON.parse(options.body), ...read()})});
    }};
    createExtension(app, proxy, profile).nodeCreated(node);
    const designer = getDesigner(node);
    if (!designer) return;
    for (const field of fields) {
      const widget = node.widgets.find(w => w.name === field);
      if (widget) widget.label = {sheet_size_mode: 'Sheet canvas mode / 合成サイズ', sheet_width: 'Sheet width / 合成幅', sheet_height: 'Sheet height / 合成高さ'}[field];
    }
    const section = document.createElement('section');
    section.style.cssText = 'padding:10px;border:1px solid #496778;border-radius:8px;margin:8px 0';
    const title = document.createElement('div');
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'width:100%;display:block;background:white;margin-top:6px';
    const hint = document.createElement('small');
    hint.textContent = 'Assembly panel placement / 合成用パネル配置。生成サイズは上のOutput size、合成サイズはノードのSheet canvas設定。';
    section.append(title, canvas, hint);
    designer.ui.root.append(section);
    let disposed = false, frame, observed = JSON.stringify(read()), rendered = null;
    const update = () => {
      if (disposed) return;
      const key = JSON.stringify(read());
      if (key !== observed) { observed = key; rendered = null; void designer.controller.refreshPreview(); }
      const preview = designer.controller.preview;
      const plan = preview?.sheet_plan;
      const current = designer.controller.isCurrentPreview;
      section.style.opacity = current ? '1' : '.5';
      if (plan && rendered !== plan.plan_hash) {
        rendered = plan.plan_hash;
        const [width, height] = plan.canvas;
        canvas.width = width; canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'white'; ctx.fillRect(0, 0, width, height);
        ctx.strokeStyle = '#222'; ctx.lineWidth = 1;
        ctx.font = `${Math.max(12, Math.round(Math.min(width, height) / 45))}px sans-serif`;
        for (const view of plan.views) {
          const [left, top, right, bottom] = view.bounds;
          ctx.strokeRect(left + .5, top + .5, right - left - 1, bottom - top - 1);
          ctx.fillStyle = '#243844'; ctx.fillText(view.view_id, left + 6, top + 24, right - left - 12);
        }
        title.textContent = `Sheet assembly / 合成配置: ${width} × ${height} · ${plan.views.length} views`;
        canvas.dataset.planHash = plan.plan_hash;
        canvas.dataset.panelBounds = JSON.stringify(plan.views);
      }
      frame = requestAnimationFrame(update);
    };
    const previous = node.onRemoved;
    node.onRemoved = function(...args) {
      disposed = true; cancelAnimationFrame(frame); section.remove(); instances.delete(node);
      return previous?.apply(this, args);
    };
    instances.set(node, {refresh: () => designer.afterConfigure()});
    frame = requestAnimationFrame(update);
  },
  afterConfigureGraph() {
    for (const node of app.graph?._nodes ?? []) instances.get(node)?.refresh();
  },
});
