import json
import logging

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


class SmartFitController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            f'uellow_fit.{key}', default
        )

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

        # Add fit labels
        for r in results:
            s = r['score']
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
        product_id = kwargs.get('product_id')
        if not product_id:
            return {'error': 'product_id required'}

        product = request.env['product.template'].sudo().browse(int(product_id))
        if not product.exists():
            return {'error': 'Product not found'}

        # Get profile
        profile  = self._get_or_create_profile()
        profile_data = profile.to_dict() if profile else {}

        # Get product sizes
        sizes    = self._get_product_sizes(product)
        category = self._detect_category(product)

        if not sizes:
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

        # Run analysis
        results = self._analyze_fit(profile_data, sizes, category)

        return {
            'has_sizes':   True,
            'has_profile': True,
            'category':    category,
            'product':     {'id': product.id, 'name': product.name},
            'profile':     profile_data,
            'results':     results,
            'recommended': results[0]['size'] if results else None,
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
            if key in kwargs and kwargs[key] is not None:
                vals[field] = kwargs[key]

        if vals:
            profile.sudo().write(vals)

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

        request.env['customer.fit.history'].sudo().create({
            'profile_id':  profile.id,
            'product_id':  int(product_id) if product_id else False,
            'size_chosen': size_chosen,
            'fit_result':  fit_result,
            'notes':       kwargs.get('notes', ''),
        })

        return {'success': True}

    @http.route('/fit/quick', type='json', auth='public', methods=['POST'], csrf=False)
    def quick_analyze(self, **kwargs):
        """Quick analysis with manual measurements (no saved profile needed)."""
        product_id = kwargs.get('product_id')
        chest      = float(kwargs.get('chest', 0))
        waist      = float(kwargs.get('waist', 0))
        shoulder   = float(kwargs.get('shoulder', 0))
        shoe_eu    = float(kwargs.get('shoe_size_eu', 0))
        pref_fit   = kwargs.get('preferred_fit', 'regular')

        if not product_id:
            return {'error': 'product_id required'}

        product = request.env['product.template'].sudo().browse(int(product_id))
        if not product.exists():
            return {'error': 'Product not found'}

        profile_data = {
            'chest': chest, 'waist': waist, 'shoulder': shoulder,
            'shoe_size_eu': shoe_eu, 'preferred_fit': pref_fit,
        }

        sizes    = self._get_product_sizes(product)
        category = self._detect_category(product)
        results  = self._analyze_fit(profile_data, sizes, category)

        return {
            'results':     results,
            'recommended': results[0]['size'] if results else None,
            'category':    category,
        }
