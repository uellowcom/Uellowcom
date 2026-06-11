"""Shared safety helpers for the Smart Connector (SSRF guard + AI input
sanitisation). Kept dependency-free so both the import engine and the price
intelligence model can import them without a circular reference."""
import ipaddress
import re
import socket
from urllib.parse import urlparse


def is_safe_public_url(url):
    """Reject anything that isn't a plain public http(s) URL — blocks SSRF
    against internal hosts (localhost / link-local / private ranges / cloud
    metadata 169.254.169.254). Returns (ok: bool, reason: str)."""
    if not url or not isinstance(url, str):
        return False, 'empty url'
    try:
        p = urlparse(url.strip())
    except Exception:
        return False, 'unparseable url'
    if p.scheme not in ('http', 'https'):
        return False, 'only http/https allowed'
    host = p.hostname or ''
    if not host:
        return False, 'no host'
    # block obvious internal names
    low = host.lower()
    if low in ('localhost',) or low.endswith('.local') or low.endswith('.internal'):
        return False, 'internal host blocked'
    # resolve and reject private / loopback / link-local / reserved IPs
    try:
        infos = socket.getaddrinfo(host, None)
        for fam, _t, _p, _c, sockaddr in infos:
            ip = ipaddress.ip_address(sockaddr[0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return False, 'private/internal IP blocked'
    except (socket.gaierror, ValueError):
        # DNS failure → let the HTTP layer fail cleanly with a real error
        return True, ''
    return True, ''


# Control chars + the most common prompt-injection trigger phrases.
_INJECT_PATTERNS = re.compile(
    r'(ignore\s+(all\s+)?previous|disregard\s+(all\s+)?previous|'
    r'system\s+prompt|you\s+are\s+now|act\s+as|'
    r'تجاهل\s+(كل\s+)?التعليمات|تصرف\s+ك)',
    re.IGNORECASE)


def resolve_ai_config(env):
    """Return (api_key, model) for Smart Connector AI calls.

    Single source of truth: the Smart Connector's own key/model are used when
    set, otherwise we fall back to the Beena AI engine's PROVEN-WORKING config
    (uellow_ai.*) so a blank or stale Smart-Connector key doesn't silently
    break translation/enrichment. The model likewise falls back to Beena's
    configured model (e.g. claude-sonnet-4-6) instead of a hard-coded id that
    may 404 for this account.
    """
    ICP = env['ir.config_parameter'].sudo()
    sc_key = (ICP.get_param('uellow.sc.anthropic_key') or '').strip()
    beena_key = (ICP.get_param('uellow_ai.claude_api_key') or '').strip()
    key = sc_key or beena_key
    model = ((ICP.get_param('uellow.sc.ai_model') or '').strip()
             or (ICP.get_param('uellow_ai.claude_model') or '').strip()
             or 'claude-sonnet-4-6')
    return key, model


def sanitize_ai_text(s, max_len=600):
    """Make a product field safe to embed inside an AI prompt: strip control
    characters, collapse whitespace, neutralise injection trigger phrases,
    and cap the length."""
    if not s:
        return ''
    s = str(s)
    # drop control chars (keep normal whitespace)
    s = ''.join(ch for ch in s if ch == ' ' or ch == '\t' or (ord(ch) >= 32 and ch not in '\r\n') or ch == '\n')
    s = re.sub(r'[\r\n]+', ' ', s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    s = _INJECT_PATTERNS.sub('[filtered]', s)
    return s[:max_len]
