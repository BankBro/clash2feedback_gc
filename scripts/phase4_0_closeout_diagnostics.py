from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


RELIABLE_REPAIR_FIELDS = [
    "candidate_readable",
    "ligand_valid",
    "fixed_structure_match_success",
    "old_clash_resolved",
    "no_new_severe_clash",
    "scaffold_stable",
    "keep_region_stable",
    "anchor_integrity",
    "edit_compliance",
    "pocket_retention",
]


REPORT_FILES = [
    "backend_comparison_rates.csv",
    "diffsbdd_center_sensitivity.csv",
    "diffsbdd_center_sensitivity.md",
    "diffdec_failure_funnel.csv",
    "diffdec_failure_analysis.md",
    "rule_backend_diagnostic.md",
    "full_resampling_control_analysis.md",
    "full_resampling_global_control_metrics.csv",
    "phase4_0_closeout_patch_audit.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate phase 4.0 closeout diagnostics from existing result files only."
    )
    parser.add_argument("--report-root", default="reports/phase4_0_backend_feasibility")
    parser.add_argument("--run-root", default="runs/phase4_0_backend_feasibility")
    args = parser.parse_args()

    repo_root = Path.cwd()
    report_root = repo_root / args.report_root
    run_root = repo_root / args.run_root

    data = _load_inputs(report_root)
    backend_rates = _write_backend_comparison_rates(report_root, data)
    center_rows = _write_diffsbdd_center_sensitivity(report_root, data)
    rule_sections = _write_rule_backend_diagnostic(report_root, data)
    diffdec_sections = _write_diffdec_failure_analysis(report_root, run_root, data)
    full_sections = _write_full_resampling_analysis(report_root, data)
    _write_closeout_audit(
        report_root,
        repo_root,
        data,
        backend_rates=backend_rates,
        center_rows=center_rows,
        rule_sections=rule_sections,
        diffdec_sections=diffdec_sections,
        full_sections=full_sections,
    )

    for name in REPORT_FILES:
        print(report_root / name)
    return 0


def _load_inputs(report_root: Path) -> dict[str, object]:
    return {
        "backend_comparison": _read_csv(report_root / "backend_comparison.csv"),
        "candidate_manifest": _read_csv(report_root / "candidate_manifest.csv"),
        "adapter_input_manifest": _read_csv(report_root / "adapter_input_manifest.csv"),
        "verifier_outcome": _read_csv(report_root / "verifier_outcome.csv"),
        "failure_cases": _read_csv(report_root / "failure_cases.csv"),
        "model_inventory": _read_csv(report_root / "model_inventory.csv"),
        "selected_cases": _read_csv(report_root / "selected_cases.csv"),
        "summary": json.loads((report_root / "phase4_0_small_scale_summary.json").read_text(encoding="utf-8")),
    }


def _write_backend_comparison_rates(report_root: Path, data: dict[str, object]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in data["backend_comparison"]:  # type: ignore[index]
        denominator = _to_int(row["selected_case_denominator"])
        attempt_rows = _to_int(row["attempt_rows"])
        candidate_count_sum = _to_int(row["candidate_count_sum"])
        proposal_count_sum = _to_int(row["proposal_count_sum"])
        reliable_cases = _to_int(row["sample_reliable_success_count"])
        output = {
            "backend_name": row["backend_name"],
            "selected_case_denominator": str(denominator),
            "attempt_rows": str(attempt_rows),
            "candidate_count_sum": str(candidate_count_sum),
            "proposal_count_sum": str(proposal_count_sum),
            "failure_attempt_rate": _rate(_to_int(row["failure_attempts"]), attempt_rows),
            "candidate_readable_rate": _rate(_to_int(row["candidate_readable_count"]), candidate_count_sum),
            "fixed_structure_match_rate": _rate(
                _to_int(row["fixed_structure_match_success_count"]), candidate_count_sum
            ),
            "anchor_integrity_rate": _rate(_to_int(row["anchor_integrity_success_count"]), candidate_count_sum),
            "reliable_candidate_rate": _rate(_to_int(row["reliable_candidate_success_count"]), candidate_count_sum),
            "sample_reliable_repair_yield": _rate(reliable_cases, denominator),
            "proposal_per_case_mean": _mean(proposal_count_sum, denominator),
            "candidate_per_case_mean": _mean(candidate_count_sum, denominator),
            "cost_per_reliable_case": _mean(proposal_count_sum, reliable_cases) if reliable_cases else "NA",
        }
        rows.append(output)
    rows.sort(key=lambda item: item["backend_name"])
    _write_csv(report_root / "backend_comparison_rates.csv", rows)
    return rows


def _write_diffsbdd_center_sensitivity(report_root: Path, data: dict[str, object]) -> list[dict[str, str]]:
    candidate_rows = [
        row
        for row in data["candidate_manifest"]  # type: ignore[index]
        if row["backend_name"] == "diffsbdd_conditional_inpainting"
    ]
    verifier_rows = [
        row
        for row in data["verifier_outcome"]  # type: ignore[index]
        if row["backend_name"] == "diffsbdd_conditional_inpainting"
    ]

    attempt_by_center: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in candidate_rows:
        center = _extract_center(row)
        attempt_by_center[center][row["attempt_id"]] = row

    rows: list[dict[str, str]] = []
    for center in ["ligand", "pocket"]:
        attempts = list(attempt_by_center.get(center, {}).values())
        current_verifier = [row for row in verifier_rows if _extract_center(row) == center]
        candidate_denominator = sum(_to_int(row["candidate_count"]) for row in attempts)
        top_failures = _top_reasons(row["failure_reason"] for row in current_verifier if row["failure_reason"])
        rows.append(
            {
                "center": center,
                "attempt_rows": str(len(attempts)),
                "candidate_count": str(candidate_denominator),
                "execution_failure_count": str(
                    len({row["attempt_id"] for row in attempts if row["failure_stage"] == "execution"})
                ),
                "candidate_readable_count": str(_count_true(current_verifier, "candidate_readable")),
                "fixed_structure_match_success_count": str(
                    _count_true(current_verifier, "fixed_structure_match_success")
                ),
                "anchor_integrity_success_count": str(_count_true(current_verifier, "anchor_integrity")),
                "old_clash_resolved_count": str(_count_true(current_verifier, "old_clash_resolved")),
                "no_new_severe_clash_count": str(_count_true(current_verifier, "no_new_severe_clash")),
                "reliable_candidate_success_count": str(_count_true(current_verifier, "reliable_repair_success")),
                "sample_reliable_success_count": str(
                    len({row["case_id"] for row in current_verifier if _is_true(row["reliable_repair_success"])})
                ),
                "top_failure_reasons": top_failures,
            }
        )

    _write_csv(report_root / "diffsbdd_center_sensitivity.csv", rows)

    table = _markdown_table(
        rows,
        [
            "center",
            "attempt_rows",
            "candidate_count",
            "execution_failure_count",
            "candidate_readable_count",
            "anchor_integrity_success_count",
            "old_clash_resolved_count",
            "no_new_severe_clash_count",
            "reliable_candidate_success_count",
            "sample_reliable_success_count",
        ],
    )
    md = [
        "# DiffSBDD Conditional Center Sensitivity",
        "",
        "## 1. Scope",
        "",
        "- 本报告只读取既有 `candidate_manifest.csv` 和 `verifier_outcome.csv`, 未重新调用 DiffSBDD.",
        "- `diffsbdd_conditional_inpainting` 对每个 selected case 分别尝试 `center=ligand` 和 `center=pocket`.",
        "- center 优先从 `generation_metadata.center` 解析, 失败时回退到 `candidate_source` 或 `attempt_id`.",
        "",
        "## 2. Center-Level Counters",
        "",
        table,
        "",
        "## 3. Failure Pattern",
        "",
    ]
    for row in rows:
        md.append(f"- `{row['center']}` top failure reasons: {row['top_failure_reasons'] or 'NA'}.")
    md.extend(
        [
            "",
            "## 4. Interpretation",
            "",
        "- 两个 center 均能产生可读候选, 但可靠修复数仍低, 主要瓶颈不是候选读取, 而是 anchor integrity, old clash resolved 和 no new severe clash 的联合满足.",
        "- `sample_reliable_success_count` 是按单个 center 分别统计的 case 级成功数, ligand 和 pocket 之间可能重叠, 不能直接相加为总体 9/40.",
        "- 当前结果证明 DiffSBDD conditional local completion 有非零可行性, 但进入后续阶段前需要 anchor-aware filtering, local reconnection check 和 adapter schema 的继续修补.",
        "- `H_clash` 未进入 DiffSBDD 生成过程, 碰撞信息只在后验 verifier 中使用.",
        ]
    )
    (report_root / "diffsbdd_center_sensitivity.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return rows


def _write_rule_backend_diagnostic(report_root: Path, data: dict[str, object]) -> dict[str, object]:
    selected = {row["case_id"]: row for row in data["selected_cases"]}  # type: ignore[index]
    verifier = [
        row
        for row in data["verifier_outcome"]  # type: ignore[index]
        if row["backend_name"] == "rule_fixed_topology"
    ]
    comparison = _comparison_by_backend(data, "rule_fixed_topology")
    reliable_cases = {row["case_id"] for row in verifier if _is_true(row["reliable_repair_success"])}

    injection_rows = _stratified_success_rows(selected, reliable_cases, "injection_mode")
    difficulty_rows = _stratified_success_rows(selected, reliable_cases, "difficulty_bin")

    md = [
        "# Rule Backend Diagnostic",
        "",
        "## 1. Role",
        "",
        "`rule_fixed_topology` 是固定拓扑局部构象搜索. 它保留原分子拓扑和 atom order, 通过 anchor axis rotation 和内部 torsion proposal 在参考掩码区域内搜索可逆构象.",
        "",
        "它的阶段 4.0 定位是构象型强基线和可逆性 sanity check, 不是生成式局部修复主方法.",
        "",
        "## 2. Why 38/40 Is Plausible",
        "",
        "- 阶段 2 人工失败样本由 `easy_rotation`, `torsion_perturb`, `directed_clash` 等受控局部扰动构造.",
        "- 规则型后端的搜索空间与上述构造方式高度相关, 因而能把大量局部碰撞恢复到无旧严重碰撞且无新严重碰撞的构象.",
        "- same-topology 候选天然更容易满足 fixed structure match, keep region stable 和 anchor integrity.",
        "",
        "## 3. Why It Is Not A Generative Main Method",
        "",
        "- 它不生成新片段, 不改变取代基组成, 也不学习生成式修复策略.",
        "- 它与阶段 2 的人工扰动方式同源, 因此高成功率不能外推为生成式局部补全已经完成.",
        "- 后续生成式主线仍应围绕 DiffSBDD conditional adapter, DiffDec adapter 或新的局部生成基座模型继续修补.",
        "",
        "## 4. Proposal Cost",
        "",
        f"- selected case denominator: {comparison['selected_case_denominator']}.",
        f"- proposal_count_sum: {comparison['proposal_count_sum']}.",
        f"- candidate_count_sum: {comparison['candidate_count_sum']}.",
        f"- reliable_candidate_success_count: {comparison['reliable_candidate_success_count']}.",
        f"- sample_reliable_success_count: {comparison['sample_reliable_success_count']}.",
        "- 每个 case 最多保留 K=8 个候选, 但内部 proposal search 成本不能被 K=8 掩盖. 本次内部 proposal_count_sum = 1200, 最终候选数 = 320.",
        "",
        "## 5. Stratified Sample Success",
        "",
        "### 5.1 By Injection Mode",
        "",
        _markdown_table(injection_rows, ["group", "selected_cases", "reliable_cases", "sample_success_rate"]),
        "",
        "### 5.2 By Difficulty Bin",
        "",
        _markdown_table(difficulty_rows, ["group", "selected_cases", "reliable_cases", "sample_success_rate"]),
        "",
        "## 6. Report Wording",
        "",
        "最终报告应写成: `rule_fixed_topology` 证明当前受控人工局部碰撞样本存在大量构象可逆失败, 适合作为 sanity check 和强基线. 不应写成生成式局部修复主线已经完成, 也不建议直接把它作为阶段 4.1 生成式主方法.",
    ]
    (report_root / "rule_backend_diagnostic.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {
        "comparison": comparison,
        "injection_rows": injection_rows,
        "difficulty_rows": difficulty_rows,
    }


def _write_diffdec_failure_analysis(report_root: Path, run_root: Path, data: dict[str, object]) -> dict[str, object]:
    backend = "diffdec_single_rgroup"
    candidate_rows = [row for row in data["candidate_manifest"] if row["backend_name"] == backend]  # type: ignore[index]
    verifier = [row for row in data["verifier_outcome"] if row["backend_name"] == backend]  # type: ignore[index]
    attempts = _attempt_rows(candidate_rows)
    generated_candidates = sum(_to_int(row["candidate_count"]) for row in attempts.values())
    execution_failures = len({row["attempt_id"] for row in attempts.values() if row["failure_stage"] == "execution"})
    unsupported = _extract_unsupported_atoms(run_root / "diffdec_single_rgroup")

    metric_rows = [
        _metric("attempts", len(attempts), len(attempts), "DiffDec formal attempts."),
        _metric("execution_failures", execution_failures, len(attempts), "Execution-level failures before candidates."),
        _metric("generated_candidates", generated_candidates, generated_candidates, "Candidates emitted by attempts."),
        _metric("readable_candidates", _count_true(verifier, "candidate_readable"), generated_candidates, ""),
        _metric("ligand_valid", _count_true(verifier, "ligand_valid"), generated_candidates, ""),
        _metric(
            "fixed_structure_match_success",
            _count_true(verifier, "fixed_structure_match_success"),
            generated_candidates,
            "",
        ),
        _metric("anchor_integrity_success", _count_true(verifier, "anchor_integrity"), generated_candidates, ""),
        _metric(
            "generated_atom_count_mismatch",
            _count_contains(verifier, "failure_reason", "generated_atom_count_mismatch"),
            generated_candidates,
            "Adapter mapping failure reason.",
        ),
        _metric(
            "generated_atom_element_mismatch",
            _count_contains(verifier, "failure_reason", "generated_atom_element_mismatch"),
            generated_candidates,
            "Adapter mapping failure reason.",
        ),
        _metric("old_clash_resolved", _count_true(verifier, "old_clash_resolved"), generated_candidates, ""),
        _metric("no_new_severe_clash", _count_true(verifier, "no_new_severe_clash"), generated_candidates, ""),
        _metric("scaffold_stable", _count_true(verifier, "scaffold_stable"), generated_candidates, ""),
        _metric("keep_region_stable", _count_true(verifier, "keep_region_stable"), generated_candidates, ""),
        _metric("edit_compliance", _count_true(verifier, "edit_compliance"), generated_candidates, ""),
        _metric("pocket_retention", _count_true(verifier, "pocket_retention"), generated_candidates, ""),
        _metric("reliable_success", _count_true(verifier, "reliable_repair_success"), generated_candidates, ""),
    ]
    _write_csv(report_root / "diffdec_failure_funnel.csv", metric_rows)

    top_failure = _top_reasons((row["failure_reason"] for row in verifier if row["failure_reason"]), limit=12)
    top_verifier = _top_reasons(
        (_split_reason_items(row["verifier_failure_reasons"]) for row in verifier),
        limit=8,
    )
    unsupported_text = ", ".join(f"{key}={value}" for key, value in sorted(unsupported.items())) or "NA"

    md = [
        "# DiffDec Failure Analysis",
        "",
        "## 1. Scope",
        "",
        "- 本报告只读取已有 `candidate_manifest.csv`, `adapter_input_manifest.csv`, `verifier_outcome.csv`, `failure_cases.csv` 和 DiffDec 运行日志.",
        "- 未重新调用 DiffDec, 未生成新候选, 未修改 `external/DiffDec` 源码或 denoising/sampling 过程.",
        "",
        "## 2. Failure Funnel",
        "",
        _markdown_table(metric_rows, ["metric", "count", "denominator", "rate", "notes"]),
        "",
        "## 3. Top Failure Reasons",
        "",
        f"- top `failure_reason`: {top_failure or 'NA'}.",
        f"- top `verifier_failure_reasons`: {top_verifier or 'NA'}.",
        f"- unsupported protein atom elements recovered from logs: {unsupported_text}.",
        "",
        "## 4. Interpretation",
        "",
        "DiffDec 当前不是环境阻塞. `model_inventory.csv` 显示环境和 checkpoint 已 ready, formal run 已使用 GPU 执行. 当前 0 reliable success 更应解释为输入适配, anchor/scaffold 匹配, candidate mapping 和 generated R-group size 控制尚未解决.",
        "",
        "`CL` protein atom vocabulary 问题确实存在, 本次日志中对应 `case_002599` 的 `KeyError: 'CL'`, 但它只解释 1 个 execution failure. 其余 39 个 attempt 已生成候选并进入 verifier, 因此不能把 0 reliable success 简单归因于 protein atom vocabulary.",
        "",
        "后续优先级建议:",
        "",
        "- 先审计 `fixed_context.sdf` 和带星号出口 scaffold smiles 是否和 phase4 anchor 一致.",
        "- 再修 generated R-group size / atom count 与 oracle mask size 的映射策略.",
        "- 同步检查候选回填到原 ligand atom order 的 adapter, 尤其是 generated atom element mismatch 和 count mismatch.",
        "- 最后修补 protein atom vocabulary, 包括 `CL` 等非标准或大写元素兼容.",
    ]
    (report_root / "diffdec_failure_analysis.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {
        "metric_rows": metric_rows,
        "top_failure": top_failure,
        "top_verifier": top_verifier,
        "unsupported": unsupported,
    }


def _write_full_resampling_analysis(report_root: Path, data: dict[str, object]) -> dict[str, object]:
    backend = "diffsbdd_full_resampling"
    verifier = [row for row in data["verifier_outcome"] if row["backend_name"] == backend]  # type: ignore[index]
    comparison = _comparison_by_backend(data, backend)
    candidate_count = _to_int(comparison["candidate_count_sum"])
    metric = {
        "backend_name": backend,
        "candidate_denominator": str(candidate_count),
        "candidate_readable_rate": _rate(_count_true(verifier, "candidate_readable"), candidate_count),
        "ligand_valid_rate": _rate(_count_true(verifier, "ligand_valid"), candidate_count),
        "pocket_retention_rate": _rate(_count_true(verifier, "pocket_retention"), candidate_count),
        "no_new_severe_clash_rate": _rate(_count_true(verifier, "no_new_severe_clash"), candidate_count),
        "fixed_structure_match_rate": _rate(_count_true(verifier, "fixed_structure_match_success"), candidate_count),
        "anchor_integrity_rate": _rate(_count_true(verifier, "anchor_integrity"), candidate_count),
        "reliable_local_repair_success_count": str(_count_true(verifier, "reliable_repair_success")),
    }
    _write_csv(report_root / "full_resampling_global_control_metrics.csv", [metric])

    md = [
        "# DiffSBDD Full Resampling Control Analysis",
        "",
        "## 1. Role",
        "",
        "`diffsbdd_full_resampling` 是全配体重采样对照, 不是局部修复后端.",
        "",
        "## 2. Why Local Repair Success Is Zero",
        "",
        "- full resampling 不使用局部 reference mask.",
        "- full resampling 不固定 keep region.",
        "- full resampling 不保证 scaffold, anchor 或原 atom order 保留.",
        "- 因此在阶段 4.0 的 reliable local repair 标准下, 0 reliable local repair success 是合理结果.",
        "",
        "## 3. Global Control Metrics",
        "",
        _markdown_table([metric], list(metric.keys())),
        "",
        "## 4. Follow-Up",
        "",
        "该后端只能作为“直接重新生成完整配体”的全局对照. 它不应进入阶段 4.1 的 Random / Predicted / Oracle 局部掩码组, 也不应被写成局部 mask repair 的成功后端.",
    ]
    (report_root / "full_resampling_control_analysis.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"comparison": comparison, "metric": metric}


def _write_closeout_audit(
    report_root: Path,
    repo_root: Path,
    data: dict[str, object],
    *,
    backend_rates: list[dict[str, str]],
    center_rows: list[dict[str, str]],
    rule_sections: dict[str, object],
    diffdec_sections: dict[str, object],
    full_sections: dict[str, object],
) -> None:
    summary = data["summary"]  # type: ignore[assignment]
    git_status = _git(["status", "--short"], repo_root)
    git_branch = _git(["branch", "--show-current"], repo_root)
    git_head = _git(["rev-parse", "HEAD"], repo_root)
    inventory = {row["backend_name"]: row for row in data["model_inventory"]}  # type: ignore[index]

    md = [
        "# Phase 4.0 Closeout Patch Audit",
        "",
        "## 1. Repository Check",
        "",
        f"- `git status --short`: `{git_status or 'clean'}`.",
        f"- `git branch --show-current`: `{git_branch}`.",
        f"- `git rev-parse HEAD`: `{git_head}`.",
        "",
        "## 2. Closeout Scope",
        "",
        "- 阶段 4.0 主实验是否完成: 是.",
        "- 是否需要重跑 40 case: 否.",
        "- 是否需要补跑主后端: 否.",
        "- DiffSBDD joint blocked 是否影响最终报告: 否, 它是 backend feasibility audit 的真实结论.",
        "- 是否需要生成式后端继续修补: 是, 作为后续阶段.",
        "- 是否可以进入 `phase4_0_final_experiment_report.md` 生成: yes.",
        "",
        "## 3. Reliable Repair Candidate Definition",
        "",
        "可靠修复候选必须同时满足以下 10 项标准:",
        "",
    ]
    md.extend(f"- `{field}`." for field in RELIABLE_REPAIR_FIELDS)
    md.extend(
        [
            "",
            "这意味着:",
            "",
            "- 不是“生成出来”就算成功.",
            "- 不是“没有新碰撞”就算成功.",
            "- 必须旧碰撞消除, 无新严重碰撞, 局部结构保持, 连接点合理, 候选合法, 且仍在口袋中.",
            "- 对 DiffSBDD / DiffDec 等可能改变拓扑或原子顺序的后端, `fixed_structure_match_success=true` 是进入可靠成功的必要条件.",
            "",
            "## 4. Existing Result Contract",
            "",
            f"- mode: `{summary['mode']}`.",
            f"- selected_case_count: {summary['selected_case_count']}.",
            f"- formal_40_case_results_generated: {summary['formal_40_case_results_generated']}.",
            f"- training_or_finetuning_performed: {summary['training_or_finetuning_performed']}.",
            f"- h_clash_used_in_diffsbdd_generation: {summary['h_clash_used_in_diffsbdd_generation']}.",
            f"- phase4_mask_seed_unchanged: {summary['phase4_mask_seed_unchanged']}.",
            "",
            "## 5. Backend Wording For Final Report",
            "",
            "- `rule_fixed_topology`: 构象型强基线和可逆性 sanity check. 38/40 case 成功证明当前受控人工局部碰撞样本存在大量构象可逆失败, 但不能写成生成式局部修复主方法.",
            "- `diffsbdd_conditional_inpainting`: 生成式局部补全有非零可靠修复结果, 是当前最值得继续修补的生成式局部补全后端.",
            "- `diffdec_single_rgroup`: 环境, checkpoint 和 GPU formal run 已跑通, 但 0 reliable success. 主要问题是输入适配, anchor/scaffold 匹配, candidate mapping 和 generated R-group size 控制; `CL` vocabulary 只解释 1 个 execution failure.",
            "- `diffsbdd_full_resampling`: 只能作为全配体重采样对照, 不能作为局部修复后端.",
            "- `diffsbdd_joint_inpainting`: 当前 blocked, 不需要先修 joint 再出阶段 4.0 最终报告.",
            "",
            "## 6. Backend Rates",
            "",
            _markdown_table(
                backend_rates,
                [
                    "backend_name",
                    "selected_case_denominator",
                    "failure_attempt_rate",
                    "reliable_candidate_rate",
                    "sample_reliable_repair_yield",
                    "proposal_per_case_mean",
                    "cost_per_reliable_case",
                ],
            ),
            "",
            "## 7. DiffSBDD Center Sensitivity",
            "",
            _markdown_table(
                center_rows,
                [
                    "center",
                    "attempt_rows",
                    "candidate_count",
                    "execution_failure_count",
                    "reliable_candidate_success_count",
                    "sample_reliable_success_count",
                ],
            ),
            "",
            "- center-level sample counts are not additive because the same case can succeed under both centers.",
            "",
            "## 8. Blocked Backends",
            "",
            f"- `diffsbdd_joint_inpainting`: status `{inventory['diffsbdd_joint_inpainting']['status']}`, blocked_reason `{inventory['diffsbdd_joint_inpainting']['blocked_reason']}`.",
            "",
            "## 9. New Closeout Patch Outputs",
            "",
        ]
    )
    md.extend(f"- `reports/phase4_0_backend_feasibility/{name}`." for name in REPORT_FILES if name != "phase4_0_closeout_patch_audit.md")
    md.extend(
        [
            "- `reports/phase4_0_backend_feasibility/phase4_0_closeout_patch_audit.md`.",
            "",
            "## 10. Follow-Up Recommendation",
            "",
            "- 可以进入 `phase4_0_final_experiment_report.md` 生成.",
            "- 不建议直接以 `rule_fixed_topology` 作为生成式主线进入正式阶段 4.1.",
            "- 建议新增阶段 4.0.1 或 4.0.5, 聚焦 DiffSBDD conditional adapter / anchor-aware filtering 修补和 DiffDec adapter 修补.",
            "- 若要做 `phase4.1-rule-mini`, 只能作为规则型 sanity check, 不作为生成式修复主结果.",
            "- 阶段 4.1 的 Random / Predicted / Oracle 正式掩码对照需要另行制定方案.",
            "",
            "## 11. Validation Status",
            "",
            "- 本收尾脚本只读取既有结果文件并写出派生报告, 未调用任何 repair backend.",
            "- 本文件生成后需要运行 `conda run -n c2f_cpu python -m compileall src scripts`.",
            "- 本文件生成后需要运行 `conda run -n c2f_cpu python -m pytest tests/test_phase4_backend_feasibility.py -q`.",
            "- 本文件生成后需要运行 `conda run -n c2f_cpu python -m pytest -q`.",
            "",
            "## 12. Guardrail Statement",
            "",
            "- 本次补丁不修改阶段 2 / 2.5 / 3 历史结果.",
            "- 本次补丁不覆盖 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.",
            "- 本次补丁不提交 `external/DiffSBDD`, `external/DiffDec`, checkpoint, 大量候选 SDF 或日志缓存.",
            "- 本次补丁不生成 `phase4_0_final_experiment_report.md`.",
        ]
    )
    (report_root / "phase4_0_closeout_patch_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _comparison_by_backend(data: dict[str, object], backend_name: str) -> dict[str, str]:
    for row in data["backend_comparison"]:  # type: ignore[index]
        if row["backend_name"] == backend_name:
            return row
    raise KeyError(backend_name)


def _attempt_rows(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    attempts: dict[str, dict[str, str]] = {}
    for row in rows:
        attempts[row["attempt_id"]] = row
    return attempts


def _extract_center(row: dict[str, str]) -> str:
    metadata = row.get("generation_metadata", "")
    if metadata:
        try:
            center = json.loads(metadata).get("center")
            if center:
                return str(center)
        except json.JSONDecodeError:
            pass
    source = row.get("candidate_source", "")
    if "center_ligand" in source:
        return "ligand"
    if "center_pocket" in source:
        return "pocket"
    if "center_full_ligand" in source:
        return "full_ligand"
    attempt = row.get("attempt_id", "")
    parts = attempt.split(":")
    if len(parts) >= 3 and parts[1] in {"ligand", "pocket"}:
        return parts[1]
    return row.get("center", "") or "unknown"


def _stratified_success_rows(
    selected: dict[str, dict[str, str]], reliable_cases: set[str], field: str
) -> list[dict[str, str]]:
    totals: Counter[str] = Counter(row[field] for row in selected.values())
    successes: Counter[str] = Counter(selected[case_id][field] for case_id in reliable_cases if case_id in selected)
    rows = []
    for group in sorted(totals):
        rows.append(
            {
                "group": group,
                "selected_cases": str(totals[group]),
                "reliable_cases": str(successes[group]),
                "sample_success_rate": _rate(successes[group], totals[group]),
            }
        )
    return rows


def _extract_unsupported_atoms(diffdec_run_root: Path) -> Counter[str]:
    counter: Counter[str] = Counter()
    if not diffdec_run_root.exists():
        return counter
    pattern = re.compile(r"KeyError: '([^']+)'")
    for log_path in diffdec_run_root.glob("**/*.log"):
        text = log_path.read_text(encoding="utf-8", errors="replace")
        for match in pattern.finditer(text):
            counter[match.group(1)] += 1
    return counter


def _top_reasons(values: Iterable[str] | Iterable[Iterable[str]], limit: int = 5) -> str:
    counter: Counter[str] = Counter()
    for value in values:
        if isinstance(value, str):
            items = [value]
        else:
            items = list(value)
        for item in items:
            if item:
                counter[item] += 1
    return "; ".join(f"{reason} ({count})" for reason, count in counter.most_common(limit))


def _split_reason_items(value: str) -> list[str]:
    if not value:
        return []
    return [item for item in value.split(";") if item]


def _metric(metric: str, count: int, denominator: int, notes: str) -> dict[str, str]:
    return {
        "metric": metric,
        "count": str(count),
        "denominator": str(denominator),
        "rate": _rate(count, denominator),
        "notes": notes,
    }


def _count_true(rows: Iterable[dict[str, str]], field: str) -> int:
    return sum(1 for row in rows if _is_true(row.get(field, "")))


def _count_contains(rows: Iterable[dict[str, str]], field: str, pattern: str) -> int:
    return sum(1 for row in rows if pattern in row.get(field, ""))


def _is_true(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _to_int(value: str | int | float) -> int:
    if value == "":
        return 0
    return int(float(value))


def _rate(count: int, denominator: int) -> str:
    if denominator <= 0:
        return "NA"
    return f"{count / denominator:.6f}"


def _mean(total: int, denominator: int) -> str:
    if denominator <= 0:
        return "NA"
    return f"{total / denominator:.6f}"


def _markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    if not rows:
        return "NA"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def _git(args: list[str], repo_root: Path) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, check=True, text=True, capture_output=True)
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
