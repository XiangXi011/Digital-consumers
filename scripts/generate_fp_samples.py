#!/usr/bin/env python3
"""Generate FP persona samples from mapped M persona samples.

Reads persona_samples_complete.json and personas/FP*.yaml.
For each FP, picks representative samples from the mapped M segments,
rewrites segment_id/segment_name/sample_id, and appends to the JSON.
"""

import copy
import json
import random
from pathlib import Path

import yaml


def load_fp_yamls(personas_dir: Path) -> dict[str, dict]:
    fps = {}
    for path in sorted(personas_dir.glob("FP*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        fps[data["id"]] = data
    return fps


def generate_fp_samples(json_path: Path, personas_dir: Path, samples_per_fp: int = 2) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    samples: list[dict] = data.get("samples", [])

    fp_yamls = load_fp_yamls(personas_dir)

    # Group M samples by segment_id
    m_samples_by_segment: dict[str, list[dict]] = {}
    for sample in samples:
        sid = sample.get("segment_id", "")
        if sid.startswith("M"):
            m_samples_by_segment.setdefault(sid, []).append(sample)

    existing_fp_ids = {s["segment_id"] for s in samples if s["segment_id"].startswith("F")}
    if existing_fp_ids:
        print(f"FP samples already exist: {existing_fp_ids}; skipping generation.")
        return

    rng = random.Random(42)  # deterministic for reproducibility
    new_samples: list[dict] = []

    for fp_id, fp_data in sorted(fp_yamls.items()):
        fp_name = fp_data["name"]
        mapped = fp_data.get("mapped_system_personas", [])
        if not mapped:
            print(f"Warning: {fp_id} has no mapped_system_personas, skipping.")
            continue

        # Collect candidate M samples from all mapped segments
        candidates: list[dict] = []
        for m_id in mapped:
            candidates.extend(m_samples_by_segment.get(m_id, []))

        if not candidates:
            print(f"Warning: no M samples found for {fp_id} mapped to {mapped}, skipping.")
            continue

        # Pick samples_per_fp unique candidates
        selected = rng.sample(candidates, min(samples_per_fp, len(candidates)))

        for idx, src in enumerate(selected, start=1):
            new_sample = copy.deepcopy(src)
            new_sample["sample_id"] = f"{fp_id}-{idx:02d}"
            new_sample["segment_id"] = fp_id
            new_sample["segment_name"] = fp_name
            # Update nickname to reflect the FP persona (keep original as base)
            old_nickname = new_sample.get("basic_profile", {}).get("nickname", "")
            if old_nickname:
                new_sample["basic_profile"]["nickname"] = f"{old_nickname}({fp_name})"
            new_samples.append(new_sample)

        print(f"Generated {len(selected)} samples for {fp_id} ({fp_name}) from {mapped}")

    samples.extend(new_samples)
    data["samples"] = samples

    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTotal samples: {len(samples)} ({len(new_samples)} new FP samples added)")
    print(f"Saved to {json_path}")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    json_path = repo_root / "persona_samples_complete.json"
    personas_dir = repo_root / "personas"
    generate_fp_samples(json_path, personas_dir, samples_per_fp=2)
