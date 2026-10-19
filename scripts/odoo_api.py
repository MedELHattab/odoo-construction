"""Minimal Odoo JSON-2 client (stdlib only).

Config comes from environment variables:
  ODOO_API_KEY  (required)
  ODOO_URL      (default http://localhost:8069)
  ODOO_DB       (default construction)

Usage:
  python scripts/odoo_api.py <model> <method> '<json body>'
  python scripts/odoo_api.py res.partner search_read '{"fields":["name"],"limit":5}'
"""
import json
import os
import sys
import urllib.error
import urllib.request


def call(model, method, body=None):
    key = os.environ.get("ODOO_API_KEY")
    if not key:
        sys.exit("ODOO_API_KEY is not set")
    url = f"{os.environ.get('ODOO_URL', 'http://localhost:8069')}/json/2/{model}/{method}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body or {}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"bearer {key}",
            "X-Odoo-Database": os.environ.get("ODOO_DB", "construction"),
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    payload = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    print(json.dumps(call(sys.argv[1], sys.argv[2], payload), indent=2))
