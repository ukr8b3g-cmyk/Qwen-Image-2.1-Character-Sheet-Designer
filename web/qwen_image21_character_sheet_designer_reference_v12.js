import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';
import {createExtension} from './multi_integration.js';

app.registerExtension(createExtension(app, api, {
  nodeType: 'QwenImage21CharacterSheetDesignerReferenceV12',
  displayName: 'Qwen 2.1 Sheet Designer Reference V1.2',
  extensionName: 'qwen21.CharacterSheetDesignerReferenceV12',
  previewPath: '/qwen_image21_character_sheet_designer/reference_v12_preview',
  perOutputReferences: true,
  partChoices: true,
}));
