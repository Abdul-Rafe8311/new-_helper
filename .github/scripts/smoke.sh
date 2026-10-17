#!/usr/bin/env bash
# Post-deploy smoke test. Usage: smoke.sh <web-url> <api-url> <expected-git-sha>
# Checks the web root, the API /health (and the deployed commit), and "Try the demo"
# through the web domain, which also proves the /api rewrite and the cookie work.
set -euo pipefail

WEB_URL="${1:?web url}"
API_URL="${2:?api url}"
SHA="${3:?git sha}"
WEB_URL="${WEB_URL%/}"
API_URL="${API_URL%/}"

fail() {
  echo "::error::smoke test failed: $*"
  exit 1
}

echo "web / ..."
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 30 "$WEB_URL/") || fail "web / unreachable"
[ "$code" = "200" ] || fail "web / returned $code"

echo "api /health ..."
health=$(curl -fsS --max-time 30 "$API_URL/health") || fail "api /health unreachable"
echo "$health" | jq -e --arg sha "$SHA" '.status == "ok" and .git_sha == $sha' >/dev/null ||
  fail "api /health did not report ok at $SHA: $health"

echo "POST /api/auth/demo through the web domain ..."
jar=$(mktemp)
trap 'rm -f "$jar"' EXIT
body=$(curl -sS --max-time 30 -c "$jar" -w '\n%{http_code}' -X POST "$WEB_URL/api/auth/demo") ||
  fail "demo request unreachable"
code=$(tail -n1 <<<"$body")
payload=$(sed '$d' <<<"$body")
[ "$code" = "200" ] || fail "POST /api/auth/demo returned $code: $payload"
echo "$payload" | jq -e '.email | type == "string"' >/dev/null || fail "demo response has no email"
grep -q "dp_session" "$jar" || fail "demo response set no session cookie"

echo "GET /api/auth/me with the demo cookie ..."
curl -fsS --max-time 30 -b "$jar" "$WEB_URL/api/auth/me" | jq -e '.email' >/dev/null ||
  fail "session cookie was not accepted by /auth/me"

echo "smoke test passed"
