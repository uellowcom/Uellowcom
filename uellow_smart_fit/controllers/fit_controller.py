import json
import logging
from types import SimpleNamespace

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── Size Charts ───────────────────────────────────────────────────────────────
# Standard measurements per size for different categories

SHIRT_CHEST = {
    'XS': (80, 88),  'S': (88, 96),  'M': (96, 104),
    'L': (104, 112), 'XL': (112, 120), 'XXL': (120, 130), '3XL': (130, 142),
}

SHIRT_SHOULDER = {
    'XS': (38, 41), 'S': (41, 43), 'M': (43, 45),
    'L': (45, 47),  'XL': (47, 50), 'XXL': (50, 53), '3XL': (53, 57),
}

PANTS_WAIST = {
    '28': (68, 73), '30': (73, 78), '32': (78, 83), '34': (83, 88),
    '36': (88, 93), '38': (93, 98), '40': (98, 105), '42': (105, 112),
}

DRESS_CHEST = {
    'XS': (78, 83), 'S': (83, 88), 'M': (88, 93),
    'L': (93, 98),  'XL': (98, 105), 'XXL': (105, 113),
}

SHOE_EU_TO_CM = {
    35: 22.0, 36: 22.5, 37: 23.5, 38: 24.0, 39: 24.5,
    40: 25.5, 41: 26.0, 42: 26.5, 43: 27.5, 44: 28.0,
    45: 28.5, 46: 29.5, 47: 30.0, 48: 30.5,
}

FIT_TOLERANCE = {
    'slim':    -1,   # Prefer smaller
    'regular':  0,
    'loose':    1,   # Prefer larger
}

# ── Per-area analysis constants ───────────────────────────────────────────────
# Comfort ease (in cm) — how much bigger the garment should be than the body.
# (min_ease, max_ease). Below min = tight; above max = loose; within = comfortable.
EASE_RANGES = {
    'chest':    (4.0,  12.0),
    'waist':    (2.0,  10.0),
    'hip':      (3.0,  10.0),
    'shoulder': (-1.0,  1.5),
    'length':   (-3.0,  5.0),
    'sleeve':   (-1.0,  3.0),
    'inseam':   (-2.0,  3.0),
    'thigh':    (2.0,   8.0),
    # Shoes: shoe inner length minus foot length. Want a little wiggle room.
    'foot_length': (0.5, 1.5),
}

# Weight of each area when computing the overall match score.
AREA_WEIGHTS = {
    'chest': 35, 'shoulder': 25, 'sleeve': 10, 'length': 15,
    'waist': 30, 'hip': 25, 'inseam': 10, 'thigh': 10,
    'foot_length': 100,
}

# Bilingual labels for the UI.
AREA_LABELS = {
    'chest':       {'ar': 'الصدر',     'en': 'Chest'},
    'shoulder':    {'ar': 'الكتف',     'en': 'Shoulder'},
    'sleeve':      {'ar': 'الكم',      'en': 'Sleeve'},
    'length':      {'ar': 'الطول',     'en': 'Length'},
    'waist':       {'ar': 'الوسط',     'en': 'Waist'},
    'hip':         {'ar': 'الورك',     'en': 'Hip'},
    'inseam':      {'ar': 'الساق',     'en': 'Inseam'},
    'thigh':       {'ar': 'الفخذ',     'en': 'Thigh'},
    'foot_length': {'ar': 'طول القدم', 'en': 'Foot length'},
}

# Which areas matter for which category.
RELEVANT_AREAS_BY_CATEGORY = {
    'shirt':   ['chest', 'shoulder', 'sleeve', 'length'],
    'tshirt':  ['chest', 'shoulder', 'sleeve', 'length'],
    'top':     ['chest', 'shoulder', 'sleeve', 'length'],
    'jacket':  ['chest', 'shoulder', 'sleeve', 'length'],
    'sweater': ['chest', 'shoulder', 'sleeve', 'length'],
    'hoodie':  ['chest', 'shoulder', 'sleeve', 'length'],
    'coat':    ['chest', 'shoulder', 'sleeve', 'length'],
    'dress':   ['chest', 'waist', 'hip', 'length'],
    'gown':    ['chest', 'waist', 'hip', 'length'],
    'abaya':   ['chest', 'shoulder', 'length'],
    'pants':   ['waist', 'hip', 'inseam', 'thigh'],
    'jeans':   ['waist', 'hip', 'inseam', 'thigh'],
    'shorts':  ['waist', 'hip', 'thigh'],
    'skirt':   ['waist', 'hip', 'length'],
    'shoe':    ['foot_length'],
    'sneaker': ['foot_length'],
    'boot':    ['foot_length'],
    'sandal':  ['foot_length'],
    'slipper': ['foot_length'],
    'generic': ['chest', 'shoulder', 'waist', 'hip', 'length'],
}


class SmartFitController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            f'uellow_fit.{key}', default
        )

    @staticmethod
    def _num(v, default=0.0):
        """Parse a client-supplied numeric value without ever raising.
        Public endpoints receive arbitrary strings; a bad value must yield a
        clean fallback, not an HTTP 500."""
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _int_id(v):
        """Parse a client-supplied record id; return None on garbage."""
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    def _get_or_create_profile(self):
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return None
        partner = request.env.user.partner_id
        profile = request.env['customer.body.profile'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )
        if not profile:
            profile = request.env['customer.body.profile'].sudo().create({
                'partner_id': partner.id,
            })
        return profile

    # ── Core Analysis Algorithm ───────────────────────────────────────────────

    def _analyze_fit(self, profile_data, product_sizes, category):
        """
        Compare customer measurements against product size chart.
        Returns ranked list of sizes with fit scores.
        """
        if not profile_data or not product_sizes:
            return []

        chest      = profile_data.get('chest', 0)
        waist      = profile_data.get('waist', 0)
        shoulder   = profile_data.get('shoulder', 0)
        hip        = profile_data.get('hip', 0)
        height     = profile_data.get('height', 0)
        shoe_eu    = profile_data.get('shoe_size_eu', 0)
        pref_fit   = profile_data.get('preferred_fit', 'regular')
        tolerance  = FIT_TOLERANCE.get(pref_fit, 0)

        results = []

        for size_name in product_sizes:
            size_upper = size_name.upper().strip()
            score      = 0
            issues     = []
            details    = {}

            # ── Shirt / Top analysis ──────────────────────────────────────────
            if category in ('shirt', 'top', 'jacket', 'tshirt', 'sweater', 'hoodie', 'coat'):
                if chest and size_upper in SHIRT_CHEST:
                    lo, hi  = SHIRT_CHEST[size_upper]
                    ideal   = (lo + hi) / 2
                    ease    = 4 + tolerance * 2  # comfort ease
                    fit_lo  = lo - ease
                    fit_hi  = hi + ease

                    if fit_lo <= chest <= fit_hi:
                        fit_pct = 100 - abs(chest - ideal) / (hi - lo) * 40
                        score  += fit_pct
                        details['chest'] = {'status': 'perfect', 'diff': round(chest - ideal, 1)}
                    elif chest < fit_lo:
                        score  += 40
                        diff    = round(fit_lo - chest, 1)
                        issues.append(f'الصدر واسع +{diff}cm')
                        details['chest'] = {'status': 'loose', 'diff': diff}
                    else:
                        score  += 20
                        diff    = round(chest - fit_hi, 1)
                        issues.append(f'الصدر ضيق {diff}cm')
                        details['chest'] = {'status': 'tight', 'diff': diff}

                if shoulder and size_upper in SHIRT_SHOULDER:
                    lo, hi  = SHIRT_SHOULDER[size_upper]
                    if lo <= shoulder <= hi:
                        score  += 30
                        details['shoulder'] = {'status': 'perfect', 'diff': 0}
                    elif shoulder < lo - 1:
                        score  += 15
                        details['shoulder'] = {'status': 'loose', 'diff': round(lo - shoulder, 1)}
                    elif shoulder > hi + 1:
                        score  += 10
                        issues.append('الكتف ضيق')
                        details['shoulder'] = {'status': 'tight', 'diff': round(shoulder - hi, 1)}
                    else:
                        score  += 25
                        details['shoulder'] = {'status': 'ok', 'diff': 0}

            # ── Pants / Bottom analysis ────────────────────────────────────────
            elif category in ('pants', 'jeans', 'shorts', 'trousers', 'skirt'):
                if waist and size_upper in PANTS_WAIST:
                    lo, hi  = PANTS_WAIST[size_upper]
                    ease    = 2 + tolerance * 2
                    if lo - ease <= waist <= hi + ease:
                        fit_pct = 100 - abs(waist - (lo + hi) / 2) / (hi - lo) * 30
                        score  += fit_pct
                        details['waist'] = {'status': 'perfect', 'diff': round(waist - (lo+hi)/2, 1)}
                    elif waist < lo - ease:
                        score  += 35
                        details['waist'] = {'status': 'loose', 'diff': round(lo - waist, 1)}
                    else:
                        score  += 15
                        issues.append(f'الوسط ضيق')
                        details['waist'] = {'status': 'tight', 'diff': round(waist - hi, 1)}

                if hip:
                    details['hip'] = {'status': 'checked', 'value': hip}

            # ── Dress analysis ────────────────────────────────────────────────
            elif category in ('dress', 'abaya', 'gown'):
                if chest and size_upper in DRESS_CHEST:
                    lo, hi = DRESS_CHEST[size_upper]
                    if lo <= chest <= hi + 4:
                        score  += 80
                        details['chest'] = {'status': 'perfect', 'diff': 0}
                    else:
                        score  += 30
                        details['chest'] = {'status': 'check', 'diff': round(abs(chest - (lo+hi)/2), 1)}

            # ── Shoe analysis ─────────────────────────────────────────────────
            elif category in ('shoe', 'sneaker', 'sandal', 'boot', 'slipper'):
                if shoe_eu:
                    try:
                        size_num = float(size_upper)
                        diff     = abs(shoe_eu - size_num)
                        if diff == 0:
                            score  += 100
                            details['shoe'] = {'status': 'perfect', 'diff': 0}
                        elif diff <= 0.5:
                            score  += 80
                            details['shoe'] = {'status': 'close', 'diff': diff}
                        elif diff <= 1:
                            score  += 50
                            issues.append('قريب من مقاسك')
                            details['shoe'] = {'status': 'close', 'diff': diff}
                        else:
                            score  += 10
                            details['shoe'] = {'status': 'far', 'diff': diff}
                    except ValueError:
                        pass

            # ── Generic (no category match) ───────────────────────────────────
            else:
                score = 50  # neutral

            results.append({
                'size':       size_name,
                'score':      round(score),
                'issues':     issues,
                'details':    details,
                'recommended': False,
            })

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        # Mark top as recommended
        if results:
            results[0]['recommended'] = True

        # Add fit labels. Cap the score at 100 — for shirts/tops the chest
        # contribution can reach 100 and shoulder adds up to another 30, so the
        # raw sum can exceed 100. Ranking above already used the raw score.
        for r in results:
            s = min(r['score'], 100)
            r['score'] = s
            if s >= 85:
                r['fit_label'] = 'مناسب تماماً'
                r['fit_color'] = 'green'
            elif s >= 65:
                r['fit_label'] = 'مناسب'
                r['fit_color'] = 'yellow'
            elif s >= 40:
                r['fit_label'] = 'مقبول'
                r['fit_color'] = 'orange'
            else:
                r['fit_label'] = 'غير مناسب'
                r['fit_color'] = 'red'

        return results

    # ── Per-area analysis using the per-product size chart ───────────────────

    def _classify_area(self, body_value, garment_value, area, tolerance=0.0):
        """Compare one body region to a garment dimension.
        Returns dict {fit, diff_cm, pct} or None if missing data."""
        if not body_value or not garment_value:
            return None
        diff = round(garment_value - body_value, 1)
        lo, hi = EASE_RANGES.get(area, (-2.0, 5.0))
        lo -= (tolerance or 0)
        hi += (tolerance or 0)

        if diff < lo:
            gap = lo - diff
            pct = max(0, int(round(100 - gap * 20)))
            return {'fit': 'tight', 'diff_cm': diff, 'pct': pct,
                    'garment_cm': garment_value, 'body_cm': body_value}
        if diff > hi:
            gap = diff - hi
            pct = max(0, int(round(100 - gap * 15)))
            return {'fit': 'loose', 'diff_cm': diff, 'pct': pct,
                    'garment_cm': garment_value, 'body_cm': body_value}

        mid = (lo + hi) / 2
        rng = max((hi - lo) / 2, 0.1)
        pct = max(85, int(round(100 - abs(diff - mid) / rng * 15)))
        return {'fit': 'comfortable', 'diff_cm': diff, 'pct': pct,
                'garment_cm': garment_value, 'body_cm': body_value}

    def _analyze_chart_size(self, profile, chart_row, category):
        """Compute per-area verdict + overall % for one size row."""
        relevant = RELEVANT_AREAS_BY_CATEGORY.get(category, RELEVANT_AREAS_BY_CATEGORY['generic'])
        # Mapping: profile field → chart field
        profile_field = {
            'chest': 'chest', 'shoulder': 'shoulder',
            'waist': 'waist', 'hip': 'hip',
            'sleeve': 'arm_length',
            'inseam': 'inseam', 'thigh': 'thigh',
            'length': None,   # no direct body measure
            'foot_length': 'foot_length_cm',
        }

        areas = []
        weighted = 0
        wsum = 0

        for area in relevant:
            body_attr = profile_field.get(area)
            body_val  = getattr(profile, body_attr, 0) if body_attr else 0
            chart_attr = f'{area}_cm'
            garment_val = getattr(chart_row, chart_attr, 0)
            if not garment_val:
                continue
            # If no body value, just report garment dimension (no comparison)
            if not body_val:
                areas.append({
                    'key': area, 'label': AREA_LABELS[area]['ar'],
                    'fit': 'unknown', 'pct': None,
                    'diff_cm': None, 'garment_cm': round(garment_val, 1),
                    'body_cm': None,
                    'note': 'مقاسك غير موجود — أكمل بروفايلك',
                })
                continue
            info = self._classify_area(body_val, garment_val, area, chart_row.tolerance_cm)
            if not info:
                continue
            info['key']   = area
            info['label'] = AREA_LABELS[area]['ar']
            areas.append(info)
            w = AREA_WEIGHTS.get(area, 10)
            weighted += info['pct'] * w
            wsum     += w

        overall = int(round(weighted / wsum)) if wsum else 0
        # Fit label & color from overall
        if overall >= 85:
            fit_label, fit_color = 'مناسب تماماً', 'green'
        elif overall >= 70:
            fit_label, fit_color = 'مناسب', 'yellow'
        elif overall >= 50:
            fit_label, fit_color = 'مقبول', 'orange'
        else:
            fit_label, fit_color = 'غير مناسب', 'red'

        return {
            'size':         chart_row.size_label,
            'overall_pct':  overall,
            'fit_label':    fit_label,
            'fit_color':    fit_color,
            'areas':        areas,
            'recommended':  False,
        }

    def _analyze_with_chart(self, profile, product, category):
        """Loop product.size.chart rows. Returns sorted list + recommended index."""
        rows = product.size_chart_ids.sorted('sequence')
        if not rows:
            return None
        results = [self._analyze_chart_size(profile, r, category) for r in rows]
        results.sort(key=lambda x: x['overall_pct'], reverse=True)
        if results:
            results[0]['recommended'] = True
        return results

    def _chart_to_legacy(self, chart_results):
        """Adapt per-area chart results to the legacy shape the /fit/analyze &
        /fit/quick widgets expect (needs 'score', 'issues', 'details')."""
        out = []
        for r in (chart_results or []):
            issues, details = [], {}
            for a in (r.get('areas') or []):
                fit = a.get('fit')
                key = a.get('key')
                label = a.get('label') or key or ''
                if fit == 'tight':
                    issues.append(f'{label} ضيق')
                elif fit == 'loose':
                    issues.append(f'{label} واسع')
                if key:
                    details[key] = {'status': fit, 'diff': a.get('diff_cm')}
            out.append({
                'size':        r.get('size'),
                'score':       r.get('overall_pct', 0),
                'overall_pct': r.get('overall_pct', 0),
                'issues':      issues,
                'details':     details,
                'areas':       r.get('areas', []),
                'fit_label':   r.get('fit_label'),
                'fit_color':   r.get('fit_color'),
                'recommended': r.get('recommended', False),
                'estimate':    False,
            })
        return out

    def _mark_estimate(self, results):
        """Flag generic-table results as an estimate (no real product chart)."""
        for r in (results or []):
            r['estimate'] = True
            if r.get('fit_label') == 'مناسب تماماً':
                r['fit_label'] = 'مناسب (تقديري)'
        return results

    def _save_fit_check(self, profile, product, analysis, source='beena_check'):
        """Persist a fit-check snapshot to customer.fit.history."""
        if not profile or not product or not analysis:
            return False
        area_map = {a['key']: a for a in (analysis.get('areas') or [])}
        def _fit(k):  return (area_map.get(k) or {}).get('fit') or False
        def _diff(k): return (area_map.get(k) or {}).get('diff_cm') or 0.0
        vals = {
            'profile_id':        profile.id,
            'product_id':        product.id,
            'size_chosen':       analysis.get('size'),
            'overall_match_pct': analysis.get('overall_pct') or 0,
            'category':          analysis.get('category') or '',
            'source':            source,
            'chest_fit':    _fit('chest'),
            'waist_fit':    _fit('waist'),
            'hip_fit':      _fit('hip'),
            'shoulder_fit': _fit('shoulder'),
            'length_fit':   _fit('length'),
            'sleeve_fit':   _fit('sleeve'),
            'inseam_fit':   _fit('inseam'),
            'chest_diff_cm':    _diff('chest'),
            'waist_diff_cm':    _diff('waist'),
            'hip_diff_cm':      _diff('hip'),
            'shoulder_diff_cm': _diff('shoulder'),
            'length_diff_cm':   _diff('length'),
            'sleeve_diff_cm':   _diff('sleeve'),
            'inseam_diff_cm':   _diff('inseam'),
            'details_json':     json.dumps(analysis, ensure_ascii=False),
        }
        try:
            return request.env['customer.fit.history'].sudo().create(vals)
        except Exception as e:
            _logger.warning('save_fit_check failed: %s', e)
            return False

    def _last_fit_check(self, profile, product):
        """Return latest fit-check record for this customer+product or None."""
        if not profile or not product:
            return None
        return request.env['customer.fit.history'].sudo().search([
            ('profile_id', '=', profile.id),
            ('product_id', '=', product.id),
        ], order='create_date desc', limit=1) or None

    # ── Variant resolution ──────────────────────────────────────────────
    def _resolve_variant_id(self, product, chart_row):
        """Resolve the exact product.product (variant) for a chart row.

        Priority:
          1. chart_row.attribute_value_id  → match via product_template_attribute_value
          2. legacy fallback: substring match of chart_row.size_label in variant.display_name

        Returns variant id (int) or False.
        """
        if not product or not chart_row:
            return False

        # 1. Strict link via attribute value
        if chart_row.attribute_value_id:
            ptav = product.attribute_line_ids.product_template_value_ids.filtered(
                lambda v: v.product_attribute_value_id == chart_row.attribute_value_id
            )
            if ptav:
                variant = product.product_variant_ids.filtered(
                    lambda v: ptav in v.product_template_attribute_value_ids
                )
                if variant:
                    return variant[:1].id

        # 2. Fallback for legacy rows without attribute link
        size_label = (chart_row.size_label or '').strip().lower()
        if not size_label:
            return False
        for variant in product.product_variant_ids:
            display = (variant.display_name or '').lower()
            # Try exact match within parentheses or after colon first
            if (f'({size_label})' in display
                    or f': {size_label}' in display
                    or f'- {size_label}' in display
                    or display.endswith(' ' + size_label)):
                return variant.id
        # Last resort: substring (least reliable)
        for variant in product.product_variant_ids:
            if size_label in (variant.display_name or '').lower():
                return variant.id
        return False

    def _detect_category(self, product):
        """Detect product category for fit analysis."""
        name     = (product.name or '').lower()
        categ    = (product.categ_id.name or '').lower() if product.categ_id else ''
        combined = name + ' ' + categ

        mappings = {
            'shirt':    ['shirt', 'قميص', 'تيشرت', 'tshirt', 't-shirt', 'polo', 'blouse'],
            'jacket':   ['jacket', 'جاكيت', 'coat', 'معطف', 'blazer', 'hoodie', 'sweater', 'sweatshirt'],
            'pants':    ['pants', 'jeans', 'trousers', 'بنطلون', 'shorts', 'شورت', 'jogger'],
            'dress':    ['dress', 'فستان', 'abaya', 'عباية', 'gown', 'skirt', 'تنورة'],
            'shoe':     ['shoe', 'حذاء', 'sneaker', 'boot', 'sandal', 'slipper', 'كوتش'],
        }

        for cat, keywords in mappings.items():
            if any(kw in combined for kw in keywords):
                return cat

        return 'generic'

    def _get_product_sizes(self, product):
        """Extract available sizes from product attributes."""
        sizes = []
        for tmpl_attr in product.attribute_line_ids:
            attr_name = tmpl_attr.attribute_id.name.lower()
            if any(kw in attr_name for kw in ['size', 'مقاس', 'حجم']):
                sizes = [v.name for v in tmpl_attr.value_ids]
                break
        return sizes

    # ── Endpoints ─────────────────────────────────────────────────────────────

    @http.route('/fit/analyze', type='json', auth='public', methods=['POST'], csrf=False)
    def analyze_size(self, **kwargs):
        """Main endpoint: analyze size for a product."""
        pid = self._int_id(kwargs.get('product_id'))
        if not pid:
            return {'error': 'product_id required'}

        product = request.env['product.template'].sudo().browse(pid)
        if not product.exists():
            return {'error': 'Product not found'}

        # Get profile
        profile  = self._get_or_create_profile()
        profile_data = profile.to_dict() if profile else {}

        # Get product sizes
        sizes    = self._get_product_sizes(product)
        category = self._detect_category(product)
        has_chart = bool(product.size_chart_ids)

        if not sizes and not has_chart:
            return {
                'has_sizes':  False,
                'category':   category,
                'product':    {'id': product.id, 'name': product.name},
                'message':    'هذا المنتج ليس له مقاسات محددة',
            }

        if not profile_data.get('chest') and not profile_data.get('shoe_size_eu'):
            return {
                'has_sizes':   True,
                'has_profile': False,
                'sizes':       sizes,
                'category':    category,
                'message':     'أضف مقاساتك لتحليل دقيق',
            }

        # Accurate path: use the product's own size chart when it has one.
        if has_chart and profile:
            chart_results = self._analyze_with_chart(profile, product, category)
            if chart_results:
                results = self._chart_to_legacy(chart_results)
                return {
                    'has_sizes':   True,
                    'has_profile': True,
                    'source':      'chart',
                    'category':    category,
                    'product':     {'id': product.id, 'name': product.name},
                    'profile':     profile_data,
                    'results':     results,
                    'recommended': results[0]['size'] if results else None,
                }

        # Fallback: generic hardcoded tables — an estimate only.
        results = self._mark_estimate(self._analyze_fit(profile_data, sizes, category))

        return {
            'has_sizes':   True,
            'has_profile': True,
            'source':      'estimate',
            'category':    category,
            'product':     {'id': product.id, 'name': product.name},
            'profile':     profile_data,
            'results':     results,
            'recommended': results[0]['size'] if results else None,
            'note':        'تقدير تقريبي — لا يوجد جدول مقاسات لهذا المنتج',
        }

    @http.route('/fit/profile', type='json', auth='user', methods=['POST'], csrf=False)
    def get_profile(self, **kwargs):
        """Get or create customer body profile."""
        profile = self._get_or_create_profile()
        if not profile:
            return {'error': 'Login required', 'logged_in': False}
        return {'profile': profile.to_dict(), 'logged_in': True}

    @http.route('/fit/profile/save', type='json', auth='user', methods=['POST'], csrf=False)
    def save_profile(self, **kwargs):
        """Save customer measurements."""
        profile = self._get_or_create_profile()
        if not profile:
            return {'error': 'Login required'}

        fields_map = {
            'height': 'height', 'weight': 'weight', 'body_type': 'body_type',
            'gender': 'gender', 'shoulder': 'shoulder', 'chest': 'chest',
            'waist': 'waist', 'hip': 'hip', 'arm_length': 'arm_length',
            'inseam': 'inseam', 'thigh': 'thigh',
            'shoe_size_eu': 'shoe_size_eu', 'shoe_size_us': 'shoe_size_us',
            'shoe_width': 'shoe_width', 'preferred_fit': 'preferred_fit',
        }

        vals = {}
        for key, field in fields_map.items():
            if key in kwargs and kwargs[key] not in (None, ''):
                vals[field] = kwargs[key]

        if vals:
            try:
                profile.sudo().write(vals)
            except Exception:
                # skip any single value the ORM rejects (bad float/selection)
                for _f, _v in vals.items():
                    try:
                        profile.sudo().write({_f: _v})
                    except Exception:
                        pass

        return {'success': True, 'profile': profile.to_dict()}

    @http.route('/fit/feedback', type='json', auth='user', methods=['POST'], csrf=False)
    def save_feedback(self, **kwargs):
        """Save fit feedback after purchase — improves future recommendations."""
        product_id  = kwargs.get('product_id')
        size_chosen = kwargs.get('size_chosen')
        fit_result  = kwargs.get('fit_result')

        profile = self._get_or_create_profile()
        if not profile:
            return {'error': 'Login required'}

        try:
            request.env['customer.fit.history'].sudo().create({
                'profile_id':  profile.id,
                'product_id':  int(product_id) if product_id else False,
                'size_chosen': size_chosen,
                'fit_result':  fit_result,
                'notes':       kwargs.get('notes', ''),
            })
        except Exception:
            return {'success': False, 'error': 'invalid_feedback'}

        return {'success': True}

    @http.route('/fit/quick', type='json', auth='public', methods=['POST'], csrf=False)
    def quick_analyze(self, **kwargs):
        """Quick analysis with manual measurements (no saved profile needed)."""
        pid        = self._int_id(kwargs.get('product_id'))
        chest      = self._num(kwargs.get('chest'))
        waist      = self._num(kwargs.get('waist'))
        shoulder   = self._num(kwargs.get('shoulder'))
        shoe_eu    = self._num(kwargs.get('shoe_size_eu'))
        pref_fit   = kwargs.get('preferred_fit', 'regular')

        if not pid:
            return {'error': 'product_id required'}

        product = request.env['product.template'].sudo().browse(pid)
        if not product.exists():
            return {'error': 'Product not found'}

        profile_data = {
            'chest': chest, 'waist': waist, 'shoulder': shoulder,
            'shoe_size_eu': shoe_eu, 'preferred_fit': pref_fit,
        }

        sizes    = self._get_product_sizes(product)
        category = self._detect_category(product)

        # Accurate path: use the product's own size chart when it has one.
        if product.size_chart_ids:
            foot_len = SHOE_EU_TO_CM.get(int(round(shoe_eu)), 0) if shoe_eu else 0
            pseudo = SimpleNamespace(
                chest=chest, waist=waist, shoulder=shoulder, hip=0,
                arm_length=0, inseam=0, thigh=0, foot_length_cm=foot_len,
                preferred_fit=pref_fit,
            )
            chart_results = self._analyze_with_chart(pseudo, product, category)
            if chart_results:
                results = self._chart_to_legacy(chart_results)
                return {
                    'results':     results,
                    'recommended': results[0]['size'] if results else None,
                    'category':    category,
                    'source':      'chart',
                }

        # Fallback: generic hardcoded tables — an estimate only.
        results = self._mark_estimate(self._analyze_fit(profile_data, sizes, category))

        return {
            'results':     results,
            'recommended': results[0]['size'] if results else None,
            'category':    category,
            'source':      'estimate',
        }

    # ── Modal endpoints (product page button) ────────────────────────────

    @http.route('/fit/eligibility', type='json', auth='public', methods=['POST'], csrf=False)
    def eligibility(self, **kwargs):
        """Lightweight check used by the product page to decide whether to
        show the 'Check fit' button.

        Returns:
          eligible: bool  – show the button?
          reason:   str   – why not (logged_out | no_profile | no_chart | not_fashion)
          completion_pct: int (when applicable)
        """
        product_id = kwargs.get('product_id')
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'eligible': False, 'reason': 'logged_out'}

        pid = self._int_id(product_id)
        if not pid:
            return {'eligible': False, 'reason': 'no_product'}

        product = request.env['product.template'].sudo().browse(pid)
        if not product.exists():
            return {'eligible': False, 'reason': 'product_not_found'}

        if not product.is_fashion_item:
            return {'eligible': False, 'reason': 'not_fashion'}

        if not product.size_chart_ids:
            return {'eligible': False, 'reason': 'no_chart',
                    'is_fashion': True}

        partner = request.env.user.partner_id
        profile = request.env['customer.body.profile'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1)
        completion = int(profile.completion_pct or 0) if profile else 0
        if not profile or completion < 40:
            return {'eligible': False, 'reason': 'no_profile',
                    'completion_pct': completion,
                    'measurements_url': '/my/measurements'}

        return {
            'eligible':       True,
            'completion_pct': completion,
            'product_name':   product.name,
            'has_chart':      True,
        }

    @http.route('/fit/check', type='json', auth='user', methods=['POST'], csrf=False)
    def check_fit_modal(self, **kwargs):
        """Full per-area fit check for the product page modal.

        Returns the same shape as the Beena tool — the modal renders it.
        """
        product_id = kwargs.get('product_id')
        requested_size = (kwargs.get('size') or '').strip()

        pid = self._int_id(product_id)
        if not pid:
            return {'state': 'no_product'}

        product = request.env['product.template'].sudo().browse(pid)
        if not product.exists():
            return {'state': 'product_not_found'}

        partner = request.env.user.partner_id
        profile = request.env['customer.body.profile'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1)
        if not profile or (profile.completion_pct or 0) < 40:
            return {'state': 'no_profile',
                    'measurements_url': '/my/measurements'}

        if not product.size_chart_ids:
            return {'state': 'no_chart', 'product_id': product.id}

        try:
            category = self._detect_category(product)
            results  = self._analyze_with_chart(profile, product, category)
            if not results:
                return {'state': 'error'}

            chosen = None
            if requested_size:
                chosen = next((r for r in results if (r['size'] or '').lower() == requested_size.lower()), None)
            if not chosen:
                chosen = next((r for r in results if r.get('recommended')), results[0])
            chosen['category'] = category

            self._save_fit_check(profile, product, chosen, source='beena_check')

            # Resolve variant via the new attribute-aware resolver
            chart_row = product.size_chart_ids.filtered(
                lambda r: (r.size_label or '').strip().lower() == (chosen['size'] or '').strip().lower()
            )[:1]
            variant_id = self._resolve_variant_id(product, chart_row) if chart_row else False

            # ALL sizes (for in-modal size selector). Ordered by the chart's
            # natural sequence, not score, so the picker matches the product page.
            ordered_rows = product.size_chart_ids.sorted('sequence')
            by_size = {(r['size'] or '').strip().lower(): r for r in results}
            all_sizes = []
            for row in ordered_rows:
                key = (row.size_label or '').strip().lower()
                r = by_size.get(key)
                if not r:
                    continue
                all_sizes.append({
                    'size':        r['size'],
                    'overall_pct': r['overall_pct'],
                    'fit_label':   r['fit_label'],
                    'fit_color':   r['fit_color'],
                    'recommended': r.get('recommended', False),
                })
            # Alts kept for backward compatibility (cards that still use it)
            alts = [s for s in all_sizes if s['size'] != chosen['size']][:3]

            return {
                'state':             'ready',
                'product_id':        product.id,
                'product_name':      product.name,
                'product_image_url': '/web/image/product.template/%s/image_512' % product.id,
                'product_price_kd':  float(product.list_price or 0.0),
                'category':          category,
                'size':              chosen['size'],
                'overall_pct':       chosen['overall_pct'],
                'fit_label':         chosen['fit_label'],
                'fit_color':         chosen['fit_color'],
                'areas':             chosen['areas'],
                'all_sizes':         all_sizes,
                'alternates':        alts,
                'variant_id':        variant_id,
                'preferred_unit':    profile.preferred_unit or 'cm',
            }
        except Exception as e:
            _logger.warning('check_fit modal failed: %s', e)
            return {'state': 'error'}
