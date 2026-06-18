#!/usr/bin/env python3
"""Find accurate product images for the 65 failed products using the Claude API's
server-side web_search tool (runs on Anthropic infra — not IP-blocked like this VM).

Run INSIDE the container (it has the anthropic SDK + reaches api.anthropic.com):
    docker exec -i odoo-docker-web-1 odoo shell -d odoo --no-http --log-level=warn \
        < /mnt/uellowcom/dimg/claude_image_finder.py

It writes /mnt/uellowcom/dimg/found_images.json  ({pid: [url, ...]}).
Then run the HOST downloader (claude_image_apply.sh) to fetch + apply.

Why split: Claude's web_search runs server-side and returns real retailer/manufacturer
image URLs; the actual image bytes are then downloaded from the HOST, whose egress
reaches Amazon/Shopify/manufacturer CDNs (the container + this VM are blocked from the
open image-search engines, which is why the Drive-scrape left 65 gaps).
"""
import json, re, anthropic

MODEL = "claude-opus-4-8"            # skill default; switch to claude-sonnet-4-6 to cut cost
ICP = env['ir.config_parameter'].sudo()
client = anthropic.Anthropic(api_key=ICP.get_param('uellow_ai.claude_api_key'))

pids_names = []
for line in open('/mnt/uellowcom/dimg/fail_named.txt'):
    line = line.strip()
    if '|' in line:
        pid, name = line.split('|', 1)
        pids_names.append((int(pid), name))

SYS = ("You are a product-image sourcing assistant for an e-commerce catalog. "
       "Given a product name (brand + model), use web_search to find the OFFICIAL or "
       "reputable-retailer product photo: the actual PRODUCT on a clean/white background, "
       "high resolution, NOT a promotional flyer or lifestyle scene. Return direct image "
       "file URLs ending in .jpg/.jpeg/.png/.webp when you can see them in results. "
       "Prefer the manufacturer site, Amazon, or a major retailer CDN.")

def find_for(name):
    """One product → list of candidate direct image URLs."""
    msgs = [{"role": "user", "content":
             "Product: %r\n\nSearch the web, then reply with ONLY a JSON array of 1-3 "
             "direct image URLs (best first), e.g. [\"https://...jpg\"]. No prose." % name}]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
    for _ in range(6):                      # manual loop for server-tool pause_turn
        r = client.messages.create(model=MODEL, max_tokens=1024, system=SYS,
                                   tools=tools, messages=msgs)
        if r.stop_reason == "pause_turn":
            msgs = [msgs[0], {"role": "assistant", "content": r.content}]
            continue
        break
    txt = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    m = re.search(r'\[.*?\]', txt, re.S)
    urls = []
    if m:
        try:
            urls = [u for u in json.loads(m.group(0)) if isinstance(u, str) and u.startswith("http")]
        except Exception:
            pass
    if not urls:                            # fallback: scrape any image URL from the text
        urls = re.findall(r'https?://[^\s"\']+?\.(?:jpg|jpeg|png|webp)', txt, re.I)
    return urls[:3]

out = {}
for i, (pid, name) in enumerate(pids_names, 1):
    try:
        urls = find_for(name)
    except Exception as e:
        print("ERR pid %d: %s" % (pid, str(e)[:120])); urls = []
    if urls:
        out[str(pid)] = urls
    print("[%d/%d] pid=%d  %d urls  %s" % (i, len(pids_names), pid, len(urls), name[:45]), flush=True)

json.dump(out, open('/mnt/uellowcom/dimg/found_images.json', 'w'))
print("DONE: %d/%d products got image URLs -> found_images.json" % (len(out), len(pids_names)))
