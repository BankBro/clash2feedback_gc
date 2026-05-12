from __future__ import annotations

from typing import Any

import pandas as pd


GAP_COLUMNS = [
    "group",
    "metric",
    "count",
    "mean",
    "median",
    "min",
    "max",
]


def artificial_vs_model_induced_gap(
    phase2_manifest: pd.DataFrame,
    model_clash_report: pd.DataFrame,
    failure_taxonomy: pd.DataFrame,
    repairability_proxy: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    supported = phase2_manifest[phase2_manifest.get("oracle_split", "") == "supported_single_rgroup"] if not phase2_manifest.empty else phase2_manifest
    rows.extend(_numeric_rows("phase2_supported_single_rgroup", supported, ["target_num_severe_pairs", "max_clash_depth", "total_clash_score", "dominant_ratio_valid_rgroups", "ligand_internal_severe_clash_count"]))
    single_ids = set(
        failure_taxonomy.loc[failure_taxonomy.get("failure_taxonomy", "") == "single_rgroup_clash", "candidate_id"].tolist()
    ) if not failure_taxonomy.empty and "candidate_id" in failure_taxonomy else set()
    model_single = model_clash_report[model_clash_report["candidate_id"].isin(single_ids)] if single_ids and "candidate_id" in model_clash_report else model_clash_report.head(0)
    rows.extend(_numeric_rows("model_induced_single_rgroup_clash", model_single, ["num_severe_clash_pairs", "max_clash_depth", "total_clash_score"]))
    rows.extend(_numeric_rows("model_induced_all_failures", model_clash_report, ["num_severe_clash_pairs", "max_clash_depth", "total_clash_score"]))
    if not failure_taxonomy.empty:
        for taxonomy, count in failure_taxonomy["failure_taxonomy"].value_counts(dropna=False).items():
            rows.append(_count_row("model_induced_all_failures", f"failure_taxonomy:{taxonomy}", int(count)))
    if not repairability_proxy.empty:
        for proxy, count in repairability_proxy["repairability_proxy"].value_counts(dropna=False).items():
            rows.append(_count_row("model_induced_all_failures", f"repairability_proxy:{proxy}", int(count)))
    return pd.DataFrame(rows, columns=GAP_COLUMNS)


def _numeric_rows(group_name: str, df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if df.empty:
        return rows
    for column in columns:
        if column not in df:
            continue
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            {
                "group": group_name,
                "metric": column,
                "count": int(len(values)),
                "mean": float(values.mean()),
                "median": float(values.median()),
                "min": float(values.min()),
                "max": float(values.max()),
            }
        )
    return rows


def _count_row(group_name: str, metric: str, count: int) -> dict[str, Any]:
    return {
        "group": group_name,
        "metric": metric,
        "count": int(count),
        "mean": float(count),
        "median": float(count),
        "min": float(count),
        "max": float(count),
    }
