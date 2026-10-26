#!/usr/bin/env bash
# Upgrade every construction_* addon and run all their tests in one go.
# Usage: bash scripts/test_all.sh        (needs the stack running: docker compose up -d)
set -uo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1  # stop Git Bash on Windows rewriting container paths

modules=$(ls -d addons/construction_*/ | xargs -n1 basename | paste -sd, -)
tags=$(echo "$modules" | sed 's/\([a-z_0-9]*\)/\/\1/g')
log=$(mktemp)

docker compose exec -T odoo sh -c "odoo -d construction --db_host \"\$HOST\" --db_user \"\$USER\" \
  --db_password \"\$PASSWORD\" -u $modules --test-tags $tags --stop-after-init --http-port=8070" > "$log" 2>&1
status=$?

summary=$(grep -E "odoo.tests.result: .* tests when loading" "$log" | tail -1 | sed 's/.*result: //')
echo "modules: $(echo "$modules" | tr ',' '\n' | wc -l)"
echo "result : ${summary:-no test summary found (see $log)}"
grep -E "ERROR|CRITICAL|FAIL" "$log" | cut -c1-220 | head -15

# Tests consume site codes; start the next real site right after the last one that exists.
if command -v python >/dev/null && [ -n "${ODOO_API_KEY:-}" ]; then
  last=$(python -I scripts/odoo_api.py construction.site search_read \
    '{"domain":[["active","in",[true,false]]],"fields":["code"],"order":"code desc","limit":1}' 2>/dev/null \
    | python -I -c "import json,sys; d=json.load(sys.stdin); print(int(d[0]['code'].split('/')[1]) if d else 0)" 2>/dev/null || echo 0)
  seq=$(python -I scripts/odoo_api.py ir.sequence search_read \
    '{"domain":[["code","=","construction.site"]],"fields":["id"]}' 2>/dev/null \
    | python -I -c "import json,sys; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null || echo "")
  if [ -n "$seq" ]; then
    python -I scripts/odoo_api.py ir.sequence write "{\"ids\":[$seq],\"vals\":{\"number_next\":$((last + 1))}}" >/dev/null 2>&1 \
      && echo "site counter reset: next site is SITE/$(printf '%04d' $((last + 1)))"
  fi
fi

[ "$status" -eq 0 ] && ! grep -qE "[1-9][0-9]* failed|[1-9][0-9]* error\(s\)" "$log"
