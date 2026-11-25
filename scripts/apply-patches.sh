#!/bin/bash
# Apply the gated-whitelist core patches onto the freshly cloned official
# hermes-agent source tree (upstream SRC) before it is packaged.
# Called by scripts/ci-runtime.sh right after the tag/commit verification.
# PWA assets are injected separately by scripts/apply-pwa.sh AFTER the
# webapp build (dist-webapp is a build artifact, absent at clone time).
set -euo pipefail

SRC="${1:?Usage: apply-patches.sh <upstream-source-root>}"
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
PATCHES="$ROOT/patches/core"

for patch in "$PATCHES"/*.patch; do
    [[ -e "$patch" ]] || { printf '%s\n' "No core patches found in $PATCHES" >&2; exit 1; }
    # The patches apply cleanly only on the exact upstream blob we built them
    # against; on drift git apply fails and stops the build.
    (cd -- "$SRC/hermes_cli" && git apply "$patch")
    printf 'Applied %s\n' "$(basename -- "$patch")"
done

printf 'Core patches applied to %s\n' "$SRC"
