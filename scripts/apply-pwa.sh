#!/bin/bash
# Inject PWA assets (manifest + icons) into the freshly built webapp bundle.
# Called by scripts/ci-runtime.sh AFTER apps/desktop/scripts/build-webapp.mjs:
# dist-webapp is a build artifact and does not exist at clone time.
set -euo pipefail

SRC="${1:?Usage: apply-pwa.sh <upstream-source-root>}"
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
PWA="$ROOT/patches/pwa"

DEST="$SRC/apps/desktop/dist-webapp"
[[ -f "$DEST/index.html" ]] || { printf '%s\n' "dist-webapp/index.html missing: $DEST" >&2; exit 1; }
cp -- "$PWA/manifest.webmanifest" "$PWA/icon-192.png" "$PWA/icon-512.png" "$DEST/"
if ! grep -q 'rel="manifest"' "$DEST/index.html"; then
    python3 - "$DEST/index.html" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
anchor = '<meta name="theme-color"'
idx = text.find(anchor)
if idx == -1:
    raise SystemExit("theme-color meta tag not found; cannot inject manifest link")
end = text.find(">", idx)
if end == -1:
    raise SystemExit("malformed theme-color tag")
insert = '\n      <link rel="manifest" href="./manifest.webmanifest" />'
path.write_text(text[: end + 1] + insert + text[end + 1 :], encoding="utf-8")
PY
    printf 'Injected manifest link into %s\n' "$DEST/index.html"
fi
printf 'PWA assets ready in %s\n' "$DEST"
