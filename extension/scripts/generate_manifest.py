"""Regenerate manifest.json from src/supported_domains.js (Chrome + Firefox MV3).

By default this writes a minimal, store-ready manifest whose only host
permission is the OpenScout API origin. Retailer sites do NOT need host
permissions — the content script gets DOM access via content_scripts.matches —
so listing them would only invite an in-depth AMO/Chrome review.

Pass --dev to additionally include the localhost backend and broad AWS
wildcards for local development.
"""
import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--dev",
    action="store_true",
    help="Include localhost + broad AWS wildcards (local development only).",
)
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[1]
code = (ROOT / "src" / "supported_domains.js").read_text(encoding="utf-8")
config_text = (ROOT / "src" / "config.js").read_text(encoding="utf-8")
domains = sorted(set(re.findall(r'"([a-z0-9][a-z0-9.-]*\.[a-z]{2,})"', code)))

# Retailer sites are scoped via content_scripts.matches, NOT host_permissions.
retail_matches: list[str] = []
for domain in domains:
    retail_matches.append(f"*://*.{domain}/*")
    retail_matches.append(f"*://{domain}/*")

# host_permissions is reserved for origins we actually fetch() against. In
# production that's just the OpenScout API endpoint.
host_permissions: list[str] = []

api_base_match = re.search(
    r'^\s*const OPENSCOUT_API_BASE\s*=\s*"(https?://[^"]+)"',
    config_text,
    re.MULTILINE,
)
if api_base_match:
    api_base = api_base_match.group(1).rstrip("/")
    host_permissions.append(f"{api_base}/*")

if args.dev:
    for dev_pattern in (
        "http://127.0.0.1:8000/*",
        "https://*.execute-api.*.amazonaws.com/*",
        "https://*.lambda-url.*.on.aws/*",
    ):
        if dev_pattern not in host_permissions:
            host_permissions.append(dev_pattern)

manifest = {
    "manifest_version": 3,
    "name": "OpenScout",
    "version": "1.1",
    "description": "A Open Source extension that helps users find the best deals while shopping",
    "icons": {
        "16": "icons/icon16.png",
        "48": "icons/icon48.png",
        "128": "icons/icon128.png",
    },
    "action": {
        "default_icon": {
            "16": "icons/icon16.png",
            "48": "icons/icon48.png",
            "128": "icons/icon128.png",
        }
    },
    "permissions": ["storage"],
    "host_permissions": host_permissions,
    "content_scripts": [
        {
            "matches": retail_matches,
            "js": [
                "src/browser.js",
                "src/config.js",
                "src/api.js",
                "src/supported_domains.js",
                "src/detector.js",
                "src/scraper.js",
                "src/ui.js",
                "content.js",
            ],
            "run_at": "document_idle",
        }
    ],
    "background": {"service_worker": "background.js"},
    "browser_specific_settings": {
        "gecko": {
            "id": "openscout@openscout.app",
            "strict_min_version": "109.0",
        }
    },
}

(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(
    f"Wrote manifest.json — {len(domains)} domains, "
    f"{len(retail_matches)} content-script matches, "
    f"{len(host_permissions)} host permission(s)"
    + (" [dev]" if args.dev else "")
)
