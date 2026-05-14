from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_MASK_SEED_COLUMNS = {
    "case_id",
    "base_sample_id",
    "base_split",
    "injection_mode",
    "difficulty_bin",
    "oracle_mask_atom_indices",
    "oracle_keep_atom_indices",
    "oracle_anchor_scaffold_atom_idx",
    "oracle_anchor_rgroup_atom_idx",
    "oracle_anchor_bond_idx",
    "target_num_severe_pairs",
    "max_clash_depth",
    "phase4_0_backend_feasibility_candidate",
    "set_membership_s2",
}


def load_mask_seed(path: str | Path) -> pd.DataFrame:
    mask_seed_path = Path(path)
    if not mask_seed_path.exists():
        raise FileNotFoundError(f"Missing phase4 mask seed: {mask_seed_path}")
    table = pd.read_csv(mask_seed_path)
    missing = sorted(REQUIRED_MASK_SEED_COLUMNS - set(table.columns))
    if missing:
        raise ValueError(f"phase4_mask_seed.csv missing required columns: {missing}")
    return table


def select_preflight_cases(mask_seed: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    selection_cfg = config.get("selection", {})
    expected_count = int(selection_cfg.get("preflight_count", 5))
    preferred = list(selection_cfg.get("predefined_preflight_cases", []))
    eligible = mask_seed[
        mask_seed["phase4_0_backend_feasibility_candidate"].map(_as_bool)
        & mask_seed["set_membership_s2"].map(_as_bool)
    ].copy()
    if eligible.empty:
        raise ValueError("No S2 phase4_0_backend_feasibility_candidate rows found.")

    selected_rows: list[pd.Series] = []
    reasons: dict[str, str] = {}
    if preferred:
        by_case_id = {str(row["case_id"]): row for _, row in eligible.iterrows()}
        for item in preferred:
            case_id = str(item.get("case_id") or "")
            if case_id not in by_case_id:
                raise ValueError(f"Configured preflight case is not eligible or missing: {case_id}")
            selected_rows.append(by_case_id[case_id])
            reasons[case_id] = str(item.get("selection_reason") or "predefined_preflight_case")
    else:
        selected_rows = _fallback_preflight_selection(eligible, expected_count)
        reasons = {str(row["case_id"]): "deterministic_fallback_preflight_case" for row in selected_rows}

    if len(selected_rows) != expected_count:
        raise ValueError(f"Expected {expected_count} preflight cases, got {len(selected_rows)}.")
    selected = pd.DataFrame(selected_rows).copy()
    selected.insert(0, "selection_rank", range(1, len(selected) + 1))
    selected["selection_reason"] = selected["case_id"].map(reasons)
    selected["oracle_mask_size"] = selected["oracle_mask_atom_indices"].map(lambda value: len(parse_json_list(value)))
    selected["oracle_keep_size"] = selected["oracle_keep_atom_indices"].map(lambda value: len(parse_json_list(value)))
    return selected[
        [
            "selection_rank",
            "case_id",
            "base_sample_id",
            "base_split",
            "injection_mode",
            "difficulty_bin",
            "oracle_mask_size",
            "oracle_keep_size",
            "target_num_severe_pairs",
            "max_clash_depth",
            "selection_reason",
            "oracle_mask_atom_indices",
            "oracle_keep_atom_indices",
            "oracle_anchor_scaffold_atom_idx",
            "oracle_anchor_rgroup_atom_idx",
            "oracle_anchor_bond_idx",
        ]
    ]


def select_formal_cases(mask_seed: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    selection_cfg = config.get("selection", {})
    expected_count = int(selection_cfg.get("small_scale_count", 40))
    seed = int(config.get("seed", 20260514))
    base_sample_cap = int(selection_cfg.get("base_sample_soft_cap", 3))
    quotas = selection_cfg.get("small_scale_quotas", {})
    injection_quota = dict(quotas.get("injection_mode", {"directed_clash": 14, "easy_rotation": 13, "torsion_perturb": 13}))
    difficulty_quota = dict(quotas.get("difficulty_bin", {"easy": 27, "medium": 13}))
    split_quota = dict(quotas.get("base_split", {"train": 29, "test": 9, "val": 2}))

    eligible = mask_seed[
        mask_seed["phase4_0_backend_feasibility_candidate"].map(_as_bool)
        & mask_seed["set_membership_s2"].map(_as_bool)
    ].copy()
    if eligible.empty:
        raise ValueError("No S2 phase4_0_backend_feasibility_candidate rows found.")

    if sum(int(value) for value in injection_quota.values()) != expected_count:
        raise ValueError("injection_mode quota total does not match small_scale_count.")
    if sum(int(value) for value in difficulty_quota.values()) != expected_count:
        raise ValueError("difficulty_bin quota total does not match small_scale_count.")
    if sum(int(value) for value in split_quota.values()) != expected_count:
        raise ValueError("base_split quota total does not match small_scale_count.")

    selected = _solve_formal_selection(
        eligible,
        seed=seed,
        expected_count=expected_count,
        injection_quota={str(key): int(value) for key, value in injection_quota.items()},
        difficulty_quota={str(key): int(value) for key, value in difficulty_quota.items()},
        split_quota={str(key): int(value) for key, value in split_quota.items()},
        base_sample_cap=base_sample_cap,
    )
    selected = selected.sort_values(["selection_tiebreaker", "case_id"]).reset_index(drop=True)
    selected.insert(0, "selection_rank", range(1, len(selected) + 1))
    selected["selection_reason"] = (
        "formal_40_sha256_stratified_seed_"
        + str(seed)
        + "_base_sample_cap_"
        + str(base_sample_cap)
    )
    selected["oracle_mask_size"] = selected["oracle_mask_atom_indices"].map(lambda value: len(parse_json_list(value)))
    selected["oracle_keep_size"] = selected["oracle_keep_atom_indices"].map(lambda value: len(parse_json_list(value)))
    return selected[
        [
            "selection_rank",
            "case_id",
            "base_sample_id",
            "base_split",
            "injection_mode",
            "difficulty_bin",
            "oracle_mask_size",
            "oracle_keep_size",
            "target_num_severe_pairs",
            "max_clash_depth",
            "selection_reason",
            "selection_tiebreaker",
            "oracle_mask_atom_indices",
            "oracle_keep_atom_indices",
            "oracle_anchor_scaffold_atom_idx",
            "oracle_anchor_rgroup_atom_idx",
            "oracle_anchor_bond_idx",
        ]
    ]


def parse_json_list(value: Any) -> list[int]:
    if isinstance(value, list):
        raw = value
    elif pd.isna(value):
        raw = []
    else:
        raw = json.loads(str(value))
    return [int(item) for item in raw]


def _fallback_preflight_selection(eligible: pd.DataFrame, expected_count: int) -> list[pd.Series]:
    ordered = eligible.copy()
    ordered["oracle_mask_size"] = ordered["oracle_mask_atom_indices"].map(lambda value: len(parse_json_list(value)))
    ordered["split_rank"] = ordered["base_split"].map({"test": 0, "val": 1, "train": 2}).fillna(9)
    ordered["difficulty_rank"] = ordered["difficulty_bin"].map({"medium": 0, "easy": 1}).fillna(9)
    ordered["depth_distance"] = (ordered["max_clash_depth"].astype(float) - 0.8).abs()
    ordered = ordered.sort_values(["split_rank", "difficulty_rank", "depth_distance", "oracle_mask_size", "case_id"])
    return [row for _, row in ordered.head(expected_count).iterrows()]


def _solve_formal_selection(
    eligible: pd.DataFrame,
    *,
    seed: int,
    expected_count: int,
    injection_quota: dict[str, int],
    difficulty_quota: dict[str, int],
    split_quota: dict[str, int],
    base_sample_cap: int,
) -> pd.DataFrame:
    try:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import lil_matrix
    except Exception as exc:  # pragma: no cover - exercised only when scipy is absent.
        raise RuntimeError("Formal 40-case selection requires scipy.optimize.milp in the active environment.") from exc

    table = eligible.copy().reset_index(drop=True)
    table["selection_tiebreaker"] = table["case_id"].astype(str).map(lambda case_id: _stable_tiebreaker(seed, case_id))
    table = table.sort_values(["selection_tiebreaker", "case_id"]).reset_index(drop=True)
    n = int(table.shape[0])
    constraints: list[tuple[dict[int, float], float, float]] = []

    constraints.append(({idx: 1.0 for idx in range(n)}, float(expected_count), float(expected_count)))
    for key, quota in injection_quota.items():
        _add_exact_constraint(constraints, table.index[table["injection_mode"].astype(str) == key].tolist(), quota)
    for key, quota in difficulty_quota.items():
        _add_exact_constraint(constraints, table.index[table["difficulty_bin"].astype(str) == key].tolist(), quota)
    for key, quota in split_quota.items():
        _add_exact_constraint(constraints, table.index[table["base_split"].astype(str) == key].tolist(), quota)
    for _, indices in table.groupby("base_sample_id").groups.items():
        index_list = [int(idx) for idx in indices]
        constraints.append(({idx: 1.0 for idx in index_list}, 0.0, float(base_sample_cap)))

    matrix = lil_matrix((len(constraints), n), dtype=float)
    lower = np.zeros(len(constraints), dtype=float)
    upper = np.zeros(len(constraints), dtype=float)
    for row_idx, (coefficients, lb, ub) in enumerate(constraints):
        for col_idx, value in coefficients.items():
            matrix[row_idx, col_idx] = value
        lower[row_idx] = lb
        upper[row_idx] = ub

    ranks = np.arange(n, dtype=float)
    result = milp(
        c=ranks,
        integrality=np.ones(n, dtype=int),
        bounds=Bounds(np.zeros(n), np.ones(n)),
        constraints=LinearConstraint(matrix.tocsr(), lower, upper),
        options={"time_limit": 30.0, "mip_rel_gap": 0.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"Unable to solve formal 40-case selection: {result.message}")
    chosen = table.loc[result.x > 0.5].copy()
    if int(chosen.shape[0]) != expected_count:
        raise RuntimeError(f"Formal selector returned {chosen.shape[0]} rows, expected {expected_count}.")
    return chosen


def _add_exact_constraint(constraints: list[tuple[dict[int, float], float, float]], indices: list[int], quota: int) -> None:
    constraints.append(({int(idx): 1.0 for idx in indices}, float(quota), float(quota)))


def _stable_tiebreaker(seed: int, case_id: str) -> int:
    digest = hashlib.sha256(f"{seed}:{case_id}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
