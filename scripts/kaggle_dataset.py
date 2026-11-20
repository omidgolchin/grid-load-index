"""Create the private Kaggle dataset that carries the run inputs.

The custom Kaggle helper has no dataset-create command, so this
script performs the same flow the official Kaggle CLI uses,
through the connector's registered credential (a surrogate that
is swapped for the real token on requests to www.kaggle.com;
the token itself never appears here):

  1. POST /api/v1/blobs/upload     -> {token, createUrl} per file
  2. PUT the file bytes to createUrl (a signed URL; no credential)
  3. POST /api/v1/datasets/create/new with the file tokens,
     isPrivate = true
  4. Read the dataset back (metadata + view) and report the
     recorded privacy.

Contents (version 1): the retrospective snapshots
(contexts + ids) and a targets file reduced to the target
timestamps — everything a model run needs and nothing it must
not see (no reported values, no operator forecasts). The
forecasts and scores are added as a later version when they
exist (brief Step 8).

Usage:
  python3 scripts/kaggle_dataset.py [--slug grid-load-index-data]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HELPER_DIR = os.environ.get("CREDENTIAL_HELPER_DIR")
if not HELPER_DIR:
    raise SystemExit(
        "CREDENTIAL_HELPER_DIR is not set: point it at the directory "
        "holding dynamic_credentials.py (the credential helper this "
        "script imports)."
    )
sys.path.insert(0, HELPER_DIR)
from dynamic_credentials import add_surrogate_to_request, read_json_response  # noqa: E402

BASE = "https://www.kaggle.com/api/v1"
USERNAME = "omidgolchin"
ROOT = Path(__file__).resolve().parent.parent
STAGE_DIR = ROOT / "data" / "kaggle_dataset"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def _open(request, timeout=300):
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            return read_json_response(response)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:800]
        raise RuntimeError(f"HTTP {e.code} from {request.full_url}: {body}") from None


def post_json(path, payload):
    data = json.dumps(payload).encode()
    request = urllib.request.Request(BASE + path, data=data, method="POST")
    request.add_header("User-Agent", "grid-load-index kaggle_dataset.py")
    request.add_header("Content-Type", "application/json")
    add_surrogate_to_request(request, "custom.kaggle", allowed_hosts=["www.kaggle.com"])
    return _open(request)


def get(path):
    request = urllib.request.Request(BASE + path)
    request.add_header("User-Agent", "grid-load-index kaggle_dataset.py")
    add_surrogate_to_request(request, "custom.kaggle", allowed_hosts=["www.kaggle.com"])
    return _open(request)


def upload_blob(path: Path) -> str:
    """Start a blob upload and PUT the bytes; return the blob token."""
    stat = path.stat()
    response = post_json("/blobs/upload", {
        "type": 1,  # ApiBlobType.DATASET
        "name": path.name,
        "contentType": "application/octet-stream",
        "contentLength": stat.st_size,
        "lastModifiedEpochSeconds": int(stat.st_mtime),
    })
    token = response["token"]
    create_url = response["createUrl"]
    request = urllib.request.Request(create_url, data=path.read_bytes(), method="PUT")
    request.add_header("Content-Length", str(stat.st_size))
    opener = urllib.request.build_opener()  # redirects expected; signed URL, no credential
    with opener.open(request, timeout=600) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"blob PUT for {path.name} returned HTTP {resp.status}")
    return token


def stage_files() -> list[Path]:
    """Write the dataset's files into the staging directory."""
    import pandas as pd

    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    snapshots_src = ROOT / "data" / "snapshots" / "snapshots.parquet"
    targets_src = ROOT / "data" / "snapshots" / "targets.parquet"
    snapshots_out = STAGE_DIR / "snapshots.parquet"
    if not snapshots_out.exists() or snapshots_out.stat().st_mtime < snapshots_src.stat().st_mtime:
        snapshots_out.write_bytes(snapshots_src.read_bytes())
    targets = pd.read_parquet(targets_src, columns=["series", "issue_date", "horizon", "timestamps_utc"])
    targets_out = STAGE_DIR / "targets_lite.parquet"
    targets.to_parquet(targets_out, index=False)
    return [snapshots_out, targets_out]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="grid-load-index-data")
    ap.add_argument("--title", default="Grid Load Forecasting Index data")
    args = ap.parse_args()

    files = stage_files()
    tokens = []
    for path in files:
        token = upload_blob(path)
        tokens.append({"token": token, "description": path.name})
        print(f"uploaded {path.name} ({path.stat().st_size} bytes)", flush=True)
    payload = {
        "title": args.title,
        "slug": args.slug,
        "ownerSlug": USERNAME,
        "licenseName": "CC BY 4.0",
        "subtitle": "Retrospective snapshots for the Grid Load Forecasting Index",
        "description": (
            "Snapshot contexts (2,048 cleaned hourly values per series x issue day) and "
            "target timestamps for the Grid Load Forecasting Index retrospective track. "
            "Built from EIA Form 930 hourly demand by balancing authority via the PUDL "
            "stable release v2026.11.0 (EIA data: US-government public domain; PUDL: "
            "CC-BY-4.0). Reported values and operator forecasts are deliberately not "
            "included: model runs see contexts only."
        ),
        "files": tokens,
        "isPrivate": True,
        "categoryIds": [],
    }
    result = post_json("/datasets/create/new", payload)
    print(json.dumps(result, indent=1)[:1200])
    ref = f"{USERNAME}/{args.slug}"
    time.sleep(5)
    metadata = get(f"/datasets/metadata/{USERNAME}/{args.slug}")
    print("metadata:", json.dumps(metadata, indent=1)[:1200])
    print(f"dataset ref: {ref}")


if __name__ == "__main__":
    main()
