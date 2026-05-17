from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from shutil import which
from typing import Any, Iterable

import numpy as np
import pandas as pd

from clash2feedback.data.render_visual_check import (
    DEFAULT_CANDIDATE_DIRECTIONS,
    CameraView,
    select_clear_camera_views,
)
from clash2feedback.geometry.vdw import get_vdw_radius
from clash2feedback.repair.phase4_inputs import Phase4CaseInput, load_phase4_case_inputs, read_first_mol
from clash2feedback.utils.config import resolve_repo_path
from clash2feedback.utils.files import ensure_dir


VISUAL_QC_VIEWS = (
    "reconnect_clash",
    "reconnect_anchor_topology",
    "reconnect_before_after_overlay",
)

CONTACT_SHEET_NAMES = {
    "reconnect_clash": "reconnect_clash_contact_sheet.png",
    "reconnect_anchor_topology": "reconnect_anchor_topology_contact_sheet.png",
    "reconnect_before_after_overlay": "reconnect_before_after_overlay_contact_sheet.png",
}

VIEW_SELECTION = {
    "reconnect_clash": ("clash", "candidate"),
    "reconnect_anchor_topology": ("rgroup", "candidate"),
    "reconnect_before_after_overlay": ("ligand", "overlay_union"),
}

DEFAULT_LABELS = (
    "looks_single_anchor_connected",
    "looks_disconnected",
    "looks_floating_fragment",
    "looks_multi_attachment",
    "looks_possible_linker_or_bridge",
    "looks_mapping_uncertain",
    "looks_chemically_invalid",
    "needs_further_review",
)


@dataclass(frozen=True)
class VisualQCRenderTask:
    visual_case_id: str
    case_id: str
    candidate_id: str
    sampling_group: str
    view: str
    case_dir: Path
    script_path: Path
    cameras: tuple[CameraView, ...]
    candidate_directions: int


def run_phase4_0_1a_visual_qc(config: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    inputs = {key: resolve_repo_path(value, repo_root=repo_root) for key, value in config.get("inputs", {}).items()}
    outputs = {key: resolve_repo_path(value, repo_root=repo_root) for key, value in config.get("outputs", {}).items()}
    sampling_cfg = config.get("sampling", {})
    render_cfg = config.get("render", {})
    _validate_paths(inputs)

    report_root = ensure_dir(outputs["report_root"])
    run_root = ensure_dir(outputs["run_root"])

    diffsbdd = pd.read_csv(inputs["diffsbdd_reclassified"])
    clean = pd.read_csv(inputs["clean_positive"])
    rule = pd.read_csv(inputs["rule_positive"])
    selected_cases = pd.read_csv(inputs["selected_cases"])
    case_inputs = load_phase4_case_inputs(
        selected_cases,
        phase2_manifest_path=inputs["phase2_manifest"],
        phase2_benchmark_root=inputs["phase2_benchmark_root"],
        processed_root=inputs["processed_root"],
    )
    case_by_id = {case.case_id: case for case in case_inputs}

    cases = select_visual_qc_cases(
        clean=clean,
        rule=rule,
        diffsbdd=diffsbdd,
        quotas=sampling_cfg.get("quotas", {}),
        seed=int(config.get("seed", 20260517)),
    )
    cases = _attach_visual_paths(cases, run_root=run_root)

    tasks = build_visual_qc_assets_and_tasks(
        cases,
        case_by_id=case_by_id,
        run_root=run_root,
        num_clear_views=int(render_cfg.get("num_clear_views", 12)),
        candidate_directions=int(render_cfg.get("candidate_directions", DEFAULT_CANDIDATE_DIRECTIONS)),
        close_contact_overlap_threshold_angstrom=float(render_cfg.get("close_contact_overlap_threshold_angstrom", 0.0)),
    )
    render_manifest = render_visual_qc_tasks(
        tasks,
        chimerax=str(render_cfg.get("chimerax", "chimerax")),
        dry_run=bool(render_cfg.get("dry_run", False)),
        skip_existing=bool(render_cfg.get("skip_existing", False)),
        width=int(render_cfg.get("width", 1200)),
        height=int(render_cfg.get("height", 900)),
        timeout_seconds=int(render_cfg.get("timeout_seconds", 240)),
    )
    contact_sheets = (
        pd.DataFrame(columns=_contact_sheet_columns())
        if bool(render_cfg.get("dry_run", False)) or bool(render_cfg.get("no_contact_sheets", False))
        else write_visual_qc_contact_sheets(render_manifest)
    )
    cases = _merge_contact_sheet_paths(cases, contact_sheets)
    cases = _merge_camera_quality(cases, render_manifest, contact_sheets)
    manual_template = build_manual_review_template(cases)
    summary = build_visual_qc_summary(
        config=config,
        repo_root=repo_root,
        cases=cases,
        render_manifest=render_manifest,
        contact_sheets=contact_sheets,
    )

    paths = {
        "cases": report_root / "visual_qc_reconnect_cases.csv",
        "render_manifest": report_root / "visual_qc_render_manifest.csv",
        "contact_sheets": report_root / "visual_qc_contact_sheets.csv",
        "manual_review_template": report_root / "manual_review_template.csv",
        "summary": report_root / "phase4_0_1a_visual_qc_summary.json",
        "notes": report_root / "visual_qc_reconnect_notes.md",
        "expt_report": outputs["expt_report"],
    }
    cases.to_csv(paths["cases"], index=False)
    render_manifest.to_csv(paths["render_manifest"], index=False)
    contact_sheets.to_csv(paths["contact_sheets"], index=False)
    manual_template.to_csv(paths["manual_review_template"], index=False)
    paths["summary"].write_text(json.dumps(_jsonable(summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["notes"].write_text(visual_qc_notes_markdown(cases, summary), encoding="utf-8")
    paths["expt_report"].parent.mkdir(parents=True, exist_ok=True)
    paths["expt_report"].write_text(visual_qc_expt_report_markdown(cases, summary), encoding="utf-8")
    return {"summary": summary, "report_paths": paths}


def select_visual_qc_cases(
    *,
    clean: pd.DataFrame,
    rule: pd.DataFrame,
    diffsbdd: pd.DataFrame,
    quotas: dict[str, Any],
    seed: int,
) -> pd.DataFrame:
    requested = {
        "clean_positive": int(quotas.get("clean_positive", 3)),
        "rule_positive": int(quotas.get("rule_positive", 3)),
        "diffsbdd_invalid_non_reliable": int(quotas.get("diffsbdd_invalid_non_reliable", 6)),
        "diffsbdd_multi_non_reliable": int(quotas.get("diffsbdd_multi_non_reliable", 6)),
        "diffsbdd_reliable_strict_shadow_fail": int(quotas.get("diffsbdd_reliable_strict_shadow_fail", 7)),
    }
    selected: list[pd.DataFrame] = []
    used_candidate_ids: set[str] = set()

    reliable_pool = diffsbdd[
        _bool_series(diffsbdd, "reliable_repair_success")
        & ~_bool_series(diffsbdd, "strict_single_anchor_shadow_reliable")
        & _renderable_series(diffsbdd)
    ].copy()
    reliable = _pick_diverse(reliable_pool, requested["diffsbdd_reliable_strict_shadow_fail"], seed=seed)
    selected.append(_tag_sampling_group(reliable, "diffsbdd_reliable_strict_shadow_fail", "original reliable_repair_success=True but strict_single_anchor_shadow_reliable=False"))
    used_candidate_ids.update(reliable["candidate_id"].astype(str))

    invalid_pool = diffsbdd[
        (diffsbdd["reconnect_category"].astype(str) == "invalid_reconnect")
        & ~_bool_series(diffsbdd, "reliable_repair_success")
        & _renderable_series(diffsbdd)
        & ~diffsbdd["candidate_id"].astype(str).isin(used_candidate_ids)
    ].copy()
    invalid = _pick_diverse(invalid_pool, requested["diffsbdd_invalid_non_reliable"], seed=seed + 1)
    selected.append(_tag_sampling_group(invalid, "diffsbdd_invalid_non_reliable", "DiffSBDD invalid_reconnect non reliable renderable candidate"))
    used_candidate_ids.update(invalid["candidate_id"].astype(str))

    multi_pool = diffsbdd[
        (diffsbdd["reconnect_category"].astype(str) == "multi_attachment_out_of_scope")
        & ~_bool_series(diffsbdd, "reliable_repair_success")
        & _renderable_series(diffsbdd)
        & ~diffsbdd["candidate_id"].astype(str).isin(used_candidate_ids)
    ].copy()
    multi = _pick_diverse(multi_pool, requested["diffsbdd_multi_non_reliable"], seed=seed + 2)
    selected.append(_tag_sampling_group(multi, "diffsbdd_multi_non_reliable", "DiffSBDD multi_attachment_out_of_scope non reliable renderable candidate"))
    used_candidate_ids.update(multi["candidate_id"].astype(str))

    clean_pool = clean[_renderable_series(clean)].copy()
    clean_pick = _pick_diverse(clean_pool, requested["clean_positive"], seed=seed + 3)
    selected.append(_tag_sampling_group(clean_pick, "clean_positive", "original clean ligand positive reconnect sanity case"))
    used_candidate_ids.update(clean_pick["candidate_id"].astype(str))

    rule_pool = rule[_renderable_series(rule)].copy()
    rule_pick = _pick_diverse(rule_pool, requested["rule_positive"], seed=seed + 4)
    selected.append(_tag_sampling_group(rule_pick, "rule_positive", "rule_fixed_topology reliable positive reconnect sanity case"))

    result = pd.concat(selected, ignore_index=True, sort=False)
    result.insert(0, "visual_case_id", [f"vqc_{idx:03d}" for idx in range(1, len(result) + 1)])
    result["duplicate_of"] = ""
    result["fallback_reason"] = result.apply(_fallback_reason, axis=1)
    result["needs_user_review"] = True
    result["manual_visual_label"] = "pending_codex_visual_review"
    result["manual_visual_confidence"] = "pending"
    result["manual_notes"] = ""
    return result


def build_visual_qc_assets_and_tasks(
    cases: pd.DataFrame,
    *,
    case_by_id: dict[str, Phase4CaseInput],
    run_root: Path,
    num_clear_views: int,
    candidate_directions: int,
    close_contact_overlap_threshold_angstrom: float,
) -> list[VisualQCRenderTask]:
    tasks: list[VisualQCRenderTask] = []
    for _, row in cases.iterrows():
        case_id = str(row["case_id"])
        if case_id not in case_by_id:
            raise ValueError(f"visual QC case missing Phase4CaseInput: {case_id}")
        case_input = case_by_id[case_id]
        case_dir = Path(row["case_dir"])
        ensure_dir(case_dir / "images")
        ensure_dir(case_dir / "scripts")
        _write_case_assets(
            row.to_dict(),
            case_input=case_input,
            case_dir=case_dir,
            close_contact_overlap_threshold_angstrom=close_contact_overlap_threshold_angstrom,
        )
        tasks.extend(
            _build_render_tasks_for_case(
                row.to_dict(),
                case_dir=case_dir,
                num_clear_views=num_clear_views,
                candidate_directions=candidate_directions,
            )
        )
    return tasks


def render_visual_qc_tasks(
    tasks: Iterable[VisualQCRenderTask],
    *,
    chimerax: str,
    dry_run: bool,
    skip_existing: bool,
    width: int,
    height: int,
    timeout_seconds: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    executable = which(chimerax) or chimerax
    for task in tasks:
        if dry_run:
            _write_group_script(task, width=width, height=height)
            rows.extend(_render_rows(task, status="script_written", render_action="dry_run"))
            continue
        if skip_existing and _task_images_exist(task):
            rows.extend(_render_rows(task, status="rendered", render_action="skipped_existing", returncode=0))
            continue
        _write_group_script(task, width=width, height=height)
        command = [executable, "--nogui", "--offscreen", "--script", task.script_path.relative_to(task.case_dir).as_posix(), "--exit"]
        try:
            completed = subprocess.run(
                command,
                cwd=task.case_dir,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            returncode = int(completed.returncode)
            stderr_tail = _tail(completed.stderr or completed.stdout)
            status = "rendered" if returncode == 0 else "failed"
        except subprocess.TimeoutExpired as exc:
            returncode = None
            stderr_tail = str(exc)
            status = "timeout"
        rows.extend(_render_rows(task, status=status, render_action="chimerax_render", returncode=returncode, stderr_tail=stderr_tail))
    return pd.DataFrame(rows, columns=_render_manifest_columns())


def write_visual_qc_contact_sheets(render_manifest: pd.DataFrame, *, rows: int = 3, columns: int = 4) -> pd.DataFrame:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:  # pragma: no cover - optional image stack.
        return pd.DataFrame(
            [
                {
                    "visual_case_id": "",
                    "case_id": "",
                    "candidate_id": "",
                    "sampling_group": "",
                    "view": "",
                    "contact_sheet_path": "",
                    "status": f"pillow_unavailable:{exc}",
                    "num_images": 0,
                    "rows": rows,
                    "columns": columns,
                }
            ],
            columns=_contact_sheet_columns(),
        )

    rendered = render_manifest[render_manifest["status"] == "rendered"].copy()
    sheet_rows: list[dict[str, Any]] = []
    for (visual_case_id, view), group in rendered.groupby(["visual_case_id", "view"], sort=True):
        ordered = group.sort_values("angle").head(rows * columns)
        image_paths = [Path(path) for path in ordered["image_path"]]
        images = [Image.open(path).convert("RGB") for path in image_paths if path.exists()]
        if not images:
            first = group.iloc[0]
            sheet_rows.append(
                _contact_sheet_row(first, view=view, status="no_images", sheet_path="", num_images=0, rows=rows, columns=columns)
            )
            continue
        thumb_w, thumb_h = 420, 315
        tile_w, tile_h = 460, 365
        legend_h = 82
        sheet = Image.new("RGB", (columns * tile_w, rows * tile_h + legend_h), "white")
        draw = ImageDraw.Draw(sheet)
        font = _load_font(size=13)
        title_font = _load_font(size=16)
        _draw_legend(sheet, view, title_font=title_font, font=font)
        for idx, image in enumerate(images[: rows * columns]):
            image = _crop_white_border(image)
            image.thumbnail((thumb_w, thumb_h))
            tile = Image.new("RGB", (tile_w, tile_h), "white")
            tile.paste(image, ((tile_w - image.width) // 2, 34))
            tile_draw = ImageDraw.Draw(tile)
            tile_draw.text((12, 10), image_paths[idx].stem, fill=(0, 0, 0), font=font)
            sheet.paste(tile, ((idx % columns) * tile_w, legend_h + (idx // columns) * tile_h))
        case_dir = image_paths[0].parents[1]
        sheet_path = case_dir / "images" / CONTACT_SHEET_NAMES[view]
        sheet.save(sheet_path)
        first = group.iloc[0]
        sheet_rows.append(_contact_sheet_row(first, view=view, status="written", sheet_path=str(sheet_path), num_images=len(images), rows=rows, columns=columns))
    return pd.DataFrame(sheet_rows, columns=_contact_sheet_columns())


def build_manual_review_template(cases: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "visual_case_id",
        "case_id",
        "candidate_id",
        "candidate_path",
        "source_group",
        "sampling_group",
        "reconnect_category",
        "reconnect_category_reason",
        "clash_contact_sheet_path",
        "anchor_topology_contact_sheet_path",
        "before_after_overlay_contact_sheet_path",
        "manual_visual_label",
        "manual_visual_confidence",
        "manual_notes",
        "needs_user_review",
    ]
    template = cases.copy()
    for column in columns:
        if column not in template:
            template[column] = ""
    return template[columns]


def build_visual_qc_summary(
    *,
    config: dict[str, Any],
    repo_root: Path,
    cases: pd.DataFrame,
    render_manifest: pd.DataFrame,
    contact_sheets: pd.DataFrame,
) -> dict[str, Any]:
    render_status = render_manifest["status"].value_counts(dropna=False).to_dict() if not render_manifest.empty else {}
    sheet_status = contact_sheets["status"].value_counts(dropna=False).to_dict() if not contact_sheets.empty else {}
    quality_counts = _quality_counts(cases)
    return {
        "schema_version": config.get("schema_version", "phase4_0_1a_visual_qc_v0_1"),
        "mode": "visual_qc_closeout_report_only",
        "status": "completed" if not any(status in render_status for status in {"failed", "timeout", "missing_image"}) else "completed_with_render_failures",
        "git_branch": _git_output(repo_root, ["git", "branch", "--show-current"]),
        "git_head": _git_output(repo_root, ["git", "rev-parse", "HEAD"]),
        "git_status_short": _git_output(repo_root, ["git", "status", "--short", "--branch"]),
        "rerun_diffsbdd": False,
        "regenerate_candidates": False,
        "training_or_finetuning_performed": False,
        "modify_reliable_repair_fields": False,
        "local_reconnect_enters_reliable_repair_standard": False,
        "multi_attachment_is_ligand_invalid": False,
        "final_report_generated": False,
        "sample_count": int(cases.shape[0]),
        "sampling_group_counts": cases["sampling_group"].value_counts(dropna=False).to_dict(),
        "reconnect_category_counts": cases["reconnect_category"].value_counts(dropna=False).to_dict(),
        "render_task_count": int(render_manifest.shape[0]),
        "render_status_counts": render_status,
        "contact_sheet_count": int(contact_sheets.shape[0]),
        "contact_sheet_status_counts": sheet_status,
        "camera_quality_counts": quality_counts,
        "camera_retry_count_total": int(_numeric_sum(cases, ["camera_retry_count_clash", "camera_retry_count_anchor_topology", "camera_retry_count_before_after_overlay"])),
        "codex_image_review_status": "pending_codex_visual_review",
    }


def visual_qc_notes_markdown(cases: pd.DataFrame, summary: dict[str, Any]) -> str:
    lines = [
        "# Phase 4.0.1a Visual QC Reconnect Notes",
        "",
        "## 1. Scope",
        "",
        "- 本文件索引 25 个 visual QC 样本的 contact sheets 和人工/Codex 检视字段.",
        "- visual QC 是阶段 4.0.1a 收尾补充, 不重跑 DiffSBDD, 不重新生成候选.",
        "- `multi_attachment_out_of_scope` 不等于 ligand invalid, 只表示超出当前 single-anchor R-group repair 范围.",
        "- 初始生成后, `manual_visual_label` 默认为 `pending_codex_visual_review`; Codex 看图后需要回填逐 case 结论.",
        "",
        "## 2. Summary",
        "",
        f"- sample_count: {summary.get('sample_count')}.",
        f"- sampling_group_counts: `{summary.get('sampling_group_counts')}`.",
        f"- render_status_counts: `{summary.get('render_status_counts')}`.",
        f"- contact_sheet_status_counts: `{summary.get('contact_sheet_status_counts')}`.",
        f"- camera_quality_counts: `{summary.get('camera_quality_counts')}`.",
        "",
        "## 3. Case Index",
        "",
        "| visual_case_id | sampling_group | case_id | reconnect_category | quality | manual_label | contact_sheets |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, row in cases.iterrows():
        quality = "/".join(
            [
                str(row.get("camera_quality_clash", "")),
                str(row.get("camera_quality_anchor_topology", "")),
                str(row.get("camera_quality_before_after_overlay", "")),
            ]
        )
        sheets = "<br>".join(
            f"`{path}`"
            for path in [
                row.get("clash_contact_sheet_path", ""),
                row.get("anchor_topology_contact_sheet_path", ""),
                row.get("before_after_overlay_contact_sheet_path", ""),
            ]
            if str(path).strip()
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("visual_case_id", "")),
                    str(row.get("sampling_group", "")),
                    str(row.get("case_id", "")),
                    str(row.get("reconnect_category", "")),
                    quality,
                    str(row.get("manual_visual_label", "")),
                    sheets,
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def visual_qc_expt_report_markdown(cases: pd.DataFrame, summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Phase 4.0.1a Visual QC 临时实验汇报",
            "",
            "> 本文件是临时实验汇报, 不是 final report.",
            "",
            "## 1. 目标和边界",
            "",
            "- 本次 visual QC 用于检查阶段 4.0.1a reconnect 三分类与三维结构观察是否一致.",
            "- 未重跑 DiffSBDD, 未重新生成候选, 未训练或微调模型.",
            "- 未修改 reliable repair 10 项标准, 未把 local reconnect 加入 reliable repair 标准.",
            "- 未回写阶段 4.0 或阶段 4.0.1 历史结果.",
            "",
            "## 2. 抽样分布",
            "",
            f"- sample_count: {summary.get('sample_count')}.",
            f"- sampling_group_counts: `{summary.get('sampling_group_counts')}`.",
            f"- reconnect_category_counts: `{summary.get('reconnect_category_counts')}`.",
            "",
            "## 3. 渲染概况",
            "",
            f"- render_task_count: {summary.get('render_task_count')}.",
            f"- render_status_counts: `{summary.get('render_status_counts')}`.",
            f"- contact_sheet_count: {summary.get('contact_sheet_count')}.",
            f"- contact_sheet_status_counts: `{summary.get('contact_sheet_status_counts')}`.",
            "- 每个候选目标视图为 reconnect_clash, reconnect_anchor_topology, reconnect_before_after_overlay.",
            "- reconnect_clash 视图复用阶段 0 clash view 的白底, soft lighting, candidate orange stick, pocket gray transparent 和 contact marker 风格.",
            "",
            "## 4. 相机质量",
            "",
            f"- camera_quality_counts: `{summary.get('camera_quality_counts')}`.",
            f"- camera_retry_count_total: {summary.get('camera_retry_count_total')}.",
            "- 初始自动相机选择使用阶段 0 clear-view 逻辑; 低质量样本需在 Codex 看图后记录并按需重渲染.",
            "",
            "## 5. Codex 图片检视状态",
            "",
            f"- codex_image_review_status: `{summary.get('codex_image_review_status')}`.",
            "- 当前脚本阶段只生成图片, 索引和 review 模板; 若 Codex 环境完成图片检视, 需要回填 `manual_visual_label`, `manual_visual_confidence` 和 `manual_notes`.",
            "",
            "## 6. 临时关闭建议",
            "",
            "- 在完成 Codex/人工逐 case 图片检视前, 阶段 4.0.1a 不应仅凭本脚本输出正式关闭.",
            "- 若图片检视基本支持自动分类, 可建议正式关闭阶段 4.0.1a.",
            "- 若发现大量不一致, 应先修 reconnect / mapping 诊断, 不得强行关闭为正结果.",
            "",
            "## 7. Case Table",
            "",
            _markdown_table(
                cases[
                    [
                        "visual_case_id",
                        "sampling_group",
                        "case_id",
                        "candidate_budget_k",
                        "reconnect_category",
                        "reconnect_category_reason",
                        "camera_quality_clash",
                        "camera_quality_anchor_topology",
                        "camera_quality_before_after_overlay",
                        "manual_visual_label",
                        "needs_user_review",
                    ]
                ]
            ),
            "",
        ]
    )


def _write_case_assets(
    row: dict[str, Any],
    *,
    case_input: Phase4CaseInput,
    case_dir: Path,
    close_contact_overlap_threshold_angstrom: float,
) -> None:
    candidate_path = Path(str(row["candidate_path"]))
    shutil.copy2(candidate_path, case_dir / "candidate_ligand.sdf")
    shutil.copy2(case_input.failed_ligand_sdf, case_dir / "failed_ligand.sdf")
    shutil.copy2(case_input.original_ligand_sdf, case_dir / "original_ligand.sdf")
    shutil.copy2(candidate_path, case_dir / "ligand.sdf")
    _write_pocket_pdb(case_input.base_sample, case_dir / "protein_pocket.pdb")
    shutil.copy2(case_dir / "protein_pocket.pdb", case_dir / "protein.pdb")

    mol = read_first_mol(candidate_path, sanitize=False)
    coords = np.asarray(mol.GetConformer().GetPositions(), dtype=float)
    _write_nearby_pocket_pdb(case_input.base_sample, coords, case_dir / "protein_pocket_vdw_atoms.pdb")
    generated = _parse_index_json(row.get("generated_atom_indices_json", "[]"))
    all_atoms = set(range(mol.GetNumAtoms()))
    keep = sorted(all_atoms - generated)
    anchor_idx = int(float(row.get("anchor_candidate_idx", -1))) if not _is_missing(row.get("anchor_candidate_idx")) else -1
    _write_marker_pdb(case_dir / "keep_atoms.pdb", mol, coords, keep, "KEP")
    _write_marker_pdb(case_dir / "scaffold_atoms.pdb", mol, coords, keep, "SCF")
    _write_marker_pdb(case_dir / "generated_fragment_atoms.pdb", mol, coords, sorted(generated), "GEN")
    _write_marker_pdb(case_dir / "valid_rgroup_atoms.pdb", mol, coords, sorted(generated), "GEN")
    _write_marker_pdb(case_dir / "anchor_candidate_atom.pdb", mol, coords, [anchor_idx] if anchor_idx >= 0 else [], "ANC")
    attachments = _attachment_bonds(mol, generated=generated, anchor_idx=anchor_idx)
    _write_anchor_bild(case_dir / "valid_anchors.bild", coords, anchor_idx, attachments)
    _write_attachment_bild(case_dir / "actual_attachment_bonds.bild", coords, attachments["actual"], ".color 0.0 0.75 0.25")
    _write_attachment_bild(case_dir / "extra_attachment_bonds.bild", coords, attachments["extra"], ".color red")
    _write_floating_bild(case_dir / "floating_fragment.bild", mol, coords, generated=generated, keep=set(keep))
    _write_overlay_union_sdf(case_dir / "candidate_ligand.sdf", case_dir / "failed_ligand.sdf", case_dir / "overlay_union_selection.sdf")
    contact_metadata = _write_close_contact_assets(
        case_input,
        mol,
        coords,
        case_dir=case_dir,
        overlap_threshold=close_contact_overlap_threshold_angstrom,
    )
    metadata = {
        "visual_case_id": row.get("visual_case_id", ""),
        "case_id": row.get("case_id", ""),
        "candidate_id": row.get("candidate_id", ""),
        "sampling_group": row.get("sampling_group", ""),
        "reconnect_category": row.get("reconnect_category", ""),
        "reconnect_category_reason": row.get("reconnect_category_reason", ""),
        "generated_atom_count": len(generated),
        "keep_atom_count": len(keep),
        "anchor_candidate_idx": anchor_idx,
        "actual_attachment_count": len(attachments["actual"]),
        "extra_attachment_count": len(attachments["extra"]),
        **contact_metadata,
    }
    (case_dir / "case_metadata.json").write_text(json.dumps(_jsonable(metadata), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_case_readme(row, case_dir)


def _build_render_tasks_for_case(
    row: dict[str, Any],
    *,
    case_dir: Path,
    num_clear_views: int,
    candidate_directions: int,
) -> list[VisualQCRenderTask]:
    tasks = []
    for view in VISUAL_QC_VIEWS:
        selection_view, ligand_mode = VIEW_SELECTION[view]
        _write_selection_alias(case_dir, ligand_mode=ligand_mode)
        cameras = select_clear_camera_views(
            case_dir,
            view=selection_view,
            num_views=num_clear_views,
            num_candidates=candidate_directions,
        )
        cameras = tuple(_retarget_cameras(cameras, _focus_for_visual_view(case_dir, view)))
        script_path = case_dir / "scripts" / f"{view}_{cameras[0].label}_{cameras[-1].label}.cxc"
        tasks.append(
            VisualQCRenderTask(
                visual_case_id=str(row["visual_case_id"]),
                case_id=str(row["case_id"]),
                candidate_id=str(row["candidate_id"]),
                sampling_group=str(row["sampling_group"]),
                view=view,
                case_dir=case_dir,
                script_path=script_path,
                cameras=cameras,
                candidate_directions=candidate_directions,
            )
        )
    _write_selection_alias(case_dir, ligand_mode="candidate")
    return tasks


def _write_group_script(task: VisualQCRenderTask, *, width: int, height: int) -> None:
    _write_camera_focus_helper(task.case_dir / "scripts" / "center_camera_on_focus.py")
    frame_spec = _view_frame_spec(task.view)
    lines = [
        f"# Phase 4.0.1a visual QC render for {task.visual_case_id}: {task.view}.",
        "# Images are for reconnect visual QC, not automatic reliable repair pass/fail.",
        *_view_commands(task.view),
    ]
    for camera in task.cameras:
        image_rel = Path("images") / f"{task.view}_{camera.label}.png"
        lines.extend(
            [
                *_clear_view_commands(frame_spec, camera),
                f"save {image_rel.as_posix()} width {int(width)} height {int(height)}",
            ]
        )
    task.script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _view_commands(view: str) -> list[str]:
    common = ["set bgColor white", "lighting soft", "graphics silhouettes true width 1.4 depthJump 0.01"]
    if view == "reconnect_clash":
        return [
            *common,
            "open protein_pocket.pdb",
            "open candidate_ligand.sdf",
            "open protein_close_contact_atoms.pdb",
            "open ligand_close_contact_atoms.pdb",
            "open close_contacts.bild",
            "show #1 atoms",
            "style #1 stick",
            "color #1 gray",
            "transparency #1 70 target a",
            "show #2 atoms",
            "style #2 stick",
            "color #2 orange",
            "show #3 atoms",
            "show #4 atoms",
            "style #3 sphere",
            "style #4 sphere",
            "size #3 atomRadius 0.28",
            "size #4 atomRadius 0.32",
            "color #3 gray",
            "color #4 royalblue",
            "transparency #3 45 target a",
            "transparency #4 25 target a",
            "color #5 red",
        ]
    if view == "reconnect_anchor_topology":
        return [
            *common,
            "open candidate_ligand.sdf",
            "open keep_atoms.pdb",
            "open generated_fragment_atoms.pdb",
            "open anchor_candidate_atom.pdb",
            "open actual_attachment_bonds.bild",
            "open extra_attachment_bonds.bild",
            "open floating_fragment.bild",
            "style #1 stick",
            "color #1 gray",
            "transparency #1 45 target a",
            "show #2 atoms",
            "show #3 atoms",
            "show #4 atoms",
            "style #2 sphere",
            "style #3 sphere",
            "style #4 sphere",
            "size #2 atomRadius 0.20",
            "size #3 atomRadius 0.30",
            "size #4 atomRadius 0.55",
            "color #2 blue",
            "color #3 orange",
            "color #4 magenta",
            "color #5 green",
            "color #6 red",
            "color #7 red",
        ]
    if view == "reconnect_before_after_overlay":
        return [
            *common,
            "open failed_ligand.sdf",
            "open candidate_ligand.sdf",
            "open original_ligand.sdf",
            "open keep_atoms.pdb",
            "open generated_fragment_atoms.pdb",
            "open anchor_candidate_atom.pdb",
            "open actual_attachment_bonds.bild",
            "open extra_attachment_bonds.bild",
            "style #1 stick",
            "style #2 stick",
            "style #3 stick",
            "color #1 red",
            "color #2 orange",
            "color #3 lightblue",
            "transparency #1 55 target a",
            "transparency #3 72 target a",
            "show #4 atoms",
            "show #5 atoms",
            "show #6 atoms",
            "style #4 sphere",
            "style #5 sphere",
            "style #6 sphere",
            "size #4 atomRadius 0.20",
            "size #5 atomRadius 0.28",
            "size #6 atomRadius 0.48",
            "color #4 blue",
            "color #5 yellow",
            "color #6 magenta",
            "color #7 green",
            "color #8 red",
        ]
    raise ValueError(f"Unsupported visual QC view: {view}")


def _view_frame_spec(view: str) -> str:
    if view == "reconnect_before_after_overlay":
        return "#1-8"
    return "all"


def _clear_view_commands(model_spec: str, camera_view: CameraView) -> list[str]:
    axis_id = _axis_id(camera_view.label)
    focus = np.asarray(camera_view.focus, dtype=float)
    direction = _unit(np.asarray(camera_view.direction, dtype=float))
    endpoint = focus + direction * 10.0
    return [
        f"define axis fromPoint {_point_spec(focus)} toPoint {_point_spec(endpoint)} id {axis_id} color white radius 0.01",
        f"hide {axis_id} models",
        f"view {model_spec} clip false pad 0.50 zalign {axis_id}",
        f"runscript scripts/center_camera_on_focus.py {_point_spec(focus).replace(',', ' ')}",
    ]


def _write_camera_focus_helper(path: Path) -> None:
    path.write_text(
        """from __future__ import annotations

import sys

import numpy as np
from chimerax.geometry import Place


def main() -> None:
    focus = np.asarray([float(value) for value in sys.argv[1:4]], dtype=float)
    view = session.main_view
    camera = view.camera
    position = camera.position
    axes = np.asarray(position.axes(), dtype=float)
    origin = np.asarray(position.origin(), dtype=float)
    x_axis = axes[0]
    y_axis = axes[1]
    delta = focus - origin
    screen_shift = float(np.dot(delta, x_axis)) * x_axis + float(np.dot(delta, y_axis)) * y_axis
    camera.position = Place(axes=axes, origin=origin + screen_shift)
    view.center_of_rotation = focus


main()
""",
        encoding="utf-8",
    )


def _render_rows(
    task: VisualQCRenderTask,
    *,
    status: str,
    render_action: str,
    returncode: int | None = None,
    stderr_tail: str = "",
) -> list[dict[str, Any]]:
    rows = []
    for camera in task.cameras:
        image_path = task.case_dir / "images" / f"{task.view}_{camera.label}.png"
        row_status = status
        if status == "rendered" and not image_path.exists():
            row_status = "missing_image"
        rows.append(
            {
                "visual_case_id": task.visual_case_id,
                "case_id": task.case_id,
                "candidate_id": task.candidate_id,
                "sampling_group": task.sampling_group,
                "view": task.view,
                "angle": camera.label,
                "script_path": str(task.script_path),
                "image_path": str(image_path),
                "status": row_status,
                "render_action": render_action,
                "returncode": "" if returncode is None else int(returncode),
                "stderr_tail": stderr_tail,
                "camera_score": camera.score,
                "camera_focus": ",".join(f"{value:.6f}" for value in camera.focus),
                "camera_direction": ",".join(f"{value:.6f}" for value in camera.direction),
                "camera_selection_tier": camera.selection_tier,
                "candidate_directions": int(task.candidate_directions),
                "ligand_occluded_fraction": camera.ligand_occluded_fraction,
                "center_line_blocked": camera.center_line_blocked,
                "projection_area_score": camera.projection_area_score,
                "interest_occluded_fraction": camera.interest_occluded_fraction,
                "key_occluded_fraction": camera.key_occluded_fraction,
                "interest_area_score": camera.interest_area_score,
            }
        )
    return rows


def _task_images_exist(task: VisualQCRenderTask) -> bool:
    return all(
        (task.case_dir / "images" / f"{task.view}_{camera.label}.png").is_file()
        and (task.case_dir / "images" / f"{task.view}_{camera.label}.png").stat().st_size > 0
        for camera in task.cameras
    )


def _write_pocket_pdb(sample: dict[str, Any], path: Path) -> None:
    protein = sample["protein"]
    indices = [int(i) for i in sample["pocket"]["protein_atom_indices"]]
    coords = np.asarray(protein["coords"], dtype=float)
    elements = list(protein["elements"])
    atom_names = list(protein["atom_names"])
    chain_ids = list(protein["chain_ids"])
    residue_ids = list(protein["residue_ids"])
    residue_names = list(protein["residue_names"])
    lines = []
    for serial, idx in enumerate(indices, start=1):
        x, y, z = coords[idx]
        element = _element(elements[idx])
        atom_name = str(atom_names[idx] or element)[:4]
        resname = str(residue_names[idx] or "UNK")[:3]
        chain = str(chain_ids[idx] or "A")[:1]
        resid = int(residue_ids[idx] or 1)
        lines.append(
            f"ATOM  {serial:5d} {atom_name:<4s} {resname:>3s} {chain}{resid:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {element:>2s}"
        )
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_nearby_pocket_pdb(
    sample: dict[str, Any],
    ligand_coords: np.ndarray,
    path: Path,
    *,
    cutoff_angstrom: float = 7.0,
    max_atoms: int = 96,
) -> None:
    protein = sample["protein"]
    pocket_indices = [int(i) for i in sample["pocket"]["protein_atom_indices"]]
    protein_coords = np.asarray(protein["coords"], dtype=float)
    if len(ligand_coords) == 0 or not pocket_indices:
        _write_pocket_pdb(sample, path)
        return
    pocket_coords = protein_coords[pocket_indices]
    distances = np.linalg.norm(pocket_coords[:, None, :] - ligand_coords[None, :, :], axis=2).min(axis=1)
    ordered = sorted(zip(distances.tolist(), pocket_indices), key=lambda item: item[0])
    selected = [idx for dist, idx in ordered if dist <= cutoff_angstrom][:max_atoms]
    if len(selected) < min(40, len(ordered)):
        selected = [idx for _, idx in ordered[: min(max_atoms, max(40, len(ordered))) ]]
    _write_protein_contact_pdb(sample, selected, path)


def _write_marker_pdb(path: Path, mol: Any, coords: np.ndarray, indices: Iterable[int], resname: str) -> None:
    lines = []
    valid = [int(idx) for idx in sorted(set(int(i) for i in indices)) if 0 <= int(idx) < len(coords)]
    for serial, idx in enumerate(valid, start=1):
        atom = mol.GetAtomWithIdx(idx)
        element = _element(atom.GetSymbol())
        x, y, z = coords[idx]
        atom_name = f"{element}{serial}"[:4]
        lines.append(
            f"HETATM{serial:5d} {atom_name:<4s} {resname:>3s} A{serial:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {element:>2s}"
        )
    if not lines:
        lines.append("REMARK no atoms")
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_anchor_bild(path: Path, coords: np.ndarray, anchor_idx: int, attachments: dict[str, list[tuple[int, int]]]) -> None:
    lines = [".color magenta"]
    if 0 <= anchor_idx < len(coords):
        x, y, z = coords[anchor_idx]
        lines.append(f".sphere {x:.3f} {y:.3f} {z:.3f} 0.42")
    for start, end in [*attachments["actual"], *attachments["extra"]]:
        if 0 <= start < len(coords) and 0 <= end < len(coords):
            a = coords[start]
            b = coords[end]
            lines.append(f".cylinder {a[0]:.3f} {a[1]:.3f} {a[2]:.3f} {b[0]:.3f} {b[1]:.3f} {b[2]:.3f} 0.05")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_attachment_bild(path: Path, coords: np.ndarray, bonds: list[tuple[int, int]], color_line: str) -> None:
    lines = [color_line]
    for start, end in bonds:
        if 0 <= start < len(coords) and 0 <= end < len(coords):
            a = coords[start]
            b = coords[end]
            lines.append(f".cylinder {a[0]:.3f} {a[1]:.3f} {a[2]:.3f} {b[0]:.3f} {b[1]:.3f} {b[2]:.3f} 0.075")
            lines.append(f".sphere {b[0]:.3f} {b[1]:.3f} {b[2]:.3f} 0.14")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_floating_bild(path: Path, mol: Any, coords: np.ndarray, *, generated: set[int], keep: set[int]) -> None:
    from rdkit import Chem

    lines = [".color yellow"]
    for fragment in Chem.GetMolFrags(mol, asMols=False, sanitizeFrags=False):
        atoms = set(int(idx) for idx in fragment)
        if atoms & generated and not atoms & keep:
            focus = coords[sorted(atoms & generated)].mean(axis=0)
            lines.append(f".sphere {focus[0]:.3f} {focus[1]:.3f} {focus[2]:.3f} 0.34")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_close_contact_assets(
    case_input: Phase4CaseInput,
    mol: Any,
    ligand_coords: np.ndarray,
    *,
    case_dir: Path,
    overlap_threshold: float,
    max_pairs: int = 12,
) -> dict[str, Any]:
    protein = case_input.base_sample["protein"]
    pocket_indices = [int(i) for i in case_input.base_sample["pocket"]["protein_atom_indices"]]
    protein_coords_all = np.asarray(protein["coords"], dtype=float)
    protein_elements = list(protein["elements"])
    ligand_elements = [_element(mol.GetAtomWithIdx(i).GetSymbol()) for i in range(mol.GetNumAtoms())]
    pairs: list[tuple[float, int, int, float, float]] = []
    nearest: list[tuple[float, int, int, float, float]] = []
    for pocket_pos, protein_idx in enumerate(pocket_indices):
        p_coord = protein_coords_all[protein_idx]
        p_element = _element(protein_elements[protein_idx])
        p_radius = _vdw_radius(p_element)
        for ligand_idx, l_coord in enumerate(ligand_coords):
            l_radius = _vdw_radius(ligand_elements[ligand_idx])
            distance = float(np.linalg.norm(p_coord - l_coord))
            overlap = p_radius + l_radius - distance
            item = (overlap, int(protein_idx), int(ligand_idx), float(p_radius), float(l_radius))
            nearest.append(item)
            if overlap >= overlap_threshold:
                pairs.append(item)
    pairs = sorted(pairs, key=lambda item: item[0], reverse=True)[:max_pairs]
    fallback_used = False
    if not pairs:
        fallback_used = True
        pairs = sorted(nearest, key=lambda item: item[0], reverse=True)[: min(3, max_pairs)]
    protein_contact_indices = [pair[1] for pair in pairs]
    ligand_contact_indices = [pair[2] for pair in pairs]
    _write_protein_contact_pdb(case_input.base_sample, protein_contact_indices, case_dir / "protein_close_contact_atoms.pdb")
    _write_marker_pdb(case_dir / "ligand_close_contact_atoms.pdb", mol, ligand_coords, ligand_contact_indices, "LCC")
    shutil.copy2(case_dir / "ligand_close_contact_atoms.pdb", case_dir / "ligand_vdw_atoms.pdb")
    _write_close_contacts_bild(case_input.base_sample, ligand_coords, pairs, case_dir / "close_contacts.bild")
    return {
        "close_contact_pair_count": int(0 if fallback_used else len(pairs)),
        "close_contact_marker_pair_count": int(len(pairs)),
        "close_contact_fallback_used": bool(fallback_used),
        "max_contact_overlap_angstrom": float(max((pair[0] for pair in pairs), default=float("nan"))),
    }


def _write_protein_contact_pdb(sample: dict[str, Any], indices: Iterable[int], path: Path) -> None:
    protein = sample["protein"]
    coords = np.asarray(protein["coords"], dtype=float)
    elements = list(protein["elements"])
    atom_names = list(protein["atom_names"])
    chain_ids = list(protein["chain_ids"])
    residue_ids = list(protein["residue_ids"])
    residue_names = list(protein["residue_names"])
    lines = []
    for serial, idx in enumerate(sorted(set(int(i) for i in indices)), start=1):
        if idx < 0 or idx >= len(coords):
            continue
        x, y, z = coords[idx]
        element = _element(elements[idx])
        atom_name = str(atom_names[idx] or element)[:4]
        resname = str(residue_names[idx] or "UNK")[:3]
        chain = str(chain_ids[idx] or "A")[:1]
        resid = int(residue_ids[idx] or 1)
        lines.append(
            f"ATOM  {serial:5d} {atom_name:<4s} {resname:>3s} {chain}{resid:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {element:>2s}"
        )
    if not lines:
        lines.append("REMARK no atoms")
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_close_contacts_bild(sample: dict[str, Any], ligand_coords: np.ndarray, pairs: list[tuple[float, int, int, float, float]], path: Path) -> None:
    protein_coords = np.asarray(sample["protein"]["coords"], dtype=float)
    lines: list[str] = []
    for overlap, protein_idx, ligand_idx, _, _ in pairs:
        p = protein_coords[protein_idx]
        l = ligand_coords[ligand_idx]
        lines.append(".color red" if overlap >= 0 else ".color 0.45 0.45 0.45")
        lines.append(f".sphere {l[0]:.3f} {l[1]:.3f} {l[2]:.3f} 0.18")
        lines.append(".color 0.25 0.45 1.0")
        lines.append(f".sphere {p[0]:.3f} {p[1]:.3f} {p[2]:.3f} 0.16")
        lines.append(".color 0.28 0.28 0.28")
        lines.append(f".cylinder {l[0]:.3f} {l[1]:.3f} {l[2]:.3f} {p[0]:.3f} {p[1]:.3f} {p[2]:.3f} 0.035")
    if not lines:
        lines.append(".color red")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _attachment_bonds(mol: Any, *, generated: set[int], anchor_idx: int) -> dict[str, list[tuple[int, int]]]:
    actual: list[tuple[int, int]] = []
    extra: list[tuple[int, int]] = []
    for gen_idx in generated:
        atom = mol.GetAtomWithIdx(int(gen_idx))
        for neighbor in atom.GetNeighbors():
            n_idx = int(neighbor.GetIdx())
            if n_idx in generated:
                continue
            bond = (int(gen_idx), n_idx)
            if n_idx == anchor_idx:
                actual.append(bond)
            else:
                extra.append(bond)
    return {"actual": actual, "extra": extra}


def _write_overlay_union_sdf(candidate_sdf: Path, failed_sdf: Path, output_sdf: Path) -> None:
    candidate_coords, candidate_elements = _read_sdf_atoms(candidate_sdf)
    failed_coords, failed_elements = _read_sdf_atoms(failed_sdf)
    coords = np.concatenate([candidate_coords, failed_coords], axis=0)
    elements = [*candidate_elements, *failed_elements]
    lines = [
        "phase4_0_1a_overlay_union_selection",
        "  Clash2Feedback",
        "",
        f"{len(coords):>3d}{0:>3d}  0  0  0  0            999 V2000",
    ]
    for coord, element in zip(coords, elements, strict=True):
        x, y, z = coord
        lines.append(f"{x:10.4f}{y:10.4f}{z:10.4f} {element:<3s} 0  0  0  0  0  0  0  0  0  0  0  0")
    lines.extend(["M  END", "$$$$"])
    output_sdf.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_selection_alias(case_dir: Path, *, ligand_mode: str) -> None:
    if ligand_mode == "candidate":
        shutil.copy2(case_dir / "candidate_ligand.sdf", case_dir / "ligand.sdf")
    elif ligand_mode == "overlay_union":
        shutil.copy2(case_dir / "overlay_union_selection.sdf", case_dir / "ligand.sdf")
    else:
        raise ValueError(f"Unsupported ligand_mode: {ligand_mode}")


def _focus_for_visual_view(case_dir: Path, view: str) -> np.ndarray | None:
    if view == "reconnect_clash":
        coords = _concat_coords([_read_bild_coords(case_dir / "close_contacts.bild"), _read_sdf_coords(case_dir / "candidate_ligand.sdf")])
    elif view == "reconnect_anchor_topology":
        coords = _concat_coords(
            [
                _read_pdb_coords(case_dir / "anchor_candidate_atom.pdb"),
                _read_pdb_coords(case_dir / "generated_fragment_atoms.pdb"),
                _read_bild_coords(case_dir / "actual_attachment_bonds.bild"),
                _read_bild_coords(case_dir / "extra_attachment_bonds.bild"),
            ]
        )
    elif view == "reconnect_before_after_overlay":
        coords = _concat_coords(
            [
                _read_sdf_coords(case_dir / "candidate_ligand.sdf"),
                _read_sdf_coords(case_dir / "failed_ligand.sdf"),
                _read_pdb_coords(case_dir / "generated_fragment_atoms.pdb"),
            ]
        )
    else:
        coords = np.zeros((0, 3), dtype=float)
    return coords.mean(axis=0) if len(coords) else None


def _retarget_cameras(cameras: Iterable[CameraView], focus: np.ndarray | None) -> list[CameraView]:
    result = list(cameras)
    if focus is None or np.asarray(focus).shape != (3,):
        return result
    focus_tuple = tuple(float(value) for value in focus)
    return [replace(camera, focus=focus_tuple) for camera in result]


def _attach_visual_paths(cases: pd.DataFrame, *, run_root: Path) -> pd.DataFrame:
    rows = []
    for _, row in cases.iterrows():
        item = row.to_dict()
        safe_id = _safe_id(str(item["candidate_id"]))
        case_dir = run_root / str(item["case_id"]) / safe_id
        item["safe_candidate_id"] = safe_id
        item["case_dir"] = str(case_dir)
        images_dir = case_dir / "images"
        item["clash_contact_sheet_path"] = str(images_dir / CONTACT_SHEET_NAMES["reconnect_clash"])
        item["anchor_topology_contact_sheet_path"] = str(images_dir / CONTACT_SHEET_NAMES["reconnect_anchor_topology"])
        item["before_after_overlay_contact_sheet_path"] = str(images_dir / CONTACT_SHEET_NAMES["reconnect_before_after_overlay"])
        rows.append(item)
    return pd.DataFrame(rows)


def _merge_contact_sheet_paths(cases: pd.DataFrame, contact_sheets: pd.DataFrame) -> pd.DataFrame:
    if contact_sheets.empty:
        return cases
    output = cases.copy()
    for _, sheet in contact_sheets.iterrows():
        visual_case_id = str(sheet["visual_case_id"])
        view = str(sheet["view"])
        path = str(sheet.get("contact_sheet_path", ""))
        column = {
            "reconnect_clash": "clash_contact_sheet_path",
            "reconnect_anchor_topology": "anchor_topology_contact_sheet_path",
            "reconnect_before_after_overlay": "before_after_overlay_contact_sheet_path",
        }.get(view)
        if column:
            output.loc[output["visual_case_id"].astype(str) == visual_case_id, column] = path
    return output


def _merge_camera_quality(cases: pd.DataFrame, render_manifest: pd.DataFrame, contact_sheets: pd.DataFrame) -> pd.DataFrame:
    output = cases.copy()
    for suffix in ["clash", "anchor_topology", "before_after_overlay"]:
        output[f"camera_quality_{suffix}"] = "camera_quality_failed"
        output[f"camera_retry_count_{suffix}"] = 0
    output["camera_adjustment_notes"] = "first_pass_clear_view_selection"
    output["final_camera_selection_status"] = "first_pass"
    if render_manifest.empty:
        return output
    view_suffix = {
        "reconnect_clash": "clash",
        "reconnect_anchor_topology": "anchor_topology",
        "reconnect_before_after_overlay": "before_after_overlay",
    }
    for (visual_case_id, view), group in render_manifest.groupby(["visual_case_id", "view"], sort=False):
        suffix = view_suffix[str(view)]
        quality = _camera_quality_for_group(group)
        output.loc[output["visual_case_id"].astype(str) == str(visual_case_id), f"camera_quality_{suffix}"] = quality
    poor_mask = output[
        ["camera_quality_clash", "camera_quality_anchor_topology", "camera_quality_before_after_overlay"]
    ].isin(["camera_quality_poor", "camera_quality_failed"]).any(axis=1)
    output.loc[poor_mask, "manual_visual_label"] = "needs_further_review"
    output.loc[poor_mask, "manual_visual_confidence"] = "low"
    output.loc[poor_mask, "needs_user_review"] = True
    return output


def _camera_quality_for_group(group: pd.DataFrame) -> str:
    rendered = group[group["status"] == "rendered"]
    if rendered.shape[0] == 0:
        return "camera_quality_failed"
    if rendered.shape[0] < 8:
        return "camera_quality_poor"
    occlusion = pd.to_numeric(rendered["ligand_occluded_fraction"], errors="coerce").fillna(0.0)
    key_occ = pd.to_numeric(rendered["key_occluded_fraction"], errors="coerce").fillna(0.0)
    projection = pd.to_numeric(rendered["projection_area_score"], errors="coerce").fillna(1.0)
    blocked = rendered["center_line_blocked"].map(lambda value: str(value).lower() == "true").mean()
    if float(occlusion.median()) <= 0.20 and float(key_occ.median()) <= 0.35 and float(projection.median()) >= 0.25 and float(blocked) <= 0.25:
        return "camera_quality_good"
    if float(occlusion.median()) <= 0.40 and float(key_occ.median()) <= 0.55 and float(projection.median()) >= 0.12 and float(blocked) <= 0.50:
        return "camera_quality_usable"
    return "camera_quality_poor"


def _pick_diverse(df: pd.DataFrame, count: int, *, seed: int) -> pd.DataFrame:
    if count <= 0 or df.empty:
        return df.head(0).copy()
    pool = df.copy()
    pool["_sort_budget"] = pd.to_numeric(pool.get("candidate_budget_k", 0), errors="coerce").fillna(0).astype(int)
    pool["_sort_extra"] = pd.to_numeric(pool.get("num_extra_attachments", 0), errors="coerce").fillna(0).astype(int)
    pool["_sort_reason"] = pool.get("reconnect_category_reason", "").astype(str)
    pool["_sort_candidate"] = pool.get("candidate_id", "").astype(str)
    pool = pool.sort_values(["_sort_budget", "_sort_reason", "_sort_extra", "case_id", "_sort_candidate"]).reset_index(drop=True)
    selected_indices: list[int] = []
    used_budgets: set[int] = set()
    used_reasons: set[str] = set()
    used_extra: set[int] = set()
    used_cases: set[str] = set()
    while len(selected_indices) < min(count, pool.shape[0]):
        best_idx = None
        best_score = -1
        for idx, row in pool.iterrows():
            if idx in selected_indices:
                continue
            budget = int(row.get("_sort_budget", 0))
            reason = str(row.get("_sort_reason", ""))
            extra = int(row.get("_sort_extra", 0))
            case_id = str(row.get("case_id", ""))
            score = 0
            score += 9 if budget not in used_budgets else 0
            score += 7 if reason not in used_reasons else 0
            score += 5 if extra not in used_extra else 0
            score += 3 if case_id not in used_cases else 0
            score += int(seed % 3)
            if score > best_score:
                best_score = score
                best_idx = int(idx)
        if best_idx is None:
            break
        selected_indices.append(best_idx)
        row = pool.loc[best_idx]
        used_budgets.add(int(row.get("_sort_budget", 0)))
        used_reasons.add(str(row.get("_sort_reason", "")))
        used_extra.add(int(row.get("_sort_extra", 0)))
        used_cases.add(str(row.get("case_id", "")))
    result = pool.loc[selected_indices].drop(columns=[col for col in pool.columns if col.startswith("_sort_")]).copy()
    return result.reset_index(drop=True)


def _tag_sampling_group(df: pd.DataFrame, group: str, reason: str) -> pd.DataFrame:
    result = df.copy()
    result["sampling_group"] = group
    result["sampling_reason"] = reason
    return result


def _fallback_reason(row: pd.Series) -> str:
    reason = str(row.get("reconnect_category_reason", ""))
    if str(row.get("sampling_group", "")) == "diffsbdd_invalid_non_reliable" and "anchor_not_mapped" not in reason:
        return "anchor_not_mapped_not_available_in_diffsbdd_candidates"
    return ""


def _renderable_series(df: pd.DataFrame) -> pd.Series:
    readable = _bool_series(df, "candidate_readable") if "candidate_readable" in df else pd.Series([True] * len(df), index=df.index)
    paths = df.get("candidate_path", pd.Series([""] * len(df), index=df.index)).map(_path_exists)
    generated = (
        pd.to_numeric(df.get("generated_fragment_heavy_atom_count", pd.Series([1] * len(df), index=df.index)), errors="coerce")
        .fillna(1)
        .astype(int)
        >= 0
    )
    return readable & paths & generated


def _path_exists(value: Any) -> bool:
    if _is_missing(value):
        return False
    text = str(value).strip()
    return bool(text) and Path(text).exists()


def _bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df:
        return pd.Series([False] * int(df.shape[0]), index=df.index, dtype=bool)
    return df[column].map(lambda value: _as_bool(value, default=False)).astype(bool)


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if _is_missing(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and math.isnan(value):
            return default
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _parse_index_json(value: Any) -> set[int]:
    if _is_missing(value):
        return set()
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return set()
    return {int(item) for item in payload}


def _read_sdf_atoms(path: Path) -> tuple[np.ndarray, list[str]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    counts = lines[3].split()
    num_atoms = int(counts[0])
    coords: list[list[float]] = []
    elements: list[str] = []
    for line in lines[4 : 4 + num_atoms]:
        parts = line.split()
        if len(parts) < 4:
            continue
        coords.append([float(parts[0]), float(parts[1]), float(parts[2])])
        elements.append(_element(parts[3]))
    return np.asarray(coords, dtype=float), elements


def _read_sdf_coords(path: Path) -> np.ndarray:
    coords, _ = _read_sdf_atoms(path)
    return coords


def _read_pdb_coords(path: Path) -> np.ndarray:
    coords: list[list[float]] = []
    if not path.exists():
        return np.zeros((0, 3), dtype=float)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        try:
            coords.append([float(line[30:38]), float(line[38:46]), float(line[46:54])])
        except ValueError:
            parts = line.split()
            if len(parts) >= 9:
                coords.append([float(parts[6]), float(parts[7]), float(parts[8])])
    return np.asarray(coords, dtype=float) if coords else np.zeros((0, 3), dtype=float)


def _read_bild_coords(path: Path) -> np.ndarray:
    coords: list[list[float]] = []
    if not path.exists():
        return np.zeros((0, 3), dtype=float)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == ".sphere" and len(parts) >= 5:
            coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif parts[0] == ".cylinder" and len(parts) >= 7:
            coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
            coords.append([float(parts[4]), float(parts[5]), float(parts[6])])
    return np.asarray(coords, dtype=float) if coords else np.zeros((0, 3), dtype=float)


def _concat_coords(arrays: Iterable[np.ndarray]) -> np.ndarray:
    valid = [np.asarray(array, dtype=float) for array in arrays if np.asarray(array).ndim == 2 and len(array)]
    if not valid:
        return np.zeros((0, 3), dtype=float)
    return np.concatenate(valid, axis=0)


def _safe_id(value: str, *, max_length: int = 96) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "candidate"
    if len(text) <= max_length:
        return text
    import hashlib

    suffix = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return f"{text[: max_length - 11]}_{suffix}"


def _element(value: Any) -> str:
    text = "".join(ch for ch in str(value).strip() if ch.isalpha())
    if not text:
        return "C"
    if len(text) >= 2 and text[:2].upper() in {"CL", "BR"}:
        return text[:2].title()
    return text[0].upper()


def _vdw_radius(element: str) -> float:
    try:
        return get_vdw_radius(element)
    except ValueError:
        return get_vdw_radius("C")


def _unit(values: np.ndarray) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm < 1e-12:
        return np.asarray([1.0, 0.0, 0.0], dtype=float)
    return vector / norm


def _point_spec(point: np.ndarray) -> str:
    return ",".join(f"{float(value):.4f}" for value in point)


def _axis_id(label: str) -> str:
    try:
        index = int(label.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        index = 1
    return f"#{90 + max(1, min(index, 80))}"


def _tail(text: str, max_chars: int = 600) -> str:
    compact = " ".join(str(text).split())
    return compact[-max_chars:]


def _validate_paths(input_paths: dict[str, Path]) -> None:
    missing = [f"{name}={path}" for name, path in input_paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing visual QC input path(s): " + "; ".join(missing))


def _render_manifest_columns() -> list[str]:
    return [
        "visual_case_id",
        "case_id",
        "candidate_id",
        "sampling_group",
        "view",
        "angle",
        "script_path",
        "image_path",
        "status",
        "render_action",
        "returncode",
        "stderr_tail",
        "camera_score",
        "camera_focus",
        "camera_direction",
        "camera_selection_tier",
        "candidate_directions",
        "ligand_occluded_fraction",
        "center_line_blocked",
        "projection_area_score",
        "interest_occluded_fraction",
        "key_occluded_fraction",
        "interest_area_score",
    ]


def _contact_sheet_columns() -> list[str]:
    return [
        "visual_case_id",
        "case_id",
        "candidate_id",
        "sampling_group",
        "view",
        "contact_sheet_path",
        "status",
        "num_images",
        "rows",
        "columns",
    ]


def _contact_sheet_row(row: pd.Series, *, view: str, status: str, sheet_path: str, num_images: int, rows: int, columns: int) -> dict[str, Any]:
    return {
        "visual_case_id": row.get("visual_case_id", ""),
        "case_id": row.get("case_id", ""),
        "candidate_id": row.get("candidate_id", ""),
        "sampling_group": row.get("sampling_group", ""),
        "view": view,
        "contact_sheet_path": sheet_path,
        "status": status,
        "num_images": int(num_images),
        "rows": int(rows),
        "columns": int(columns),
    }


def _draw_legend(sheet: Any, view: str, *, title_font: Any, font: Any) -> None:
    from PIL import ImageDraw

    labels = {
        "reconnect_clash": [
            ("candidate ligand", (230, 155, 0)),
            ("protein pocket", (135, 135, 135)),
            ("ligand contact atoms", (65, 115, 255)),
            ("contact markers", (220, 0, 0)),
        ],
        "reconnect_anchor_topology": [
            ("candidate/keep", (110, 110, 110)),
            ("generated fragment", (230, 155, 0)),
            ("anchor", (220, 0, 220)),
            ("actual attachment", (0, 180, 60)),
            ("extra attachment/floating", (220, 0, 0)),
        ],
        "reconnect_before_after_overlay": [
            ("failed ligand", (220, 0, 0)),
            ("candidate ligand", (230, 155, 0)),
            ("original ligand", (120, 185, 230)),
            ("generated fragment", (235, 210, 0)),
            ("anchor", (220, 0, 220)),
        ],
    }[view]
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((0, 0, sheet.width, 81), fill=(248, 248, 248), outline=(210, 210, 210))
    draw.text((12, 10), view, fill=(0, 0, 0), font=title_font)
    x = 12
    y = 48
    for label, color in labels:
        draw.rectangle((x, y, x + 14, y + 10), fill=color, outline=(80, 80, 80))
        draw.text((x + 20, y - 4), label, fill=(0, 0, 0), font=font)
        x += 20 + max(120, len(label) * 8)


def _load_font(*, size: int) -> Any:
    from PIL import ImageFont

    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _crop_white_border(image: Any, *, threshold: int = 12, margin: int = 18) -> Any:
    from PIL import Image, ImageChops

    background = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, background).convert("L")
    mask = diff.point(lambda value: 255 if value > threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return image
    left, upper, right, lower = bbox
    return image.crop((max(0, left - margin), max(0, upper - margin), min(image.width, right + margin), min(image.height, lower + margin)))


def _numeric_sum(df: pd.DataFrame, columns: Iterable[str]) -> int:
    total = 0
    for column in columns:
        if column in df:
            total += int(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())
    return total


def _quality_counts(cases: pd.DataFrame) -> dict[str, int]:
    values: list[str] = []
    for column in ["camera_quality_clash", "camera_quality_anchor_topology", "camera_quality_before_after_overlay"]:
        if column in cases:
            values.extend(cases[column].astype(str).tolist())
    return dict(pd.Series(values).value_counts().to_dict()) if values else {}


def _git_output(repo_root: Path, command: list[str]) -> str:
    completed = subprocess.run(command, cwd=repo_root, text=True, capture_output=True, check=False)
    return (completed.stdout or completed.stderr).strip()


def _markdown_table(df: pd.DataFrame, *, max_rows: int = 80) -> str:
    if df.empty:
        return "_empty_"
    table = df.head(max_rows).fillna("").astype(str)
    lines = [
        "| " + " | ".join(table.columns) + " |",
        "| " + " | ".join(["---"] * len(table.columns)) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in table.columns) + " |")
    if df.shape[0] > max_rows:
        lines.append(f"\n_omitted {df.shape[0] - max_rows} rows_")
    return "\n".join(lines)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _write_case_readme(row: dict[str, Any], case_dir: Path) -> None:
    text = f"""# Phase 4.0.1a Visual QC: {row.get('visual_case_id')}

## 1. Case

- case_id: {row.get('case_id')}.
- candidate_id: {row.get('candidate_id')}.
- sampling_group: {row.get('sampling_group')}.
- reconnect_category: {row.get('reconnect_category')}.
- reconnect_category_reason: {row.get('reconnect_category_reason')}.

## 2. Views

- `reconnect_clash_contact_sheet.png`: candidate 与 pocket close-contact / clash 观察.
- `reconnect_anchor_topology_contact_sheet.png`: anchor, generated fragment, actual/extra attachment 观察.
- `reconnect_before_after_overlay_contact_sheet.png`: failed/candidate/original overlay 和局部变化观察.
"""
    (case_dir / "README.md").write_text(text, encoding="utf-8")
