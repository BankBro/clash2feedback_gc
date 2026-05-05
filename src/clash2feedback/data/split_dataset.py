from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pandas as pd

from clash2feedback.utils.files import ensure_dir


DEFAULT_GROUP_PRIORITY = [
    "uniprot_id",
    "target_id",
    "target_name",
    "protein_family",
    "cluster",
    "pdb_id",
    "complex_id",
]


def resolve_split_groups(
    manifest: pd.DataFrame,
    *,
    group_priority: list[str] | None = None,
) -> tuple[pd.DataFrame, str]:
    priority = group_priority or DEFAULT_GROUP_PRIORITY
    rows = []
    for _, row in manifest.iterrows():
        source_col = "complex_id"
        value = row.get("complex_id")
        for column in priority:
            if column in manifest.columns and _not_empty(row.get(column)):
                source_col = column
                value = row.get(column)
                break
        item = row.to_dict()
        item["split_group_resolved"] = str(value)
        item["split_group_source"] = source_col
        rows.append(item)
    resolved = pd.DataFrame(rows)
    source_values = set(resolved.get("split_group_source", []))
    if source_values & {"uniprot_id", "target_id", "target_name", "protein_family", "cluster"}:
        strategy = "target_level"
    elif source_values == {"complex_id"}:
        strategy = "complex_level_smoke"
    else:
        strategy = "pdb_or_complex_level_smoke"
    return resolved, strategy


def make_grouped_splits(
    manifest: pd.DataFrame,
    *,
    group_col: str = "split_group_resolved",
    ratios: tuple[float, float, float] = (0.7, 0.1, 0.2),
    seed: int = 20260504,
) -> dict[str, list[str]]:
    if manifest.empty:
        return {"train": [], "val": [], "test": []}
    if group_col not in manifest.columns:
        raise ValueError(f"Missing split group column: {group_col}")

    grouped = {
        str(group): sorted(rows["sample_id"].astype(str).tolist())
        for group, rows in manifest.groupby(group_col, sort=True)
    }
    groups = sorted(grouped)
    rng = random.Random(seed)
    rng.shuffle(groups)
    split_names = _assign_split_names(len(groups), ratios)
    splits = {"train": [], "val": [], "test": []}
    for group, split_name in zip(groups, split_names, strict=True):
        splits[split_name].extend(grouped[group])
    for split_name in splits:
        splits[split_name] = sorted(splits[split_name])
    return splits


def write_splits(splits: dict[str, list[str]], output_dir: str | Path) -> None:
    directory = ensure_dir(output_dir)
    for split_name in ("train", "val", "test"):
        with (directory / f"{split_name}.txt").open("w", encoding="utf-8") as f:
            for sample_id in splits.get(split_name, []):
                f.write(f"{sample_id}\n")


def make_splits_from_manifest(
    manifest_path: str | Path,
    output_dir: str | Path,
    config: dict[str, Any],
) -> pd.DataFrame:
    manifest = pd.read_parquet(manifest_path)
    split_cfg = config.get("split", {})
    directory = ensure_dir(output_dir)
    if manifest.empty:
        write_splits({"train": [], "val": [], "test": []}, directory)
        report = manifest.copy()
        for column in ["split_group_resolved", "split_group_source", "split"]:
            report[column] = pd.Series(dtype=str)
        report["split_strategy"] = "complex_level_smoke"
        report["split_seed"] = int(split_cfg.get("seed", 20260504))
        report["split_version"] = str(split_cfg.get("split_version", "v0_1"))
        report.to_csv(directory / "split_report.csv", index=False)
        return report

    resolved, strategy = resolve_split_groups(
        manifest,
        group_priority=list(split_cfg.get("group_priority", DEFAULT_GROUP_PRIORITY)),
    )
    splits = make_grouped_splits(
        resolved,
        ratios=tuple(float(x) for x in split_cfg.get("ratios", [0.7, 0.1, 0.2])),
        seed=int(split_cfg.get("seed", 20260504)),
    )
    write_splits(splits, directory)

    split_by_sample = {
        sample_id: split_name
        for split_name, sample_ids in splits.items()
        for sample_id in sample_ids
    }
    report = resolved.copy()
    report["split"] = report["sample_id"].astype(str).map(split_by_sample)
    report["split_strategy"] = strategy
    report["split_seed"] = int(split_cfg.get("seed", 20260504))
    report["split_version"] = str(split_cfg.get("split_version", "v0_1"))
    report.to_csv(directory / "split_report.csv", index=False)
    return report


def _assign_split_names(num_groups: int, ratios: tuple[float, float, float]) -> list[str]:
    if num_groups <= 0:
        return []
    if num_groups == 1:
        return ["train"]
    if num_groups == 2:
        return ["train", "test"]

    train_ratio, val_ratio, test_ratio = ratios
    total = train_ratio + val_ratio + test_ratio
    train_ratio, val_ratio, test_ratio = train_ratio / total, val_ratio / total, test_ratio / total
    num_val = max(1, round(num_groups * val_ratio))
    num_test = max(1, round(num_groups * test_ratio))
    num_train = max(1, num_groups - num_val - num_test)
    while num_train + num_val + num_test > num_groups:
        if num_train >= num_val and num_train >= num_test and num_train > 1:
            num_train -= 1
        elif num_test > 1:
            num_test -= 1
        else:
            num_val -= 1
    return ["train"] * num_train + ["val"] * num_val + ["test"] * num_test


def _not_empty(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    return str(value) != ""
