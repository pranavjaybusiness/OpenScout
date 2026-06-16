"""Regenerate manifest.json from src/supported_domains.js (Chrome + Firefox MV3)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
code = (ROOT / "src" / "supported_domains.js").read_text(encoding="utf-8")
config_text = (ROOT / "src" / "config.js").read_text(encoding="utf-8")
domains = sorted(set(re.findall(r'"([a-z0-9][a-z0-9.-]*\.[a-z]{2,})"', code)))

patterns: list[str] = []
for domain in domains:
    patterns.append(f"*://*.{domain}/*")
    patterns.append(f"*://{domain}/*")

api_base_match = re.search(
    r'^const OPENSCOUT_API_BASE\s*=\s*"(https?://[^"]+)"',
    config_text,
    re.MULTILINE,
)
if api_base_match:
    api_base = api_base_match.group(1).rstrip("/")
    patterns.append(f"{api_base}/*")
else:
    patterns.append("http://127.0.0.1:8000/*")
    patterns.append("https://*.execute-api.*.amazonaws.com/*")

retail_matches = [
    p
    for p in patterns
    if "127.0.0.1" not in p
    and "lambda-url" not in p
    and "execute-api" not in p
]

manifest = {
    "manifest_version": 3,
    "name": "OpenScout",
    "version": "1.4",
    "description": "Automated product parser and price comparator.",
    "permissions": ["storage"],
    "host_permissions": patterns,
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
print(f"Wrote manifest.json — {len(domains)} domains, {len(retail_matches)} match patterns")
