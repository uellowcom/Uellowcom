/** @odoo-module **/
/**
 * Flash Sale V49 – Snippet Options
 *
 * Registers editor options that appear in the right-hand panel when
 * the user selects the Flash Sale V49 block in the website builder.
 */

import options from "@web_editor/js/editor/snippets.options";

options.registry.FlashSaleV49 = options.Class.extend({
    /**
     * Update the category ID used to fetch products.
     * The value is stored as a data attribute on the wrapper element.
     */
    setCategoryId(previewMode, widgetValue) {
        const catId = parseInt(widgetValue, 10);
        if (!isNaN(catId) && catId > 0) {
            this.$target[0].dataset.categoryId = catId;
        }
    },

    /**
     * Update the "More" button href.
     */
    setMoreLink(previewMode, widgetValue) {
        const btn = this.$target[0].querySelector("#v49_btn_link");
        if (btn && widgetValue) {
            btn.setAttribute("href", widgetValue);
        }
    },

    /**
     * Update the block title text.
     */
    setTitle(previewMode, widgetValue) {
        const title = this.$target[0].querySelector("#v49_title_text");
        if (title && widgetValue) {
            title.innerText = widgetValue;
        }
    },
});
