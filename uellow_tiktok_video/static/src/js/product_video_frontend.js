/** @odoo-module **/
/**
 * Uellow TikTok Video Gallery - Frontend JS
 * Handles video rendering in product page gallery and shop listing overlays.
 */

import { onMounted } from "@odoo/owl";
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

// ============================================================
// Product Page: Video Gallery Widget
// ============================================================
publicWidget.registry.UellowProductVideoGallery = publicWidget.Widget.extend({
    selector: '#uellow_product_video_area',
    events: {
        'click .uellow-video-thumb': '_onThumbClick',
        'click .uellow-video-close-btn': '_onClosePlayer',
    },

    start() {
        this._super(...arguments);
        const productTmplId = parseInt(this.el.dataset.productTmplId, 10);
        if (productTmplId) {
            this._loadVideos(productTmplId);
        }
        return Promise.resolve();
    },

    async _loadVideos(productTmplId) {
        try {
            const result = await rpc('/uellow/product/video/' + productTmplId, {});
            if (result && result.videos && result.videos.length) {
                this._renderVideos(result.videos);
            }
        } catch (err) {
            console.warn('[Uellow Video] Failed to load videos:', err);
        }
    },

    _renderVideos(videos) {
        if (!videos || !videos.length) return;

        // Build the video section HTML
        const first = videos[0];
        const html = `
            <div class="uellow-video-section">
                <div class="uellow-main-video-container" data-video-type="${first.type}">
                    ${this._buildMainPlayer(first)}
                </div>
                ${videos.length > 1 ? this._buildThumbnailBar(videos) : ''}
            </div>
        `;
        this.el.innerHTML = html;

        // Re-attach TikTok embed script if needed
        this._initTikTokEmbed();
    },

    _buildMainPlayer(video) {
        if (video.type === 'tiktok_url') {
            if (video.tiktok_video_id && !video.tiktok_video_id.startsWith('short:')) {
                return `
                    <div class="uellow-tiktok-embed-wrapper">
                        <div class="uellow-tiktok-ratio">
                            <iframe
                                src="https://www.tiktok.com/embed/v2/${video.tiktok_video_id}"
                                class="uellow-tiktok-iframe"
                                allowfullscreen
                                scrolling="no"
                                allow="encrypted-media"
                                title="${this._esc(video.name)}"
                            ></iframe>
                        </div>
                        <div class="uellow-video-label">
                            <span class="uellow-tiktok-badge">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.27 6.27 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.18 8.18 0 004.77 1.52V6.78a4.85 4.85 0 01-1-.09z"/>
                                </svg>
                                TikTok
                            </span>
                            ${this._esc(video.name)}
                        </div>
                    </div>
                `;
            } else {
                // Short URL fallback - show link
                return `
                    <div class="uellow-tiktok-fallback">
                        <p>⚠️ لا يمكن تضمين هذا الفيديو مباشرة.</p>
                        <a href="${this._esc(video.tiktok_url)}" target="_blank" rel="noopener" class="btn btn-dark">
                            مشاهدة على TikTok
                        </a>
                    </div>
                `;
            }
        } else if (video.type === 'direct_upload' && video.file_url) {
            return `
                <div class="uellow-direct-video-wrapper">
                    <video
                        class="uellow-direct-video"
                        controls
                        preload="metadata"
                        playsinline
                    >
                        <source src="${this._esc(video.file_url)}" type="${this._esc(video.mimetype || 'video/mp4')}"/>
                        متصفحك لا يدعم تشغيل الفيديو.
                    </video>
                </div>
            `;
        } else if (video.embed_url) {
            return `
                <div class="uellow-iframe-video-wrapper">
                    <div class="uellow-iframe-ratio">
                        <iframe
                            src="${this._esc(video.embed_url)}"
                            class="uellow-video-iframe"
                            allowfullscreen
                            allow="autoplay; encrypted-media"
                            title="${this._esc(video.name)}"
                            frameborder="0"
                        ></iframe>
                    </div>
                </div>
            `;
        }
        return '<div class="uellow-no-video">لا يمكن تشغيل هذا الفيديو</div>';
    },

    _buildThumbnailBar(videos) {
        const thumbs = videos.map((v, i) => `
            <div class="uellow-video-thumb ${i === 0 ? 'active' : ''}"
                 data-video-index="${i}"
                 data-video-json="${this._esc(JSON.stringify(v))}">
                <div class="uellow-video-thumb-icon">
                    ${this._getVideoTypeIcon(v.type)}
                </div>
                <span class="uellow-video-thumb-name">${this._esc(v.name)}</span>
            </div>
        `).join('');
        return `<div class="uellow-video-thumbs-bar">${thumbs}</div>`;
    },

    _getVideoTypeIcon(type) {
        if (type === 'tiktok_url') {
            return `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.27 6.27 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.18 8.18 0 004.77 1.52V6.78a4.85 4.85 0 01-1-.09z"/>
            </svg>`;
        }
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
        </svg>`;
    },

    _onThumbClick(ev) {
        const thumb = ev.currentTarget;
        const videoData = JSON.parse(thumb.dataset.videoJson);
        const container = this.el.querySelector('.uellow-main-video-container');
        if (container) {
            container.innerHTML = this._buildMainPlayer(videoData);
            container.dataset.videoType = videoData.type;
            this._initTikTokEmbed();
        }
        // Update active state
        this.el.querySelectorAll('.uellow-video-thumb').forEach(t => t.classList.remove('active'));
        thumb.classList.add('active');
    },

    _onClosePlayer() {
        this.el.querySelector('.uellow-main-video-container').innerHTML = '';
    },

    _initTikTokEmbed() {
        // Load TikTok embed script if not already loaded
        if (!document.querySelector('script[src*="tiktok.com/embed.js"]')) {
            const script = document.createElement('script');
            script.src = 'https://www.tiktok.com/embed.js';
            script.async = true;
            document.body.appendChild(script);
        } else if (window.tiktok) {
            // Re-trigger existing TikTok embed
            try { window.tiktok.reload(); } catch (e) {}
        }
    },

    _esc(str) {
        if (typeof str !== 'string') return str;
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },
});

export default publicWidget.registry.UellowProductVideoGallery;
