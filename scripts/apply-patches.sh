#!/bin/bash
# Apply the reverse-proxy / panel-launch / PWA patches onto the freshly cloned
# official hermes-agent source tree (upstream SRC) before it is packaged.
# Called by scripts/ci-runtime.sh after the tag/commit verification steps.
set -euo pipefail

SRC="${1:?Usage: apply-patches.sh <upstream-source-root>}"
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
PATCHES="$ROOT/patches/core"
PWA="$ROOT/patches/pwa"

# 1) Core patches: gate whitelist (PWA metadata served without sign-in) and
#    static asset registry. Paths are relative to hermes_cli/.
for patch in "$PATCHES"/*.patch; do
    [[ -e "$patch" ]] || { printf '%s\n' "No core patches found in $PATCHES" >&2; exit 1; }
    # The patches apply cleanly only on the exact upstream blob we built them
    # against; on drift git apply fails and stops the build.
    (cd -- "$SRC/hermes_cli" && git apply "$patch")
    printf 'Applied %s\n' "$(basename -- "$patch")"
done

# 2) PWA assets + manifest link. Icons are copied as-is; the manifest link is
#    injected into dist-webapp/index.html if absent.
DEST="$SRC/apps/desktop/dist-webapp"
[[ -d "$DEST" ]] || { printf '%s\n' "dist-webapp missing: $DEST" >&2; exit 1; }
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

printf 'Patches applied to %s\n' "$SRC"
