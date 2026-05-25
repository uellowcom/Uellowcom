/** @odoo-module **/
/**
 * Uellow TikTok Video - Backend JS
 * Adds a preview panel in the product form when editing videos.
 */

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { Component, useState, onWillUpdateProps } from "@odoo/owl";

// Simple TikTok URL preview component shown in backend list
class TikTokPreviewField extends CharField {
    get previewUrl() {
        const val = this.props.record.data[this.props.name];
        if (!val) return null;
        const match = val.match(/tiktok\.com\/@[\w.]+\/video\/(\d+)/);
        if (match) {
            return `https://www.tiktok.com/embed/v2/${match[1]}`;
        }
        return null;
    }
}
TikTokPreviewField.template = "uellow_tiktok_video.TikTokPreviewField";

// Backend CSS is minimal - just ensure video tabs look good
