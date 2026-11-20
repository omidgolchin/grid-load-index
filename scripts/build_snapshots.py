"""Build the retrospective snapshots and targets (PLAN.md).

Writes data/snapshots/snapshots.parquet and targets.parquet
(gitignored) and data/manifests/snapshot_manifest.csv (committed:
counts and hashes).

Usage: .venv/bin/python scripts/build_snapshots.py
"""

import hashlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import snapshots, spec  # noqa: E402


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    summary = snapshots.build_all()
    rows = []
    for path, kind in ((spec.SNAPSHOTS_PARQUET, "snapshots"), (spec.TARGETS_PARQUET, "targets")):
        rows.append({
            "file": str(path.relative_to(spec.ROOT)),
            "kind": kind,
            "bytes": path.stat().st_size,
            "sha256": sha256_of(path),
        })
    manifest = pd.DataFrame(rows)
    out = spec.ROOT / "data" / "manifests" / "snapshot_manifest.csv"
    manifest.to_csv(out, index=False)
    print(summary)
    print(manifest.to_string(index=False))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
