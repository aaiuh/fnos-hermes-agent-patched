#!/usr/bin/env python3
"""Inject PWA assets into the prepared app/hermes-src AFTER prepare-runtime
published it, then rewrite the .fnos-runtime.json receipt so every later
check (build-fpk verify_runtime / verify_frontend) stays consistent.

Runs at CI between prepare-runtime.py and the runtime tar step. This is the
fork's own packaging step; upstream integrity evidence for the official
build (hermes-build.json inside dist-webapp) is left untouched.
"""
import hashlib
import json
import sys
from pathlib import Path

RECEIPT = ".fnos-runtime.json"
DIST = Path("apps/desktop/dist-webapp")
PWA = ("manifest.webmanifest", "icon-192.png", "icon-512.png")
MANIFEST_LINK = '<link rel="manifest" href="./manifest.webmanifest" />'


def sha(p: Path) -> str:
    return hashlib.file_digest(p.open("rb"), "sha256").hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: apply-pwa-final.py <patches/pwa dir> <app/hermes-src>", file=sys.stderr)
        return 2
    pwa_dir = Path(sys.argv[1]).resolve()
    root = Path(sys.argv[2]).resolve()
    dist = root / DIST

    if not (dist / "index.html").is_file() or not (root / RECEIPT).is_file():
        print("apply-pwa-final: prepared hermes-src not found", file=sys.stderr)
        return 1
    if any(not (pwa_dir / name).is_file() for name in PWA):
        print("apply-pwa-final: PWA assets missing", file=sys.stderr)
        return 1

    receipt_path = root / RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    # 1) copy assets into dist-webapp
    for name in PWA:
        (dist / name).write_bytes((pwa_dir / name).read_bytes())

    # 2) inject the manifest link if absent
    index = dist / "index.html"
    text = index.read_text(encoding="utf-8")
    if "rel=\"manifest\"" not in text:
        anchor = '<meta name="theme-color"'
        i = text.find(anchor)
        if i == -1:
            print("apply-pwa-final: theme-color anchor not found", file=sys.stderr)
            return 1
        end = text.find(">", i)
        text = text[: end + 1] + "\n      " + MANIFEST_LINK + text[end + 1:]
        index.write_text(text, encoding="utf-8")

    # 3) rewrite the receipt inventories to include the injected files
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
    actual = {}
    for current, dirs, files in __import__("os").walk(root):
        for name in sorted(files):
            p = Path(current) / name
            actual[p.relative_to(root).as_posix()] = sha(p)
    actual.pop(RECEIPT, None)
    if actual != receipt["files"]:
        missing = set(receipt["files"]) - set(actual)
        extra = set(actual) - set(receipt["files"])
        changed = {k for k in set(actual) & set(receipt["files"]) if actual[k] != receipt["files"][k]}
        print(f"apply-pwa-final: receipt self-check failed missing={sorted(missing)[:5]} "
              f"extra={sorted(extra)[:5]} changed={sorted(changed)[:5]}", file=sys.stderr)
        return 1
    print(f"apply-pwa-final: injected PWA into {root} ({DIST}); receipt rewritten and self-checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
