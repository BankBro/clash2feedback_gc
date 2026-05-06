from __future__ import annotations

import pickle
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from clash2feedback.utils.files import ensure_dir


VISUAL_NOTE_COLUMNS = [
    "complex_id",
    "target_id",
    "ligand_in_pocket",
    "pocket_ok",
    "scaffold_ok",
    "rgroups_ok",
    "anchors_ok",
    "obvious_clash",
    "result",
    "notes",
]


def select_visual_check_samples(
    visual_check: pd.DataFrame,
    manifest: pd.DataFrame,
    *,
    num_samples: int = 10,
) -> pd.DataFrame:
    if visual_check.empty:
        raise ValueError("visual_check is empty")
    rows = visual_check.copy()
    if "sample_id" not in rows.columns:
        raise ValueError("visual_check must contain sample_id")
    if not manifest.empty and "sample_id" in manifest.columns:
        keep = [
            column
            for column in ["sample_id", "target_id", "split_group", "pdb_id", "phase0_usable"]
            if column in manifest.columns
        ]
        rows = rows.merge(manifest[keep], on="sample_id", how="left", suffixes=("", "_manifest"))
    if "manual_check_status" not in rows.columns:
        rows["manual_check_status"] = "unchecked"
    if "recommended_check_priority" not in rows.columns:
        rows["recommended_check_priority"] = "medium"
    rows["_manual_status"] = rows["manual_check_status"].fillna("unchecked").astype(str).str.lower()
    rows = rows[~rows["_manual_status"].isin({"fail", "failed", "manual_fail"})].copy()
    rows["_priority_rank"] = rows["recommended_check_priority"].map({"high": 0, "medium": 1, "low": 2}).fillna(3)
    rows["_sample_id"] = rows["sample_id"].astype(str)
    rows["_target_key"] = rows.apply(_target_key, axis=1)
    ordered = rows.sort_values(["_priority_rank", "_sample_id"])
    first_pass = ordered.head(min(5, num_samples))
    if len(first_pass) >= num_samples:
        selected = first_pass
    else:
        selected_indices = list(first_pass.index)
        remaining = rows.drop(index=selected_indices)
        grouped = {str(target): group.sort_values(["_priority_rank", "_sample_id"]) for target, group in remaining.groupby("_target_key")}
        target_order = sorted(grouped, key=lambda target: (int(grouped[target]["_priority_rank"].min()), target))
        while len(selected_indices) < num_samples:
            added = False
            for target in target_order:
                bucket = grouped[target]
                already = sum(1 for idx in selected_indices if idx in set(bucket.index))
                if already < len(bucket):
                    selected_indices.append(int(bucket.index[already]))
                    added = True
                    if len(selected_indices) >= num_samples:
                        break
            if not added:
                break
        selected = rows.loc[selected_indices]
    return selected.drop(columns=[c for c in selected.columns if c.startswith("_")]).reset_index(drop=True)


def generate_visual_check_assets(
    visual_check: pd.DataFrame,
    manifest: pd.DataFrame,
    *,
    output_root: str | Path,
    notes_path: str | Path,
    num_samples: int = 10,
) -> pd.DataFrame:
    selected = select_visual_check_samples(visual_check, manifest, num_samples=num_samples)
    output_dir = ensure_dir(output_root)
    asset_rows: list[dict[str, Any]] = []
    for _, row in selected.iterrows():
        sample_id = str(row["sample_id"])
        sample_dir = ensure_dir(output_dir / sample_id)
        processed_path = Path(str(row.get("processed_path") or ""))
        sample = _load_sample(processed_path)
        image_path = sample_dir / "projection.png"
        pymol_path = sample_dir / "view.pml"
        chimerax_path = sample_dir / "view.cxc"

        protein_local, ligand_local, copy_status = _copy_structure_files(row, sample_dir)
        image_status = _write_projection_image(sample, image_path)
        _write_pymol_script(pymol_path, protein_path=protein_local, ligand_path=ligand_local, image_path=Path("pymol.png"))
        _write_chimerax_script(chimerax_path, protein_path=protein_local, ligand_path=ligand_local, image_path=Path("chimerax.png"))

        asset_rows.append(
            {
                "complex_id": row.get("complex_id", sample_id),
                "sample_id": sample_id,
                "target_id": _first_nonempty(row.get("target_id"), row.get("split_group"), ""),
                "recommended_check_priority": row.get("recommended_check_priority", ""),
                "processed_path": str(processed_path),
                "asset_dir": str(sample_dir),
                "local_protein_path": str(sample_dir / protein_local) if protein_local else "",
                "local_ligand_path": str(sample_dir / ligand_local) if ligand_local else "",
                "copy_status": copy_status,
                "projection_png": str(image_path) if image_path.exists() else "",
                "projection_status": image_status,
                "pymol_script": str(pymol_path),
                "chimerax_script": str(chimerax_path),
                "manual_check_status": "requires_human_review",
                "notes": "Generated visual check assets; no headless PyMOL/ChimeraX visual judgement was performed.",
            }
        )

    assets = pd.DataFrame(asset_rows)
    notes_file = Path(notes_path)
    ensure_dir(notes_file.parent)
    notes_file.write_text(visual_check_notes_markdown(assets), encoding="utf-8")
    return assets


def visual_check_notes_markdown(assets: pd.DataFrame) -> str:
    count = len(assets)
    pass_count = 0
    fail_count = 0
    uncertain_count = 0
    requires_count = count
    lines = [
        "# 阶段 0 人工可视化抽查记录",
        "",
        "## 总体结论",
        "",
        f"- 检查样本数: {count}.",
        f"- pass: {pass_count}.",
        f"- fail: {fail_count}.",
        f"- uncertain: {uncertain_count}.",
        f"- requires_human_review: {requires_count}.",
        "- 是否发现系统性错误: 未发现可由自动脚本确认的系统性错误; 仍需人工查看图片或分子可视化软件确认.",
        "- 是否建议进入阶段 1 前继续修阶段 0: 若人工抽查未完成, 不建议把数据质量签字视为完成.",
        "",
        "## 单样本记录",
        "",
        "| complex_id | target_id | ligand_in_pocket | pocket_ok | scaffold_ok | rgroups_ok | anchors_ok | obvious_clash | result | notes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, row in assets.iterrows():
        notes = (
            "requires human review; assets: "
            f"`{row.get('asset_dir')}`; copy_status={row.get('copy_status')}; "
            f"projection_status={row.get('projection_status')}"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("complex_id", "")),
                    str(row.get("target_id", "")),
                    "requires_human_review",
                    "requires_human_review",
                    "requires_human_review",
                    "requires_human_review",
                    "requires_human_review",
                    "requires_human_review",
                    "requires_human_review",
                    notes,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 复现命令",
            "",
            "如本机安装 PyMOL, 可在每个样本目录运行:",
            "",
            "```bash",
            "pymol -cq view.pml",
            "```",
            "",
            "如本机安装 ChimeraX, 可在每个样本目录运行:",
            "",
            "```bash",
            "chimerax view.cxc",
            "```",
            "",
            "`view.cxc` 和 `view.pml` 使用相对路径. 下载某个样本目录到本地后, 只要 `protein.pdb`, `ligand.sdf` 和脚本在同一目录, 即可直接打开.",
            "",
            "当前记录没有把自动生成图片解释为人工 pass; 需要研究者实际查看后再把状态改为 pass / fail / uncertain.",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_sample(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return pickle.load(f)


def _write_projection_image(sample: dict[str, Any], image_path: Path) -> str:
    if not sample:
        return "missing_processed_sample"
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - depends on optional plotting backend
        return f"matplotlib_unavailable:{exc}"

    ligand = sample.get("ligand", {})
    pocket = sample.get("pocket", {})
    ligand_coords = np.asarray(ligand.get("coords"))
    pocket_coords = np.asarray(pocket.get("coords"))
    if ligand_coords.ndim != 2 or ligand_coords.shape[1] != 3:
        return "invalid_ligand_coords"
    if pocket_coords.ndim != 2 or pocket_coords.shape[1] != 3:
        return "invalid_pocket_coords"

    scaffold_indices = set(int(i) for i in sample.get("scaffold", {}).get("atom_indices", []))
    valid_rgroup_indices: set[int] = set()
    anchor_indices: set[int] = set()
    for rgroup in sample.get("rgroups", []):
        if rgroup.get("is_valid_for_phase0"):
            valid_rgroup_indices.update(int(i) for i in rgroup.get("heavy_atom_indices", []))
        for key in ["anchor_scaffold_atom_idx", "anchor_rgroup_atom_idx"]:
            value = rgroup.get(key)
            if value is not None:
                anchor_indices.add(int(value))

    ligand_indices = np.arange(len(ligand_coords))
    scaffold_mask = np.asarray([idx in scaffold_indices for idx in ligand_indices])
    rgroup_mask = np.asarray([idx in valid_rgroup_indices for idx in ligand_indices])
    anchor_mask = np.asarray([idx in anchor_indices for idx in ligand_indices])

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), constrained_layout=True)
    projections = [("x", "y", 0, 1), ("x", "z", 0, 2), ("y", "z", 1, 2)]
    for ax, (xlabel, ylabel, i, j) in zip(axes, projections, strict=True):
        ax.scatter(pocket_coords[:, i], pocket_coords[:, j], s=8, c="#A8A8A8", alpha=0.45, label="pocket")
        ax.scatter(ligand_coords[:, i], ligand_coords[:, j], s=28, c="#2D6CDF", label="ligand")
        if scaffold_mask.any():
            ax.scatter(
                ligand_coords[scaffold_mask, i],
                ligand_coords[scaffold_mask, j],
                s=42,
                c="#2D6CDF",
                edgecolors="#111111",
                linewidths=0.5,
                label="scaffold",
            )
        if rgroup_mask.any():
            ax.scatter(ligand_coords[rgroup_mask, i], ligand_coords[rgroup_mask, j], s=50, c="#F28E2B", label="valid R-group")
        if anchor_mask.any():
            ax.scatter(
                ligand_coords[anchor_mask, i],
                ligand_coords[anchor_mask, j],
                s=70,
                c="#D62728",
                marker="x",
                linewidths=1.5,
                label="anchor",
            )
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True, linewidth=0.3, alpha=0.3)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, frameon=False)
    fig.suptitle(str(sample.get("sample_id", "phase0 visual check")), y=1.06)
    ensure_dir(image_path.parent)
    fig.savefig(image_path, dpi=180)
    plt.close(fig)
    return "projection_png_generated"


def _copy_structure_files(row: pd.Series, sample_dir: Path) -> tuple[str, str, str]:
    protein_src = Path(str(row.get("protein_path") or ""))
    ligand_src = Path(str(row.get("ligand_path") or ""))
    protein_name = "protein.pdb" if protein_src.suffix.lower() != ".cif" else "protein.cif"
    ligand_name = "ligand.sdf"
    statuses: list[str] = []
    if protein_src.exists():
        shutil.copy2(protein_src, sample_dir / protein_name)
        statuses.append("protein_copied")
    else:
        protein_name = ""
        statuses.append("protein_missing")
    if ligand_src.exists():
        shutil.copy2(ligand_src, sample_dir / ligand_name)
        statuses.append("ligand_copied")
    else:
        ligand_name = ""
        statuses.append("ligand_missing")
    return protein_name, ligand_name, ",".join(statuses)


def _write_pymol_script(script_path: Path, *, protein_path: str, ligand_path: str, image_path: Path) -> None:
    content = f"""reinitialize
load {protein_path}, protein
load {ligand_path}, ligand
hide everything
show cartoon, protein
show sticks, protein within 8 of ligand
show sticks, ligand
color gray70, protein
color tv_orange, ligand
zoom ligand, 12
png {image_path}, width=1600, height=1200, ray=1
"""
    ensure_dir(script_path.parent)
    script_path.write_text(content, encoding="utf-8")


def _write_chimerax_script(script_path: Path, *, protein_path: str, ligand_path: str, image_path: Path) -> None:
    content = f"""open {protein_path}
open {ligand_path}
hide atoms #1
show cartoons #1
show atoms #2
style #2 stick
color #1 gray
color #2 orange
view #2
save {image_path} width 1600 height 1200
"""
    ensure_dir(script_path.parent)
    script_path.write_text(content, encoding="utf-8")


def _target_key(row: pd.Series) -> str:
    return str(_first_nonempty(row.get("target_id"), row.get("split_group"), row.get("pdb_id"), row.get("complex_id"), row.get("sample_id")))


def _first_nonempty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except TypeError:
            pass
        if str(value).strip() == "":
            continue
        return value
    return ""
