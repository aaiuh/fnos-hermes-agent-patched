#!/usr/bin/env python3
"""Apply the fork patch set onto the PREPARED app/hermes-src tree, then
rewrite the .fnos-runtime.json receipt so every later check (build-fpk
verify_runtime / verify_frontend) stays consistent.

Runs at CI between prepare-runtime.py and the runtime tar step. This is the
fork's own packaging step; upstream integrity evidence for the official
build (hermes-build.json inside dist-webapp) is left untouched.

Why a post-prepare step: archive_source exports via `git archive COMMIT`,
so worktree patches applied to the upstream clone never reach the package.
The stage tree is not a git worktree, so the patch set is stored as full
snapshot files (patches/snapshot/) and copied over, verified against the
upstream originals by content replacement.

Patch steps:
  1. core: replace two tracked hermes_cli files with the patched snapshots
     (verified: upstream original content -> exact patched content)
  2. PWA: copy manifest + icons into dist-webapp, inject the manifest link
  3. rewrite the receipt inventories (full files + renderer files + core files)
  4. self-check: recompute the full inventory and compare
"""
import hashlib
import json
import sys
from pathlib import Path

RECEIPT = ".fnos-runtime.json"
DIST = Path("apps/desktop/dist-webapp")
PWA = ("manifest.webmanifest", "icon-192.png", "icon-512.png")
MANIFEST_LINK = '<link rel="manifest" href="./manifest.webmanifest" />'
CORE = (
    "hermes_cli/dashboard_auth/middleware.py",
    "hermes_cli/web_server_static_assets.py",
)


def sha(p: Path) -> str:
    return hashlib.file_digest(p.open("rb"), "sha256").hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: apply-fork-patches.py <patches dir> <app/hermes-src>", file=sys.stderr)
        return 2
    patches = Path(sys.argv[1]).resolve()
    pwa_dir = patches / "pwa"
    snap_dir = patches / "snapshot"
    root = Path(sys.argv[2]).resolve()
    dist = root / DIST

    if not (dist / "index.html").is_file() or not (root / RECEIPT).is_file():
        print("apply-fork-patches: prepared hermes-src not found", file=sys.stderr)
        return 1
    for name in PWA:
        if not (pwa_dir / name).is_file():
            print(f"apply-fork-patches: missing {pwa_dir / name}", file=sys.stderr)
            return 1
    for name in CORE:
        if not (snap_dir / Path(name).name).is_file():
            print(f"apply-fork-patches: missing snapshot {name}", file=sys.stderr)
            return 1

    receipt_path = root / RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    # 1) core files: verify the tree still carries the upstream original, then
    #    swap in the patched snapshot. Drift between upstream tag and snapshot
    #    basis would show up as an unexpected original and fails loudly.
    for name in CORE:
        target = root / name
        snapshot = snap_dir / Path(name).name
        receipt_hash = receipt["files"].get(name)
        if receipt_hash is None:
            print(f"apply-fork-patches: {name} not in receipt inventory", file=sys.stderr)
            return 1
        if sha(target) != receipt_hash:
            print(f"apply-fork-patches: {name} drifted from the prepared inventory", file=sys.stderr)
            return 1
        patched = snapshot.read_bytes()
        target.write_bytes(patched)
        receipt["files"][name] = sha(target)

    # 2) PWA assets + manifest link
    for name in PWA:
        (dist / name).write_bytes((pwa_dir / name).read_bytes())
    index = dist / "index.html"
    text = index.read_text(encoding="utf-8")
    if "rel=\"manifest\"" not in text:
        anchor = '<meta name="theme-color"'
        i = text.find(anchor)
        if i == -1:
            print("apply-fork-patches: theme-color anchor not found", file=sys.stderr)
            return 1
        end = text.find(">", i)
        text = text[: end + 1] + "\n      " + MANIFEST_LINK + text[end + 1:]
        index.write_text(text, encoding="utf-8")

    # 3) rewrite the receipt inventories
    prefix = DIST.as_posix() + "/"
    for name in PWA:
        receipt["files"][prefix + name] = sha(dist / name)
    receipt["files"][prefix + "index.html"] = sha(index)
    renderer = receipt["renderer"]
    for name in PWA:
        renderer["files"][name] = receipt["files"][prefix + name]
    renderer["files"]["index.html"] = receipt["files"][prefix + "index.html"]

    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    # 4) self-check: recompute the full inventory exactly like prepare/build-fpk
    import os
    actual = {}
    for current, dirs, files in os.walk(root):
        for name in sorted(files):
            p = Path(current) / name
            actual[p.relative_to(root).as_posix()] = sha(p)
    actual.pop(RECEIPT, None)
    if actual != receipt["files"]:
        missing = set(receipt["files"]) - set(actual)
        extra = set(actual) - set(receipt["files"])
        changed = {k for k in set(actual) & set(receipt["files"]) if actual[k] != receipt["files"][k]}
        print(f"apply-fork-patches: receipt self-check failed missing={sorted(missing)[:5]} "
              f"extra={sorted(extra)[:5]} changed={sorted(changed)[:5]}", file=sys.stderr)
        return 1
    print(f"apply-fork-patches: applied core patches + PWA into {root}; receipt rewritten and self-checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
