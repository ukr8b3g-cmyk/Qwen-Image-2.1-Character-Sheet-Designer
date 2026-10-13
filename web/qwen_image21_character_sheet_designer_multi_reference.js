import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';
import {createExtension} from './multi_integration.js';
app.registerExtension(createExtension(app, api));
