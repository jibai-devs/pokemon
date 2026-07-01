"""Bulk-download top-rated CABT episode replays from Kaggle's daily dataset index.

Each day's dataset (kaggle/pokemon-tcg-ai-battle-episodes-<date>) ships a
manifest.csv with one row per episode: episode_id, avg_score (agent rating),
size_bytes, etc. We pick the top-N highest-rated episodes per day and pull
just those JSON files, instead of downloading the entire multi-GB dataset.

Usage:
    uv run python scripts/download_replays.py
    uv run python scripts/download_replays.py --top-per-day 100 --out data/replays/raw
"""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

DATES = [
    "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20",
    "2026-06-21", "2026-06-22", "2026-06-23", "2026-06-24", "2026-06-25",
    "2026-06-26", "2026-06-27", "2026-06-28", "2026-06-29", "2026-06-30",
]

DATASET_TMPL = "kaggle/pokemon-tcg-ai-battle-episodes-{date}"


def top_episode_ids(api: KaggleApi, dataset: str, top_n: int, manifests_dir: Path) -> list[str]:
    manifest_path = manifests_dir / f"{dataset.split('/')[-1]}.csv"
    if not manifest_path.exists():
        api.dataset_download_file(dataset, "manifest.csv", path=str(manifests_dir), force=True, quiet=True)
        downloaded = manifests_dir / "manifest.csv"
        downloaded.rename(manifest_path)

    with manifest_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: float(r["avg_score"]), reverse=True)
    return [r["episode_id"] for r in rows[:top_n]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top-per-day", type=int, default=100)
    parser.add_argument("--out", default="data/replays/raw")
    parser.add_argument("--manifests-dir", default="data/replays/manifests")
    args = parser.parse_args()

    out_dir = Path(args.out)
    manifests_dir = Path(args.manifests_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    api = KaggleApi()
    api.authenticate()

    total_downloaded = 0
    total_skipped = 0
    for date in DATES:
        dataset = DATASET_TMPL.format(date=date)
        episode_ids = top_episode_ids(api, dataset, args.top_per_day, manifests_dir)
        print(f"{date}: top {len(episode_ids)} episodes by avg_score")

        for i, ep_id in enumerate(episode_ids, 1):
            fname = f"{ep_id}.json"
            dest = out_dir / fname
            if dest.exists():
                total_skipped += 1
                continue
            api.dataset_download_file(dataset, fname, path=str(out_dir), force=True, quiet=True)
            total_downloaded += 1
            if i % 20 == 0:
                print(f"  {date}: {i}/{len(episode_ids)} done")

    print(f"\nDone. Downloaded {total_downloaded} new replays, skipped {total_skipped} already present.")
    print(f"Total replays in {out_dir}: {len(list(out_dir.glob('*.json')))}")


if __name__ == "__main__":
    main()
