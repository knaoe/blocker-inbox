#!/usr/bin/env bash
# Wrap inbox.html (written in claude.ai Artifact "body" format, without
# <!doctype>/<html>/<head>/<body>) in a standalone document, so it can be
# opened from disk or served by any static host. Outside claude.ai the page
# has no shared store and runs in demo mode with the built-in example items.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
out_dir="${1:-$root/preview}"
mkdir -p "$out_dir"
out="$out_dir/index.html"

{
  printf '%s' '<!doctype html><html><head><meta charset="utf-8">'
  printf '%s' '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
  printf '%s' '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>'
  printf '%s\n' '</head><body>'
  cat "$root/inbox.html"
  printf '\n%s\n' '</body></html>'
} > "$out"

echo "$out"
