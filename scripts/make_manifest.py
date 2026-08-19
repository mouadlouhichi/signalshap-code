#!/usr/bin/env python3
"""Emit a machine-readable manifest binding every reported number to a file.

    python scripts/make_manifest.py

Writes artefacts/MANIFEST.json: for each artefact, a SHA-256 and size; plus the
environment that produced the run (Python, key package versions, BLAS, platform)
and the git commit. A reader can then check that the archive they downloaded is
the archive the tables came from, which a prose sentence cannot establish.

This exists because the manuscript previously had to say the public snapshot
"does not reproduce the present tables". A manifest plus a tagged commit turns
that into a checkable claim.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artefacts"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:                                        # noqa: BLE001
        return "unavailable"


def _versions() -> dict:
    out = {"python": sys.version.split()[0], "platform": platform.platform(),
           "machine": platform.machine()}
    for mod in ("numpy", "scipy", "pandas", "sklearn", "matplotlib"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:                                    # noqa: BLE001
            out[mod] = "absent"
    try:
        import numpy as np
        cfg = getattr(np, "show_config", None)
        # BLAS backend materially changes candidate contents; record it.
        out["blas"] = (np.__config__.blas_opt_info.get("libraries", [])
                       if hasattr(np, "__config__")
                       and hasattr(np.__config__, "blas_opt_info") else "see numpy.show_config")
    except Exception:                                        # noqa: BLE001
        out["blas"] = "unavailable"
    return out


def main() -> int:
    files = {}
    for p in sorted(ART.rglob("*.json")):
        if p.name == "MANIFEST.json":
            continue
        files[str(p.relative_to(ART))] = {"sha256": _sha(p),
                                          "bytes": p.stat().st_size}
    man = {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_describe": _git("describe", "--tags", "--always", "--dirty"),
        "environment": _versions(),
        "n_artefacts": len(files),
        "artefacts": files,
        "note": ("SHA-256 of every artefact backing a reported number, with the "
                 "commit and environment that produced them. Cross-platform BLAS "
                 "differences change candidate contents for a small number of "
                 "users, so the backend is recorded alongside the hashes."),
    }
    (ART / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    print(f"wrote artefacts/MANIFEST.json: {len(files)} artefacts, "
          f"commit {man['git_commit'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
