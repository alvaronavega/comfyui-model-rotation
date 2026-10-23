"""
CLI tool to resolve (decrypt) an obfuscated sidecar.

The secure mode of SaveImageWithCheckpoint stores the generation data as
SHA-256 hashes.  This tool turns those hashes back into readable values using
the private manifest file (and, as a fallback, brute force against a list of
known model names).

Usage
-----

Resolve a sidecar using the manifest::

    python tools/resolve_sidecar.py SIDEcar.json MANIFEST.json

Resolve a folder of sidecars::

    python tools/resolve_sidecar.py --folder PASTA_IMAGENS MANIFEST.json

Brute force a single hash against a list of candidate values::

    python tools/resolve_sidecar.py --brute HASH models.txt

Without arguments the tool prints the current salt fingerprint so you can
confirm which project produced the sidecars.
"""

import argparse
import json
import os
import sys

# Make the package importable when run from a source checkout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.secure_hash import (  # noqa: E402
    brute_force_known,
    hash_value,
    load_manifest,
    resolve_file,
    resolve_sidecar,
)


def _print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_single(args):
    manifest = load_manifest(args.manifest)
    resolved = resolve_file(args.sidecar, args.manifest)
    _print_json(resolved)

    unresolved = [
        key for key, value in resolved.items()
        if isinstance(value, str) and value not in manifest.values()
        and value in _raw_values(args.sidecar)
    ]
    if unresolved:
        print(f"\n[warning] could not resolve: {', '.join(unresolved)}", file=sys.stderr)


def _raw_values(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {v for v in data.values() if isinstance(v, str)}
    except Exception:
        return set()


def cmd_folder(args):
    manifest = load_manifest(args.manifest)
    folder = args.folder
    count = 0
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".json"):
            continue
        path = os.path.join(folder, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        resolved = resolve_sidecar(data, manifest)
        out_path = path[:-5] + ".resolved.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(resolved, fh, ensure_ascii=False, indent=2)
        print(f"resolved -> {out_path}")
        count += 1
    print(f"\n{count} sidecar(s) resolved.")


def cmd_brute(args):
    with open(args.candidates, "r", encoding="utf-8") as fh:
        candidates = [line.strip() for line in fh if line.strip()]
    found = brute_force_known(args.hash, candidates)
    if found:
        print(f"FOUND: {found}")
    else:
        print("not found in the candidate list")


def cmd_info(args):
    salt = __import__("utils.secure_hash", fromlist=["get_salt"]).get_salt()
    fingerprint = hash_value("__fingerprint__", salt, length=16)
    print(f"salt fingerprint: {fingerprint}")
    print(f"salt length:       {len(salt)} chars")
    print("salt file:         utils/secure_config.json")
    print("\nKeep this file safe: without it the hashes cannot be reproduced.")


def main():
    parser = argparse.ArgumentParser(
        description="Resolve obfuscated sidecars produced by the secure mode."
    )
    sub = parser.add_subparsers(dest="command")

    p_single = sub.add_parser("single", help="resolve one .json sidecar")
    p_single.add_argument("sidecar")
    p_single.add_argument("manifest")
    p_single.set_defaults(func=cmd_single)

    p_folder = sub.add_parser("folder", help="resolve every .json sidecar in a folder")
    p_folder.add_argument("folder")
    p_folder.add_argument("manifest")
    p_folder.set_defaults(func=cmd_folder)

    p_brute = sub.add_parser("brute", help="match one hash against a list of candidates")
    p_brute.add_argument("hash")
    p_brute.add_argument("candidates")
    p_brute.set_defaults(func=cmd_brute)

    p_info = sub.add_parser("info", help="show the salt fingerprint")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        args = parser.parse_args(["info"])
    args.func(args)


if __name__ == "__main__":
    main()
