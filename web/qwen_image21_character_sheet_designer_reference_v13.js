import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';
import {createExtension, graphTransaction} from './multi_integration.js';
import {SHEET_FIELDS, installAssemblyUI} from './sheet_assembly_ui.js';
import {installOptionalOutputs} from './optional_outputs.js';

const profile = {
  nodeType: 'QwenImage21CharacterSheetDesignerReferenceV13',
  displayName: 'Qwen 2.1 Sheet Designer Reference V1.3',
  extensionName: 'qwen21.CharacterSheetDesignerReferenceV13',
  previewPath: '/qwen_image21_character_sheet_designer/reference_v13_preview',
  perOutputReferences: true, partChoices: true,
};
const instances = new WeakMap();

function installAdditionalUI(node, designer) {
  const read = () => Object.fromEntries(SHEET_FIELDS.map(name => [name, node.widgets.find(w => w.name === name)?.value]));
  const assembly = installAssemblyUI(node, designer, (widget, value) => {
    const previous = widget.value;
    if (value === previous) return;
    graphTransaction(node, () => {
      widget.value = value;
      node.onWidgetChanged?.(widget.name, value, previous, widget);
    }, app.canvas);
  });
  const optionalOutputs = installOptionalOutputs(node, designer.ui.root, action => graphTransaction(node, action, app.canvas));
  let disposed = false, frame, observed = JSON.stringify(read());
  const update = () => {
    if (disposed) return;
    const key = JSON.stringify(read());
    if (key !== observed) { observed = key; void designer.controller.refreshPreview(); }
    assembly?.update(); optionalOutputs.update();
    frame = requestAnimationFrame(update);
  };
  instances.set(node, {refresh: () => designer.afterConfigure()});
  frame = requestAnimationFrame(update);
  return () => {
    disposed = true; cancelAnimationFrame(frame);
    assembly?.dispose(); optionalOutputs.dispose(); instances.delete(node);
  };
}

app.registerExtension({
  name: profile.extensionName,
  nodeCreated(node) {
    if (node.comfyClass !== profile.nodeType && node.type !== profile.nodeType) return;
    const read = () => Object.fromEntries(SHEET_FIELDS.map(name => [name, node.widgets.find(w => w.name === name)?.value]));
    const proxy = {fetchApi(path, options) {
      return api.fetchApi(path, {...options, body: JSON.stringify({...JSON.parse(options.body), ...read()})});
    }};
    createExtension(app, proxy, profile, installAdditionalUI).nodeCreated(node);
  },
  afterConfigureGraph() {
    for (const node of app.graph?._nodes ?? []) instances.get(node)?.refresh();
  },
});
