/** @odoo-module **/
/**
 * UW Hot Categories — Editor Options  v4.0
 * Reads/writes settings from JSON <script> tag inside the snippet
 * Odoo saves the full page HTML → settings persist automatically
 */

(function () {
    'use strict';

    function waitOdoo(cb, tries) {
        tries = tries || 0;
        if (tries > 50) return;
        if (typeof odoo !== 'undefined' && odoo.define) { cb(); }
        else { setTimeout(function () { waitOdoo(cb, tries + 1); }, 300); }
    }

    waitOdoo(function () {
        odoo.define('uw_hot_categories.snippet_options', function (require) {
            'use strict';

            var options;
            try { options = require('web_editor.snippet.options'); }
            catch (e) { return; }
            if (!options || !options.SnippetOptionWidget) return;

            /* ── Read JSON config from script tag ── */
            function readCfg(section) {
                try {
                    var el = section.querySelector('script.uw_hc_config');
                    if (!el) return {};
                    return JSON.parse(el.textContent) || {};
                } catch (e) { return {}; }
            }

            /* ── Write JSON config to script tag — this is what Odoo saves ── */
            function writeCfg(section, cfg) {
                var el = section.querySelector('script.uw_hc_config');
                if (!el) {
                    el = document.createElement('script');
                    el.type = 'application/json';
                    el.className = 'uw_hc_config';
                    section.insertBefore(el, section.firstChild);
                }
                el.textContent = JSON.stringify(cfg, null, 2);
            }

            /* ── Get nested value: "subs.0" → cfg.subs[0] ── */
            function getField(cfg, path) {
                var parts = path.split('.');
                var v = cfg;
                for (var i = 0; i < parts.length; i++) {
                    if (v === undefined || v === null) return '';
                    v = v[parts[i]];
                }
                return (v === undefined || v === null) ? '' : String(v);
            }

            /* ── Set nested value: "subs.0", "861" → cfg.subs[0] = 861 ── */
            function setField(cfg, path, value) {
                var parts = path.split('.');
                var obj = cfg;
                for (var i = 0; i < parts.length - 1; i++) {
                    if (obj[parts[i]] === undefined) obj[parts[i]] = {};
                    obj = obj[parts[i]];
                }
                var last = parts[parts.length - 1];
                // Auto-convert to int if field is numeric
                var numFields = ['mainCat', '0', '1', '2', '3', '4', '5'];
                if (numFields.indexOf(last) !== -1 || path.startsWith('subs')) {
                    var n = parseInt(value, 10);
                    obj[last] = isNaN(n) ? value : n;
                } else if (value === 'true') {
                    obj[last] = true;
                } else if (value === 'false') {
                    obj[last] = false;
                } else {
                    obj[last] = value;
                }
            }

            /* ── Trigger snippet reload ── */
            function reloadSnippet(section) {
                section.removeAttribute('data-uw-rendered');
                var old = document.getElementById('uw_style_' + section.id);
                if (old) old.remove();
                if (window.uwHotCatsReload) {
                    window.uwHotCatsReload(section);
                }
            }

            options.registry.UwHotCats = options.SnippetOptionWidget.extend({

                /**
                 * Called by Odoo for each widget in the options panel.
                 * We intercept inputs with data-uw-field.
                 */
                selectClass: function (previewMode, widgetValue, params) {
                    return this._handleUwOption(previewMode, widgetValue, params)
                        || this._super.apply(this, arguments);
                },

                selectStyle: function (previewMode, widgetValue, params) {
                    return this._handleUwOption(previewMode, widgetValue, params)
                        || this._super.apply(this, arguments);
                },

                /**
                 * Handle our custom data-uw-field inputs
                 */
                _handleUwOption: function (previewMode, widgetValue, params) {
                    var section = this.$target[0];
                    if (!section) return false;

                    // Handle reload button
                    var widget = params && params.$widget && params.$widget[0];
                    if (widget && widget.dataset.uwReload && !previewMode) {
                        reloadSnippet(section);
                        return true;
                    }

                    // Handle field inputs
                    var field = widget && widget.dataset.uwField;
                    if (!field) return false;

                    if (!previewMode) {
                        var cfg = readCfg(section);
                        setField(cfg, field, widgetValue);
                        writeCfg(section, cfg);
                        reloadSnippet(section);
                    }
                    return true;
                },

                /**
                 * Read current value for a widget (populates the options panel)
                 */
                _computeWidgetState: function (methodName, params) {
                    var section = this.$target[0];
                    if (!section) return this._super.apply(this, arguments);

                    var widget = params && params.$widget && params.$widget[0];
                    var field = widget && widget.dataset.uwField;
                    if (field) {
                        var cfg = readCfg(section);
                        return getField(cfg, field);
                    }
                    return this._super.apply(this, arguments);
                },

                /**
                 * Reload button handler
                 */
                reloadProducts: function (previewMode) {
                    if (previewMode) return;
                    reloadSnippet(this.$target[0]);
                },
            });
        });
    });

}());
