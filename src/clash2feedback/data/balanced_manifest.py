from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from clash2feedback.utils.files import ensure_dir


PASS_STATUSES = {"pass", "passed", "ok", "manual_pass"}
FAIL_STATUSES = {"fail", "failed", "manual_fail"}
UNCERTAIN_STATUSES = {"uncertain", "requires_human_review"}


@dataclass(frozen=True)
class BalancedSelectionResult:
    selected: pd.DataFrame
    clean_pool_count: int
    requested_max_samples: int
    actual_samples: int
    min_samples: int
    max_per_target: int
    target_col: str
    reason: str


def make_balanced_selection(
    manifest: pd.DataFrame,
    visual_check: pd.DataFrame | None = None,
    *,
    max_samples: int = 30,
    min_samples: int = 20,
    max_per_target: int = 5,
    seed: int = 20260504,
) -> BalancedSelectionResult:
    """Select a deterministic target-balanced phase0 subset from a clean pool."""

    if max_samples <= 0:
        raise ValueError("max_samples must be positive")
    if min_samples <= 0:
        raise ValueError("min_samples must be positive")
    if max_per_target <= 0:
        raise ValueError("max_per_target must be positive")

    pool = _phase0_pool(manifest).copy()
    clean_pool_count = len(pool)
    if pool.empty:
        return BalancedSelectionResult(
            selected=pool,
            clean_pool_count=clean_pool_count,
            requested_max_samples=max_samples,
            actual_samples=0,
            min_samples=min_samples,
            max_per_target=max_per_target,
            target_col="complex_id",
            reason="no_phase0_usable_samples",
        )

    pool = _merge_visual_check(pool, visual_check)
    pool = pool[~pool["manual_check_status_norm"].isin(FAIL_STATUSES)].copy()
    pool["balanced_target"] = pool.apply(_target_key, axis=1)
    target_col = "balanced_target"
    pool["_manual_rank"] = pool["manual_check_status_norm"].map(_manual_rank).fillna(2).astype(int)
    pool["_priority_rank"] = pool["recommended_check_priority"].map({"high": 0, "medium": 1, "low": 2}).fillna(3)
    pool["_sample_id"] = pool["sample_id"].astype(str)

    selected_indices: list[int] = []
    grouped = {
        str(target): _ordered_bucket(rows, seed=seed)
        for target, rows in pool.groupby("balanced_target", sort=True)
    }
    for round_index in range(max_per_target):
        for target in sorted(grouped):
            if len(selected_indices) >= max_samples:
                break
            bucket = grouped[target]
            if round_index < len(bucket):
                selected_indices.append(int(bucket.index[round_index]))
        if len(selected_indices) >= max_samples:
            break

    selected = pool.loc[selected_indices].copy()
    selected = selected.sort_values(["balanced_target", "sample_id"]).reset_index(drop=True)
    reason = _selection_reason(
        selected_count=len(selected),
        max_samples=max_samples,
        min_samples=min_samples,
        num_targets=len(grouped),
        max_per_target=max_per_target,
    )
    return BalancedSelectionResult(
        selected=selected.drop(columns=[c for c in selected.columns if c.startswith("_")]),
        clean_pool_count=clean_pool_count,
        requested_max_samples=max_samples,
        actual_samples=len(selected),
        min_samples=min_samples,
        max_per_target=max_per_target,
        target_col=target_col,
        reason=reason,
    )


def write_balanced_outputs(
    result: BalancedSelectionResult,
    *,
    output_path: str | Path,
    summary_path: str | Path,
) -> None:
    output = Path(output_path)
    ensure_dir(output.parent)
    with output.open("w", encoding="utf-8") as f:
        for sample_id in result.selected["sample_id"].astype(str):
            f.write(f"{sample_id}\n")

    summary = balanced_summary_markdown(result, output_path=output)
    summary_file = Path(summary_path)
    ensure_dir(summary_file.parent)
    summary_file.write_text(summary, encoding="utf-8")


def balanced_summary_markdown(result: BalancedSelectionResult, *, output_path: str | Path) -> str:
    selected = result.selected
    lines = [
        "# 阶段 0 balanced subset 复盘",
        "",
        "## 1. 选择结论",
        "",
        f"- clean pool 总数: {result.clean_pool_count}.",
        f"- requested_max_samples: {result.requested_max_samples}.",
        f"- actual_samples: {result.actual_samples}.",
        f"- min_samples: {result.min_samples}.",
        f"- max_per_target: {result.max_per_target}.",
        f"- 输出清单: `{output_path}`.",
        f"- 选择原因: {result.reason}.",
        "- `phase0_balanced_30_v0_1` 表示 target-balanced subset with up to 30 samples, actual n = "
        f"{result.actual_samples}.",
        "",
        "## 2. Target 分布",
        "",
    ]
    lines.extend(_markdown_table(_value_counts_table(selected, "balanced_target", "target", "count")))
    lines.extend(
        [
            "",
            "## 3. 数值分布",
            "",
        ]
    )
    for column, label in [
        ("ligand_heavy_atoms", "ligand heavy atoms"),
        ("num_pocket_atoms_8A", "8A pocket atoms"),
        ("num_valid_rgroups", "valid R-groups"),
    ]:
        stats = _numeric_summary(selected, column)
        lines.append(f"- {label}: {stats}.")
    lines.extend(
        [
            "",
            "## 4. 人工检查使用情况",
            "",
        ]
    )
    lines.extend(_markdown_table(_value_counts_table(selected, "manual_check_status_norm", "manual_check_status", "count")))
    lines.extend(
        [
            "",
            "## 5. 判断",
            "",
            f"- 是否覆盖至少 6 个 target: {'是' if selected['balanced_target'].nunique() >= 6 else '否'}.",
            f"- 是否满足每个 target 最多 {result.max_per_target} 个: "
            f"{'是' if _max_count(selected, 'balanced_target') <= result.max_per_target else '否'}.",
            "- 未满 30 不是失败; 本轮优先保证 target diversity, 不为凑满 30 放宽 target cap.",
        ]
    )
    return "\n".join(lines) + "\n"


def _phase0_pool(manifest: pd.DataFrame) -> pd.DataFrame:
    if manifest.empty:
        return manifest.copy()
    if "phase0_usable" not in manifest.columns:
        return manifest.copy()
    return manifest[manifest["phase0_usable"] == True].copy()  # noqa: E712


def _merge_visual_check(manifest: pd.DataFrame, visual_check: pd.DataFrame | None) -> pd.DataFrame:
    rows = manifest.copy()
    for column, default in [
        ("recommended_check_priority", "medium"),
        ("manual_check_status", "unchecked"),
        ("manual_notes", ""),
    ]:
        if column not in rows.columns:
            rows[column] = default
    if visual_check is not None and not visual_check.empty and "sample_id" in visual_check.columns:
        keep = [
            column
            for column in [
                "sample_id",
                "recommended_check_priority",
                "manual_check_status",
                "manual_notes",
            ]
            if column in visual_check.columns
        ]
        rows = rows.drop(columns=[c for c in keep if c != "sample_id" and c in rows.columns], errors="ignore")
        rows = rows.merge(visual_check[keep], on="sample_id", how="left")
    rows["recommended_check_priority"] = rows["recommended_check_priority"].fillna("medium").astype(str)
    rows["manual_check_status"] = rows["manual_check_status"].fillna("unchecked").astype(str)
    rows["manual_check_status_norm"] = rows["manual_check_status"].str.strip().str.lower()
    rows.loc[rows["manual_check_status_norm"].eq(""), "manual_check_status_norm"] = "unchecked"
    return rows


def _target_key(row: pd.Series) -> str:
    for column in ["target_id", "split_group", "target_name", "protein_family", "cluster", "pdb_id", "complex_id"]:
        value = row.get(column)
        if _not_empty(value):
            return str(value)
    return str(row.get("sample_id"))


def _ordered_bucket(rows: pd.DataFrame, *, seed: int) -> pd.DataFrame:
    bucket = rows.copy()
    bucket["_tie_break"] = bucket["sample_id"].astype(str).map(lambda value: _stable_tie_break(value, seed))
    return bucket.sort_values(
        [
            "_manual_rank",
            "_priority_rank",
            "num_valid_rgroups",
            "ligand_heavy_atoms",
            "_tie_break",
            "_sample_id",
        ],
        ascending=[True, True, True, True, True, True],
    )


def _stable_tie_break(value: str, seed: int) -> int:
    total = seed
    for char in value:
        total = (total * 131 + ord(char)) % 1_000_003
    return total


def _manual_rank(status: Any) -> int:
    value = str(status).strip().lower()
    if value in PASS_STATUSES:
        return 0
    if value == "unchecked":
        return 1
    if value in UNCERTAIN_STATUSES:
        return 2
    if value in FAIL_STATUSES:
        return 99
    return 3


def _selection_reason(
    *,
    selected_count: int,
    max_samples: int,
    min_samples: int,
    num_targets: int,
    max_per_target: int,
) -> str:
    if selected_count >= max_samples:
        return "达到 requested_max_samples"
    if selected_count >= min_samples:
        return (
            f"当前只有 {num_targets} 个 target, 且严格执行 max_per_target={max_per_target} 后无法满 "
            f"{max_samples}; 选择 {selected_count} 是为了优先保证 target diversity"
        )
    return f"低于 min_samples={min_samples}, 需要补充更多 clean target 或放宽筛选策略"


def _numeric_summary(df: pd.DataFrame, column: str) -> str:
    if column not in df.columns:
        return "missing"
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return "count=0"
    return (
        f"count={int(values.count())}, min={values.min():.3g}, "
        f"median={values.median():.3g}, max={values.max():.3g}"
    )


def _value_counts_table(df: pd.DataFrame, column: str, name: str, count_name: str) -> pd.DataFrame:
    if column not in df.columns or df.empty:
        return pd.DataFrame(columns=[name, count_name])
    counts = df[column].fillna("missing").astype(str).value_counts().rename_axis(name).reset_index(name=count_name)
    return counts


def _markdown_table(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["| item | count |", "|---|---:|"]
    columns = list(df.columns)
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return lines


def _max_count(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns or df.empty:
        return 0
    return int(df[column].value_counts().max())


def _not_empty(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    return str(value).strip() != ""
