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
        overview_path = sample_dir / "view_overview.cxc"
        clash_path = sample_dir / "view_clash.cxc"
        rgroup_path = sample_dir / "view_rgroup.cxc"
        ligand_path = sample_dir / "view_ligand.cxc"

        protein_local, ligand_local, copy_status = _copy_structure_files(row, sample_dir)
        marker_status = _write_chimerax_marker_files(sample, sample_dir)
        image_status = _write_projection_image(sample, image_path)
        _write_pymol_script(pymol_path, protein_path=protein_local, ligand_path=ligand_local, image_path=Path("pymol.png"))
        _write_chimerax_overview_script(overview_path, protein_path=protein_local, ligand_path=ligand_local)
        _write_chimerax_clash_script(clash_path, protein_path=protein_local, ligand_path=ligand_local)
        _write_chimerax_rgroup_script(rgroup_path, protein_path=protein_local, ligand_path=ligand_local)
        _write_chimerax_ligand_script(ligand_path, ligand_path=ligand_local)
        _write_chimerax_main_script(chimerax_path, protein_path=protein_local, ligand_path=ligand_local)
        _write_visual_readme(sample_dir)

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
                "marker_status": marker_status,
                "projection_png": str(image_path) if image_path.exists() else "",
                "projection_status": image_status,
                "pymol_script": str(pymol_path),
                "chimerax_script": str(chimerax_path),
                "chimerax_overview_script": str(overview_path),
                "chimerax_clash_script": str(clash_path),
                "chimerax_rgroup_script": str(rgroup_path),
                "chimerax_ligand_script": str(ligand_path),
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
            f"marker_status={row.get('marker_status')}; "
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
            "推荐在 ChimeraX 中按顺序打开 `view_overview.cxc`, `view_clash.cxc`, `view_rgroup.cxc`, `view_ligand.cxc`.",
            "`view_clash.cxc` 会叠加灰色 protein vdW sphere, royalblue ligand vdW sphere, 黑色 silhouette 轮廓和 close-contact 红色标记, 便于判断是否存在肉眼明显严重重叠; `view_rgroup.cxc` 和 `view_ligand.cxc` 会叠加 scaffold, valid R-group 和 valid anchor 标记层.",
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
    _write_chimerax_main_script(script_path, protein_path=protein_path, ligand_path=ligand_path)


def _write_chimerax_main_script(script_path: Path, *, protein_path: str, ligand_path: str) -> None:
    content = f"""# Phase 0 visual check entrypoint.
# Recommended order:
# 1. open view_overview.cxc
# 2. open view_clash.cxc
# 3. open view_rgroup.cxc
# 4. open view_ligand.cxc

open {protein_path}
open {ligand_path}
set bgColor white
lighting soft
camera ortho
ui tool show "Side View"
hide #1 atoms
show #1 cartoons
show #2 atoms
style #2 stick
color #1 gray
color #2 orange
view
"""
    ensure_dir(script_path.parent)
    script_path.write_text(content, encoding="utf-8")


def _write_chimerax_overview_script(script_path: Path, *, protein_path: str, ligand_path: str) -> None:
    content = f"""# Overview: ligand placement inside pocket-level protein.
open {protein_path}
open {ligand_path}
set bgColor white
lighting soft
camera ortho
ui tool show "Side View"
hide #1 atoms
show #1 cartoons
surface #1
transparency #1 70
show #2 atoms
style #2 stick
color #1 gray
color #2 orange
view
save overview.png width 1800 height 1400
"""
    ensure_dir(script_path.parent)
    script_path.write_text(content, encoding="utf-8")


def _write_chimerax_clash_script(script_path: Path, *, protein_path: str, ligand_path: str) -> None:
    content = f"""# Clash sanity view: sticks plus translucent vdW spheres.
# This is for visual sanity only, not a formal vdW clash detector.
# Model guide:
# #1 protein pocket, #2 ligand, #3 protein pocket vdW atoms, #4 ligand vdW atoms, #5 close-contact markers.
open {protein_path}
open {ligand_path}
open protein_pocket_vdw_atoms.pdb
open ligand_vdw_atoms.pdb
open close_contacts.bild
set bgColor white
lighting soft
camera ortho
ui tool show "Side View"
graphics silhouettes true width 1.5 depthJump 0.01
hide #1 cartoons
show #1 atoms
show #2 atoms
show #3 atoms
show #4 atoms
style #1 stick
style #2 stick
style #3 sphere
style #4 sphere
color #1 gray
color #2 orange
color #3 gray
color #4 royalblue
transparency #1 70 target a
transparency #3 45 target a
transparency #4 25 target a
view
save clash.png width 1800 height 1400
"""
    ensure_dir(script_path.parent)
    script_path.write_text(content, encoding="utf-8")


def _write_chimerax_rgroup_script(script_path: Path, *, protein_path: str, ligand_path: str) -> None:
    content = f"""# R-group view: ligand sticks plus scaffold/R-group/anchor marker overlays.
# Model guide:
# #1 protein pocket, #2 ligand, #3 scaffold markers, #4 valid R-group markers, #5 valid anchor connections.
open {protein_path}
open {ligand_path}
open scaffold_atoms.pdb
open valid_rgroup_atoms.pdb
open valid_anchors.bild
set bgColor white
lighting soft
camera ortho
ui tool show "Side View"
hide #1 atoms
show #1 cartoons
surface #1
transparency #1 97 target s
show #2 atoms
style #2 stick
color #1 gray
color #2 gray
show #3 atoms
show #4 atoms
style #3 sphere
style #4 sphere
size #3 atomRadius 0.35
size #4 atomRadius 0.35
color #3 blue
color #4 orange
view
save rgroup.png width 1800 height 1400
"""
    ensure_dir(script_path.parent)
    script_path.write_text(content, encoding="utf-8")


def _write_chimerax_ligand_script(script_path: Path, *, ligand_path: str) -> None:
    content = f"""# Ligand-only view: scaffold, valid R-groups, and valid anchors without protein clutter.
# Model guide:
# #1 ligand, #2 scaffold markers, #3 valid R-group markers, #4 valid anchor connections.
open {ligand_path}
open scaffold_atoms.pdb
open valid_rgroup_atoms.pdb
open valid_anchors.bild
set bgColor white
lighting soft
camera ortho
ui tool show "Side View"
show #1 atoms
style #1 stick
color #1 gray
show #2 atoms
show #3 atoms
style #2 sphere
style #3 sphere
size #2 atomRadius 0.35
size #3 atomRadius 0.35
color #2 blue
color #3 orange
view
save ligand_only.png width 1800 height 1400
"""
    ensure_dir(script_path.parent)
    script_path.write_text(content, encoding="utf-8")


def _write_chimerax_marker_files(sample: dict[str, Any], sample_dir: Path) -> str:
    if not sample:
        _write_marker_pdb(sample_dir / "scaffold_atoms.pdb", [])
        _write_marker_pdb(sample_dir / "valid_rgroup_atoms.pdb", [])
        _write_anchor_bild(sample_dir / "valid_anchors.bild", [])
        _write_atom_cloud_pdb(sample_dir / "protein_pocket_vdw_atoms.pdb", [], [], "PRO")
        _write_atom_cloud_pdb(sample_dir / "ligand_vdw_atoms.pdb", [], [], "LIG")
        _write_close_contacts_bild(sample_dir / "close_contacts.bild", [])
        return "missing_processed_sample"

    ligand_coords = np.asarray(sample.get("ligand", {}).get("coords"))
    if ligand_coords.ndim != 2 or ligand_coords.shape[1] != 3:
        _write_marker_pdb(sample_dir / "scaffold_atoms.pdb", [])
        _write_marker_pdb(sample_dir / "valid_rgroup_atoms.pdb", [])
        _write_anchor_bild(sample_dir / "valid_anchors.bild", [])
        _write_atom_cloud_pdb(sample_dir / "protein_pocket_vdw_atoms.pdb", [], [], "PRO")
        _write_atom_cloud_pdb(sample_dir / "ligand_vdw_atoms.pdb", [], [], "LIG")
        _write_close_contacts_bild(sample_dir / "close_contacts.bild", [])
        return "invalid_ligand_coords"

    ligand_elements = [str(e) for e in sample.get("ligand", {}).get("elements", [])]
    pocket_coords = np.asarray(sample.get("pocket", {}).get("coords"))
    pocket_elements = [str(e) for e in sample.get("pocket", {}).get("elements", [])]

    scaffold_indices = [int(i) for i in sample.get("scaffold", {}).get("atom_indices", [])]
    valid_rgroup_indices: list[int] = []
    valid_anchor_pairs: list[tuple[int, int]] = []
    for rgroup in sample.get("rgroups", []):
        if not rgroup.get("is_valid_for_phase0"):
            continue
        valid_rgroup_indices.extend(int(i) for i in rgroup.get("heavy_atom_indices", []))
        scaffold_idx = rgroup.get("anchor_scaffold_atom_idx")
        rgroup_idx = rgroup.get("anchor_rgroup_atom_idx")
        if scaffold_idx is not None and rgroup_idx is not None:
            valid_anchor_pairs.append((int(scaffold_idx), int(rgroup_idx)))

    _write_marker_pdb(
        sample_dir / "scaffold_atoms.pdb",
        [(idx, ligand_coords[idx], "SCA") for idx in scaffold_indices if 0 <= idx < len(ligand_coords)],
    )
    _write_marker_pdb(
        sample_dir / "valid_rgroup_atoms.pdb",
        [(idx, ligand_coords[idx], "RGP") for idx in sorted(set(valid_rgroup_indices)) if 0 <= idx < len(ligand_coords)],
    )
    anchors = [
        (ligand_coords[scaffold_idx], ligand_coords[rgroup_idx])
        for scaffold_idx, rgroup_idx in valid_anchor_pairs
        if 0 <= scaffold_idx < len(ligand_coords) and 0 <= rgroup_idx < len(ligand_coords)
    ]
    _write_anchor_bild(sample_dir / "valid_anchors.bild", anchors)

    protein_vdw_atoms = _heavy_atom_cloud(pocket_coords, pocket_elements)
    ligand_vdw_atoms = _heavy_atom_cloud(ligand_coords, ligand_elements)
    _write_atom_cloud_pdb(sample_dir / "protein_pocket_vdw_atoms.pdb", protein_vdw_atoms, pocket_elements, "PRO")
    _write_atom_cloud_pdb(sample_dir / "ligand_vdw_atoms.pdb", ligand_vdw_atoms, ligand_elements, "LIG")
    close_contacts = _close_contact_segments(
        ligand_atoms=ligand_vdw_atoms,
        protein_atoms=protein_vdw_atoms,
        distance_threshold=1.8,
    )
    _write_close_contacts_bild(sample_dir / "close_contacts.bild", close_contacts)
    return (
        f"scaffold_atoms={len(scaffold_indices)},"
        f"valid_rgroup_atoms={len(set(valid_rgroup_indices))},"
        f"valid_anchor_connections={len(anchors)},"
        f"protein_vdw_atoms={len(protein_vdw_atoms)},"
        f"ligand_vdw_atoms={len(ligand_vdw_atoms)},"
        f"visual_close_contacts={len(close_contacts)}"
    )


def _write_marker_pdb(path: Path, atoms: list[tuple[int, np.ndarray, str]]) -> None:
    lines: list[str] = []
    for serial, (atom_index, coord, residue_name) in enumerate(atoms, start=1):
        x, y, z = (float(coord[0]), float(coord[1]), float(coord[2]))
        atom_name = f"C{(atom_index + 1) % 1000:03d}"[:4]
        lines.append(
            f"HETATM{serial:5d} {atom_name:<4s} {residue_name:>3s} V{1:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}{1.00:6.2f}{20.00:6.2f}           C"
        )
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_atom_cloud_pdb(
    path: Path,
    atoms: list[tuple[int, np.ndarray, str]],
    fallback_elements: list[str],
    residue_name: str,
) -> None:
    lines: list[str] = []
    for serial, (atom_index, coord, element) in enumerate(atoms, start=1):
        x, y, z = (float(coord[0]), float(coord[1]), float(coord[2]))
        clean_element = _clean_element(element)
        if not clean_element and 0 <= atom_index < len(fallback_elements):
            clean_element = _clean_element(fallback_elements[atom_index])
        if not clean_element:
            clean_element = "C"
        atom_name = f"{clean_element}{(atom_index + 1) % 1000:03d}"[:4]
        lines.append(
            f"HETATM{serial:5d} {atom_name:<4s} {residue_name:>3s} V{1:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}{1.00:6.2f}{20.00:6.2f}          {clean_element:>2s}"
        )
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_anchor_bild(path: Path, anchors: list[tuple[np.ndarray, np.ndarray]]) -> None:
    lines = ["# Valid single-anchor R-group connections", ".color red"]
    for start, end in anchors:
        sx, sy, sz = (float(start[0]), float(start[1]), float(start[2]))
        ex, ey, ez = (float(end[0]), float(end[1]), float(end[2]))
        lines.append(f".sphere {sx:.3f} {sy:.3f} {sz:.3f} 0.30")
        lines.append(f".sphere {ex:.3f} {ey:.3f} {ez:.3f} 0.30")
        lines.append(f".cylinder {sx:.3f} {sy:.3f} {sz:.3f} {ex:.3f} {ey:.3f} {ez:.3f} 0.08")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_close_contacts_bild(path: Path, contacts: list[tuple[np.ndarray, np.ndarray, float]]) -> None:
    lines = ["# Visual close-contact markers for phase0 manual sanity only", ".color red"]
    for ligand_coord, protein_coord, distance in contacts:
        lx, ly, lz = (float(ligand_coord[0]), float(ligand_coord[1]), float(ligand_coord[2]))
        px, py, pz = (float(protein_coord[0]), float(protein_coord[1]), float(protein_coord[2]))
        radius = 0.10 if distance < 1.5 else 0.07
        lines.append(f".sphere {lx:.3f} {ly:.3f} {lz:.3f} 0.22")
        lines.append(f".sphere {px:.3f} {py:.3f} {pz:.3f} 0.22")
        lines.append(f".cylinder {lx:.3f} {ly:.3f} {lz:.3f} {px:.3f} {py:.3f} {pz:.3f} {radius:.2f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _heavy_atom_cloud(coords: np.ndarray, elements: list[str]) -> list[tuple[int, np.ndarray, str]]:
    if coords.ndim != 2 or coords.shape[1] != 3:
        return []
    atoms: list[tuple[int, np.ndarray, str]] = []
    for idx, coord in enumerate(coords):
        element = elements[idx] if idx < len(elements) else ""
        clean_element = _clean_element(element)
        if clean_element == "H":
            continue
        if not np.isfinite(coord).all():
            continue
        atoms.append((idx, coord, clean_element or "C"))
    return atoms


def _close_contact_segments(
    *,
    ligand_atoms: list[tuple[int, np.ndarray, str]],
    protein_atoms: list[tuple[int, np.ndarray, str]],
    distance_threshold: float,
    max_contacts: int = 80,
) -> list[tuple[np.ndarray, np.ndarray, float]]:
    contacts: list[tuple[np.ndarray, np.ndarray, float]] = []
    if not ligand_atoms or not protein_atoms:
        return contacts
    protein_coords = np.asarray([atom[1] for atom in protein_atoms], dtype=float)
    for _, ligand_coord, _ in ligand_atoms:
        distances = np.linalg.norm(protein_coords - np.asarray(ligand_coord, dtype=float), axis=1)
        close_indices = np.where(distances < distance_threshold)[0]
        for protein_idx in close_indices:
            contacts.append((ligand_coord, protein_atoms[int(protein_idx)][1], float(distances[int(protein_idx)])))
    contacts.sort(key=lambda item: item[2])
    return contacts[:max_contacts]


def _clean_element(element: str) -> str:
    text = "".join(ch for ch in str(element).strip() if ch.isalpha())
    if not text:
        return ""
    text = text[:2]
    if len(text) == 1:
        return text.upper()
    return text[0].upper() + text[1].lower()


def _write_visual_readme(sample_dir: Path) -> None:
    content = """# Phase 0 Visual Check Package

Open these ChimeraX scripts from this directory:

```bash
chimerax view_overview.cxc
chimerax view_clash.cxc
chimerax view_rgroup.cxc
chimerax view_ligand.cxc
```

- `view_overview.cxc`: protein cartoon + transparent pocket surface + ligand sticks, for ligand-in-pocket sanity.
- `view_clash.cxc`: pale protein sticks, orange ligand sticks, gray protein vdW spheres, royalblue ligand vdW spheres, black silhouette outlines, and red close-contact markers for obvious severe overlap sanity.
- `view_rgroup.cxc`: transparent protein context + ligand sticks + scaffold/R-group/anchor marker overlays.
- `view_ligand.cxc`: ligand-only scaffold/R-group/anchor view, for checking the decomposition without protein clutter.

This package is for manual visual checking only. It does not replace the formal stage 1 clash detector.
"""
    (sample_dir / "README.md").write_text(content, encoding="utf-8")


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
