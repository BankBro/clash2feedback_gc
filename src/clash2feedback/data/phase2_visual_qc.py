from __future__ import annotations

import json
import os
import pickle
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from clash2feedback.data.render_visual_check import DEFAULT_CANDIDATE_DIRECTIONS, CameraView, select_clear_camera_views
from clash2feedback.geometry.vdw import get_vdw_radius
from clash2feedback.utils.files import ensure_dir


DEFAULT_PHASE2_VISUAL_QC_VIEWS = (
    "ligand_delta",
    "overlay_sticks",
    "overlay_surface",
    "clash_pair_vdw",
)
PHASE2_VISUAL_QC_VIEWS = (*DEFAULT_PHASE2_VISUAL_QC_VIEWS, "clash", "rgroup")
DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES = 30.0
DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES = 90.0
CAMERA_FOCUS_HELPER_NAME = "center_camera_on_focus.py"

VISUAL_QC_RGB = {
    "protein": (135, 135, 135),
    "protein_surface": (145, 145, 145),
    "original_ligand": (185, 185, 185),
    "failed_ligand": (230, 155, 0),
    "scaffold": (0, 70, 220),
    "target_original": (150, 0, 160),
    "target_failed": (0, 180, 210),
    "target_displacement": (0, 150, 110),
    "ligand_clash": (220, 0, 0),
    "protein_clash": (65, 115, 255),
    "clash_line": (70, 70, 70),
    "non_target": (0, 140, 20),
    "anchor": (220, 0, 220),
}

VISUAL_QC_CHIMERAX_COLOR = {
    "protein": "gray",
    "original_ligand": "lightgray",
    "failed_ligand": "orange",
    "scaffold": "blue",
    "target_original": "purple",
    "target_failed": "cyan",
    "ligand_clash": "red",
    "protein_clash": "royalblue",
    "clash_line": "black",
    "non_target": "green",
    "anchor": "magenta",
}

VISUAL_QC_BILD_COLOR = {
    "target_displacement": ".color 0.00 0.58 0.42",
    "ligand_clash": ".color red",
    "protein_clash": ".color 0.25 0.45 1.0",
    "clash_line": ".color 0.28 0.28 0.28",
}

VIEW_SELECTION = {
    "clash": ("clash", "failed"),
    "ligand_delta": ("ligand", "union"),
    "rgroup": ("rgroup", "failed"),
    "overlay_sticks": ("rgroup", "union"),
    "overlay_surface": ("overview", "union"),
    "clash_pair_vdw": ("clash", "failed"),
}

VIEW_LEGENDS = {
    "clash": [
        ("蛋白口袋", VISUAL_QC_RGB["protein"]),
        ("失败构象配体", VISUAL_QC_RGB["failed_ligand"]),
        ("目标R基团失败位置", VISUAL_QC_RGB["target_failed"]),
        ("配体侧碰撞点", VISUAL_QC_RGB["ligand_clash"]),
        ("蛋白侧碰撞点", VISUAL_QC_RGB["protein_clash"]),
        ("碰撞中心连线", VISUAL_QC_RGB["clash_line"]),
    ],
    "ligand_delta": [
        ("原始配体", VISUAL_QC_RGB["original_ligand"]),
        ("失败构象配体", VISUAL_QC_RGB["failed_ligand"]),
        ("骨架标记", VISUAL_QC_RGB["scaffold"]),
        ("目标R基团原始位置", VISUAL_QC_RGB["target_original"]),
        ("目标R基团失败位置", VISUAL_QC_RGB["target_failed"]),
        ("目标R基团位移", VISUAL_QC_RGB["target_displacement"]),
    ],
    "rgroup": [
        ("失败构象配体", VISUAL_QC_RGB["failed_ligand"]),
        ("骨架标记", VISUAL_QC_RGB["scaffold"]),
        ("目标R基团失败位置", VISUAL_QC_RGB["target_failed"]),
        ("非目标R基团", VISUAL_QC_RGB["non_target"]),
        ("锚点原子", VISUAL_QC_RGB["anchor"]),
    ],
    "overlay_sticks": [
        ("蛋白口袋", VISUAL_QC_RGB["protein"]),
        ("原始配体", VISUAL_QC_RGB["original_ligand"]),
        ("失败构象配体", VISUAL_QC_RGB["failed_ligand"]),
        ("骨架标记", VISUAL_QC_RGB["scaffold"]),
        ("目标R基团原始位置", VISUAL_QC_RGB["target_original"]),
        ("目标R基团失败位置", VISUAL_QC_RGB["target_failed"]),
        ("目标R基团位移", VISUAL_QC_RGB["target_displacement"]),
        ("配体侧碰撞点", VISUAL_QC_RGB["ligand_clash"]),
        ("蛋白侧碰撞点", VISUAL_QC_RGB["protein_clash"]),
        ("碰撞中心连线", VISUAL_QC_RGB["clash_line"]),
    ],
    "overlay_surface": [
        ("蛋白表面", VISUAL_QC_RGB["protein_surface"]),
        ("原始配体", VISUAL_QC_RGB["original_ligand"]),
        ("失败构象配体", VISUAL_QC_RGB["failed_ligand"]),
        ("目标R基团原始位置", VISUAL_QC_RGB["target_original"]),
        ("目标R基团失败位置", VISUAL_QC_RGB["target_failed"]),
        ("配体侧严重碰撞点", VISUAL_QC_RGB["ligand_clash"]),
    ],
    "clash_pair_vdw": [
        ("蛋白口袋背景", VISUAL_QC_RGB["protein"]),
        ("失败构象配体背景", VISUAL_QC_RGB["failed_ligand"]),
        ("蛋白碰撞原子VDW球", VISUAL_QC_RGB["protein_clash"]),
        ("配体碰撞原子VDW球", VISUAL_QC_RGB["ligand_clash"]),
        ("碰撞原子中心连线", VISUAL_QC_RGB["clash_line"]),
    ],
}


@dataclass(frozen=True)
class Phase2RenderTask:
    case_id: str
    view: str
    case_dir: Path
    script_path: Path
    cameras: tuple[CameraView, ...]
    candidate_directions: int


@dataclass(frozen=True)
class TargetDisplacementCameraGeometry:
    focus: np.ndarray
    axis: np.ndarray | None


def build_phase2_visual_qc_assets(
    *,
    visual_qc_cases_path: str | Path,
    manifest_path: str | Path,
    benchmark_root: str | Path,
    processed_root: str | Path,
    output_root: str | Path,
    case_ids: Iterable[str] | None = None,
    max_cases: int | None = None,
    views: Iterable[str] = DEFAULT_PHASE2_VISUAL_QC_VIEWS,
    num_clear_views: int = 12,
    candidate_directions: int = DEFAULT_CANDIDATE_DIRECTIONS,
) -> tuple[pd.DataFrame, list[Phase2RenderTask]]:
    visual_df = pd.read_csv(visual_qc_cases_path)
    manifest_df = pd.read_parquet(manifest_path)
    selected = _select_cases(visual_df, case_ids=case_ids, max_cases=max_cases)
    view_list = _validate_views(views)
    benchmark_root = Path(benchmark_root)
    processed_root = Path(processed_root)
    output_root = ensure_dir(output_root)

    asset_rows: list[dict[str, Any]] = []
    tasks: list[Phase2RenderTask] = []
    manifest_by_case = {str(row["case_id"]): row.to_dict() for _, row in manifest_df.iterrows()}
    for _, visual_row in selected.iterrows():
        case_id = str(visual_row["case_id"])
        if case_id not in manifest_by_case:
            raise ValueError(f"case_id from visual QC list is missing from manifest: {case_id}")
        manifest_row = manifest_by_case[case_id]
        case_dir = ensure_dir(output_root / case_id)
        ensure_dir(case_dir / "images")
        ensure_dir(case_dir / "scripts")
        case_payload = _load_pickle(benchmark_root / str(visual_row["sample_path"]))
        base_sample_id = str(case_payload["base_sample"]["sample_id"])
        base_sample = _load_pickle(processed_root / f"{base_sample_id}.pkl")

        _write_case_assets(case_dir, benchmark_root, visual_row.to_dict(), manifest_row, case_payload, base_sample)
        case_tasks = _build_case_render_tasks(
            case_id=case_id,
            case_dir=case_dir,
            views=view_list,
            num_clear_views=num_clear_views,
            candidate_directions=candidate_directions,
        )
        tasks.extend(case_tasks)
        asset_rows.append(
            {
                "case_id": case_id,
                "oracle_split": str(manifest_row.get("oracle_split", "")),
                "injection_mode": str(manifest_row.get("injection_mode", "")),
                "target_rgroup": str(manifest_row.get("target_rgroup", "")),
                "target_num_severe_pairs": int(manifest_row.get("target_num_severe_pairs", 0)),
                "non_target_num_severe_pairs": int(manifest_row.get("non_target_num_severe_pairs", 0)),
                "scaffold_num_severe_pairs": int(manifest_row.get("scaffold_num_severe_pairs", 0)),
                "max_clash_depth": float(manifest_row.get("max_clash_depth", 0.0)),
                "energy_delta": manifest_row.get("energy_delta", ""),
                "top_clash_residue": str(manifest_row.get("top_clash_residue", "")),
                "asset_dir": str(case_dir),
                "num_render_tasks": sum(len(task.cameras) for task in case_tasks),
                "num_clear_views": int(num_clear_views),
                "candidate_directions": int(candidate_directions),
                "displacement_axis_min_angle_degrees": DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES,
                "displacement_axis_max_angle_degrees": DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES,
                "manual_qc_status": "pending_manual_review",
            }
        )
    return pd.DataFrame(asset_rows), tasks


def render_phase2_visual_qc_tasks(
    tasks: Iterable[Phase2RenderTask],
    *,
    chimerax: str = "chimerax",
    dry_run: bool = False,
    skip_existing: bool = False,
    width: int = 1600,
    height: int = 1200,
    timeout_seconds: int = 240,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for task in tasks:
        if dry_run:
            _write_group_script(task, width=width, height=height)
            rows.extend(_render_rows(task, status="script_written", render_action="dry_run"))
            continue
        if skip_existing and _task_images_exist(task):
            rows.extend(_render_rows(task, status="rendered", render_action="skipped_existing", returncode=0))
            continue
        _write_group_script(task, width=width, height=height)
        completed = subprocess.run(
            [chimerax, "--nogui", "--offscreen", "--script", task.script_path.relative_to(task.case_dir).as_posix(), "--exit"],
            cwd=task.case_dir,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        stderr_tail = _tail(completed.stderr or completed.stdout)
        for camera in task.cameras:
            image_path = task.case_dir / "images" / f"{task.view}_{camera.label}.png"
            status = "rendered" if completed.returncode == 0 and image_path.exists() else "failed"
            rows.append(
                _render_row(
                    task,
                    camera,
                    image_path=image_path,
                    status=status,
                    returncode=completed.returncode,
                    stderr_tail=stderr_tail,
                    render_action="chimerax_render",
                )
            )
    return pd.DataFrame(rows)


def write_phase2_visual_qc_contact_sheets(
    render_manifest: pd.DataFrame,
    *,
    rows: int = 3,
    columns: int = 4,
) -> pd.DataFrame:
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - optional image stack
        return pd.DataFrame(
            [
                {
                    "case_id": "",
                    "view": "",
                    "contact_sheet_path": "",
                    "status": f"pillow_unavailable:{exc}",
                    "num_images": 0,
                }
            ]
        )

    sheet_rows: list[dict[str, Any]] = []
    rendered = render_manifest[render_manifest["status"] == "rendered"].copy()
    for (case_id, view), group in rendered.groupby(["case_id", "view"], sort=True):
        image_paths = [Path(path) for path in group.sort_values("angle")["image_path"]]
        images = [Image.open(path).convert("RGB") for path in image_paths if path.exists()]
        if not images:
            sheet_rows.append({"case_id": case_id, "view": view, "contact_sheet_path": "", "status": "no_images", "num_images": 0})
            continue
        thumb_w, thumb_h = 460, 345
        tile_w, tile_h = 500, 395
        max_images = max(1, rows * columns)
        images = images[:max_images]
        legend_h = 72
        case_dir = image_paths[0].parents[1]
        sheet = Image.new("RGB", (columns * tile_w, rows * tile_h + legend_h), "white")
        _draw_contact_sheet_legend(sheet, view, legend_h=legend_h, case_dir=case_dir)
        for idx, image in enumerate(images):
            image = _crop_white_border(image)
            image.thumbnail((thumb_w, thumb_h))
            tile = Image.new("RGB", (tile_w, tile_h), "white")
            tile.paste(image, ((tile_w - image.width) // 2, 32))
            draw = ImageDraw.Draw(tile)
            draw.text((12, 10), image_paths[idx].stem, fill=(0, 0, 0))
            sheet.paste(tile, ((idx % columns) * tile_w, legend_h + (idx // columns) * tile_h))
        sheet_path = case_dir / "images" / f"{view}_contact_sheet.png"
        sheet.save(sheet_path)
        sheet_rows.append(
            {
                "case_id": case_id,
                "view": view,
                "contact_sheet_path": str(sheet_path),
                "status": "written",
                "num_images": len(images),
            }
        )
    return pd.DataFrame(sheet_rows)


def _draw_contact_sheet_legend(sheet: Any, view: str, *, legend_h: int, case_dir: Path | None = None) -> None:
    try:
        from PIL import ImageDraw
    except Exception:  # pragma: no cover - optional image stack
        return
    draw = ImageDraw.Draw(sheet)
    font = _legend_font(size=13)
    title_font = _legend_font(size=14)
    draw.rectangle((0, 0, sheet.width, legend_h - 1), fill=(248, 248, 248), outline=(210, 210, 210))
    draw.text((12, 10), f"{view} 图例", fill=(0, 0, 0), font=title_font)
    x = 12
    y = 42
    for label, color in _view_legend_items(view, case_dir=case_dir):
        draw.rectangle((x, y, x + 14, y + 10), fill=color, outline=(80, 80, 80))
        draw.text((x + 20, y - 4), label, fill=(0, 0, 0), font=font)
        text_width = _text_width(draw, label, font)
        x += 20 + max(70, int(text_width) + 18)
        if x > sheet.width - 220:
            x = 12
            y += 18


def _view_legend_items(view: str, *, case_dir: Path | None = None) -> list[tuple[str, tuple[int, int, int]]]:
    if view == "clash_pair_vdw" and case_dir is not None and not _top_clash_pair_available(case_dir):
        return [
            ("蛋白口袋背景", VISUAL_QC_RGB["protein"]),
            ("失败构象配体背景", VISUAL_QC_RGB["failed_ligand"]),
            ("无可用碰撞原子对, 仅显示背景", VISUAL_QC_RGB["clash_line"]),
        ]
    return list(VIEW_LEGENDS.get(view, []))


def _legend_font(*, size: int) -> Any:
    try:
        from PIL import ImageFont
    except Exception:  # pragma: no cover - optional image stack
        return None
    for path in _cjk_font_candidates():
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _cjk_font_candidates() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[3]
    return [
        repo_root / "data/cache/fonts/NotoSansCJKsc-Regular.otf",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
    ]


def _text_width(draw: Any, text: str, font: Any) -> float:
    if hasattr(draw, "textlength"):
        return float(draw.textlength(text, font=font))
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return float(right - left)


def _crop_white_border(image: Any, *, threshold: int = 12, margin: int = 28) -> Any:
    try:
        from PIL import Image, ImageChops
    except Exception:  # pragma: no cover - optional image stack
        return image
    background = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, background).convert("L")
    mask = diff.point(lambda value: 255 if value > threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return image
    left, upper, right, lower = bbox
    left = max(0, left - margin)
    upper = max(0, upper - margin)
    right = min(image.width, right + margin)
    lower = min(image.height, lower + margin)
    if right <= left or lower <= upper:
        return image
    return image.crop((left, upper, right, lower))


def write_phase2_visual_qc_summary(
    *,
    path: str | Path,
    asset_manifest: pd.DataFrame,
    render_manifest: pd.DataFrame,
    contact_sheets: pd.DataFrame,
    output_root: str | Path,
    category_index_path: str | Path | None = None,
) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    status_counts = render_manifest["status"].value_counts().to_dict() if not render_manifest.empty else {}
    action_counts = render_manifest["render_action"].value_counts().to_dict() if "render_action" in render_manifest else {}
    candidate_counts = sorted({int(value) for value in asset_manifest.get("candidate_directions", []) if str(value) != ""})
    clear_view_counts = sorted({int(value) for value in asset_manifest.get("num_clear_views", []) if str(value) != ""})
    lines = [
        "# Phase 2 Visual QC Render Summary",
        "",
        "## 1. Status",
        "",
        f"- output_root: `{output_root}`.",
        *( [f"- category_index: `{category_index_path}`."] if category_index_path is not None else [] ),
        f"- cases: {len(asset_manifest)}.",
        f"- num_clear_views: `{clear_view_counts}`.",
        f"- candidate_directions: `{candidate_counts}`.",
        f"- displacement_axis_angle_degrees: {DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES:.1f} to {DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES:.1f}.",
        f"- render_status_counts: `{status_counts}`.",
        f"- render_action_counts: `{action_counts}`.",
        "- manual_qc_status: pending_manual_review; rendered images are aids, not automatic pass/fail decisions.",
        "",
        "## 2. Case Index",
        "",
        "| case_id | oracle_split | injection_mode | target_rgroup | max_clash_depth | contact_sheets | manual_qc_status |",
        "|---|---|---|---|---:|---|---|",
    ]
    sheets_by_case: dict[str, list[str]] = {}
    for _, row in contact_sheets.iterrows():
        if row.get("status") == "written":
            sheets_by_case.setdefault(str(row["case_id"]), []).append(str(row["contact_sheet_path"]))
    for _, row in asset_manifest.iterrows():
        links = "<br>".join(f"`{Path(sheet).as_posix()}`" for sheet in sheets_by_case.get(str(row["case_id"]), []))
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["case_id"]),
                    str(row["oracle_split"]),
                    str(row["injection_mode"]),
                    str(row["target_rgroup"]),
                    f"{float(row['max_clash_depth']):.3f}",
                    links,
                    str(row["manual_qc_status"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 3. Manual Review Guide",
            "",
            "- `ligand_delta_contact_sheet.png`: confirm original/failed difference is mainly local to target R-group.",
            "- `overlay_sticks_contact_sheet.png`: confirm original/failed overlay, target displacement guides, ligand-side clash points, protein-side clash points and center lines.",
            "- `overlay_surface_contact_sheet.png`: use pocket context plus target R-group atom markers; surface may still hide part of the ligand in some views.",
            "- `clash_pair_vdw_contact_sheet.png`: confirm the top ligand-protein clash pair overlaps as vdW spheres.",
            "- Optional legacy views `clash` and `rgroup` can still be rendered explicitly if a case needs extra debugging.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_phase2_visual_qc_category_index(
    *,
    asset_manifest: pd.DataFrame,
    output_root: str | Path,
    report_root: str | Path,
) -> pd.DataFrame:
    """Create stable visual QC symlink indexes without moving canonical case dirs."""
    output_root = ensure_dir(output_root)
    report_root = ensure_dir(report_root)
    index_path = report_root / "by_category_index.csv"

    rows: list[dict[str, str]] = []
    splits = sorted({_category_segment(value) for value in asset_manifest.get("oracle_split", [])})
    modes = sorted({_category_segment(value) for value in asset_manifest.get("injection_mode", [])})
    for split in splits:
        ensure_dir(output_root / "by_oracle_split" / split)
        for mode in modes:
            ensure_dir(output_root / "by_oracle_split_and_mode" / split / mode)
    for mode in modes:
        ensure_dir(output_root / "by_injection_mode" / mode)

    for _, row in asset_manifest.iterrows():
        case_id = str(row["case_id"])
        split = _category_segment(row.get("oracle_split", "unknown"))
        mode = _category_segment(row.get("injection_mode", "unknown"))
        case_dir = output_root / case_id
        by_split = _replace_directory_symlink(output_root / "by_oracle_split" / split / case_id, case_dir)
        by_mode = _replace_directory_symlink(output_root / "by_injection_mode" / mode / case_id, case_dir)
        by_matrix = _replace_directory_symlink(output_root / "by_oracle_split_and_mode" / split / mode / case_id, case_dir)
        rows.append(
            {
                "case_id": case_id,
                "oracle_split": split,
                "injection_mode": mode,
                "case_dir": str(case_dir),
                "by_oracle_split_link": str(by_split),
                "by_injection_mode_link": str(by_mode),
                "by_oracle_split_and_mode_link": str(by_matrix),
            }
        )

    index = pd.DataFrame(
        rows,
        columns=[
            "case_id",
            "oracle_split",
            "injection_mode",
            "case_dir",
            "by_oracle_split_link",
            "by_injection_mode_link",
            "by_oracle_split_and_mode_link",
        ],
    )
    index.to_csv(index_path, index=False)
    return index


def write_phase2_manual_review_template(path: str | Path, asset_manifest: pd.DataFrame) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    columns = [
        "case_id",
        "oracle_split",
        "injection_mode",
        "target_rgroup",
        "overlay_ok",
        "clash_location_ok",
        "scaffold_stable",
        "non_target_stable",
        "ligand_geometry_ok",
        "oracle_split_reasonable",
        "manual_qc_status",
        "manual_notes",
    ]
    rows = []
    for _, row in asset_manifest.iterrows():
        rows.append(
            {
                "case_id": row["case_id"],
                "oracle_split": row["oracle_split"],
                "injection_mode": row["injection_mode"],
                "target_rgroup": row["target_rgroup"],
                "overlay_ok": "pending",
                "clash_location_ok": "pending",
                "scaffold_stable": "pending",
                "non_target_stable": "pending",
                "ligand_geometry_ok": "pending",
                "oracle_split_reasonable": "pending",
                "manual_qc_status": "pending_manual_review",
                "manual_notes": "",
            }
        )
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def _category_segment(value: Any) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return "unknown"
    return "".join(char if char.isalnum() or char in {"_", "-", "."} else "_" for char in text)


def _replace_directory_symlink(link_path: Path, target_path: Path) -> Path:
    ensure_dir(link_path.parent)
    if link_path.is_symlink():
        link_path.unlink()
    elif link_path.exists():
        raise ValueError(f"Refusing to replace non-symlink visual QC index path: {link_path}")
    relative_target = os.path.relpath(target_path, start=link_path.parent)
    link_path.symlink_to(relative_target, target_is_directory=True)
    return link_path


def _select_cases(visual_df: pd.DataFrame, *, case_ids: Iterable[str] | None, max_cases: int | None) -> pd.DataFrame:
    selected = visual_df.copy()
    ids = [str(case_id) for case_id in case_ids or []]
    if ids:
        selected = selected[selected["case_id"].astype(str).isin(ids)].copy()
    if max_cases is not None:
        selected = selected.head(max(0, int(max_cases))).copy()
    if selected.empty:
        raise ValueError("No phase2 visual QC cases selected")
    return selected.reset_index(drop=True)


def _validate_views(views: Iterable[str]) -> list[str]:
    result = [str(view).strip() for view in views if str(view).strip()]
    invalid = [view for view in result if view not in PHASE2_VISUAL_QC_VIEWS]
    if invalid:
        raise ValueError(f"Unsupported phase2 visual QC view(s): {invalid}. Allowed: {list(PHASE2_VISUAL_QC_VIEWS)}")
    if not result:
        raise ValueError("At least one phase2 visual QC view is required")
    return result


def _load_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return pickle.load(f)


def _write_case_assets(
    case_dir: Path,
    benchmark_root: Path,
    visual_row: dict[str, Any],
    manifest_row: dict[str, Any],
    case_payload: dict[str, Any],
    base_sample: dict[str, Any],
) -> None:
    shutil.copy2(benchmark_root / str(visual_row["original_ligand_sdf"]), case_dir / "original_ligand.sdf")
    shutil.copy2(benchmark_root / str(visual_row["failed_ligand_sdf"]), case_dir / "failed_ligand.sdf")
    _write_pocket_pdb(base_sample, case_dir / "protein_pocket.pdb")
    _write_marker_files(case_payload, base_sample, manifest_row, case_dir)
    _write_selection_aliases(case_dir, ligand_mode="failed")
    _write_metrics_json(case_payload, manifest_row, visual_row, case_dir / "qc_metrics.json")
    _write_case_readme(case_payload, manifest_row, case_dir / "README.md")


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


def _write_marker_files(case: dict[str, Any], base: dict[str, Any], manifest_row: dict[str, Any], case_dir: Path) -> None:
    original = np.asarray(case["original_ligand_coords"], dtype=float)
    failed = np.asarray(case["failed_ligand_coords"], dtype=float)
    target_indices = json.loads(str(manifest_row["target_atom_indices"]))
    scaffold_indices = [int(i) for i in base["scaffold"]["atom_indices"]]
    non_target_indices: list[int] = []
    for rgroup in base.get("rgroups", []):
        if str(rgroup.get("rgroup_id")) != str(case["target_rgroup"]):
            non_target_indices.extend(int(i) for i in rgroup.get("atom_indices", []))
    anchor_indices = [int(manifest_row["anchor_scaffold_atom_idx"]), int(manifest_row["anchor_rgroup_atom_idx"])]
    _write_marker_pdb(case_dir / "target_original_atoms.pdb", original, target_indices, "TOR")
    _write_marker_pdb(case_dir / "target_failed_atoms.pdb", failed, target_indices, "TFA")
    _write_marker_pdb(case_dir / "scaffold_atoms.pdb", failed, scaffold_indices, "SCF")
    _write_marker_pdb(case_dir / "non_target_atoms.pdb", failed, non_target_indices, "NTR")
    _write_marker_pdb(case_dir / "anchor_atoms.pdb", failed, anchor_indices, "ANC")
    _write_anchor_bild(case_dir / "valid_anchors.bild", failed, anchor_indices)
    _write_severe_clashes_bild(case, base, case_dir / "severe_clashes.bild")
    _write_surface_clash_spots_bild(case, case_dir / "surface_clash_spots.bild")
    _write_top_clash_pair_assets(case, base, case_dir)
    _write_target_displacement_focus_json(original, failed, target_indices, case_dir / "target_displacement_focus.json")
    _write_target_displacement_bild(original, failed, target_indices, case_dir / "target_displacement.bild")


def _write_marker_pdb(path: Path, coords: np.ndarray, indices: Iterable[int], resname: str) -> None:
    lines = []
    for serial, idx in enumerate(sorted(set(int(i) for i in indices)), start=1):
        if idx < 0 or idx >= len(coords):
            continue
        x, y, z = coords[idx]
        lines.append(
            f"HETATM{serial:5d} C    {resname:>3s} A{serial:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C"
        )
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_anchor_bild(path: Path, coords: np.ndarray, indices: list[int]) -> None:
    lines = [".color magenta"]
    if len(indices) >= 2 and all(0 <= idx < len(coords) for idx in indices[:2]):
        a = coords[indices[0]]
        b = coords[indices[1]]
        lines.append(f".sphere {a[0]:.3f} {a[1]:.3f} {a[2]:.3f} 0.28")
        lines.append(f".sphere {b[0]:.3f} {b[1]:.3f} {b[2]:.3f} 0.28")
        lines.append(f".cylinder {a[0]:.3f} {a[1]:.3f} {a[2]:.3f} {b[0]:.3f} {b[1]:.3f} {b[2]:.3f} 0.06")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_severe_clashes_bild(case: dict[str, Any], base: dict[str, Any], path: Path) -> None:
    protein_coords = np.asarray(base["protein"]["coords"], dtype=float)
    ligand_coords = np.asarray(case["failed_ligand_coords"], dtype=float)
    lines = []
    for pair in case["clash_report"]["clash_pairs"]:
        if not pair.get("is_severe"):
            continue
        ligand_idx = int(pair["ligand_atom_idx"])
        protein_idx = int(pair.get("protein_atom_position", pair["protein_atom_idx"]))
        lx, ly, lz = ligand_coords[ligand_idx]
        px, py, pz = protein_coords[protein_idx]
        lines.append(VISUAL_QC_BILD_COLOR["ligand_clash"])
        lines.append(f".sphere {lx:.3f} {ly:.3f} {lz:.3f} 0.36")
        lines.append(VISUAL_QC_BILD_COLOR["protein_clash"])
        lines.append(f".sphere {px:.3f} {py:.3f} {pz:.3f} 0.30")
        lines.append(VISUAL_QC_BILD_COLOR["clash_line"])
        lines.append(f".cylinder {lx:.3f} {ly:.3f} {lz:.3f} {px:.3f} {py:.3f} {pz:.3f} 0.055")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_surface_clash_spots_bild(case: dict[str, Any], path: Path) -> None:
    ligand_coords = np.asarray(case["failed_ligand_coords"], dtype=float)
    ligand_indices = sorted(
        {
            int(pair["ligand_atom_idx"])
            for pair in case["clash_report"]["clash_pairs"]
            if pair.get("is_severe")
        }
    )
    lines = [VISUAL_QC_BILD_COLOR["ligand_clash"]]
    for ligand_idx in ligand_indices:
        if ligand_idx < 0 or ligand_idx >= len(ligand_coords):
            continue
        lx, ly, lz = ligand_coords[ligand_idx]
        lines.append(f".sphere {lx:.3f} {ly:.3f} {lz:.3f} 0.36")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_top_clash_pair_assets(case: dict[str, Any], base: dict[str, Any], case_dir: Path) -> None:
    pair = _top_clash_pair(case)
    metadata_path = case_dir / "top_clash_pair_metadata.json"
    if pair is None:
        metadata_path.write_text(json.dumps({"available": False}, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    protein_coords = np.asarray(base["protein"]["coords"], dtype=float)
    ligand_coords = np.asarray(case["failed_ligand_coords"], dtype=float)
    protein_idx = int(pair.get("protein_atom_position", pair["protein_atom_idx"]))
    ligand_idx = int(pair["ligand_atom_idx"])
    if protein_idx < 0 or protein_idx >= len(protein_coords) or ligand_idx < 0 or ligand_idx >= len(ligand_coords):
        metadata_path.write_text(json.dumps({"available": False, "reason": "atom_index_out_of_range"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    protein_element = _element(pair.get("protein_element", "C"))
    ligand_element = _element(pair.get("ligand_element", "C"))
    protein_radius = get_vdw_radius(protein_element)
    ligand_radius = get_vdw_radius(ligand_element)
    protein_coord = protein_coords[protein_idx]
    ligand_coord = ligand_coords[ligand_idx]

    _write_single_atom_pdb(case_dir / "top_clash_protein_vdw_atom.pdb", protein_coord, protein_element, "PRC")
    _write_single_atom_pdb(case_dir / "top_clash_ligand_vdw_atom.pdb", ligand_coord, ligand_element, "LIC")
    _write_pair_center_line_bild(case_dir / "top_clash_pair_line.bild", ligand_coord, protein_coord)
    metadata = {
        "available": True,
        "ligand_atom_idx": ligand_idx,
        "protein_atom_idx": int(pair.get("protein_atom_idx", protein_idx)),
        "protein_atom_position": protein_idx,
        "ligand_element": ligand_element,
        "protein_element": protein_element,
        "ligand_vdw_radius": ligand_radius,
        "protein_vdw_radius": protein_radius,
        "distance": float(pair.get("distance") or np.linalg.norm(ligand_coord - protein_coord)),
        "vdw_sum": float(pair.get("vdw_sum") or ligand_radius + protein_radius),
        "clash_depth": float(pair.get("clash_depth") or 0.0),
        "protein_residue_key": pair.get("protein_residue_key", ""),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _top_clash_pair(case: dict[str, Any]) -> dict[str, Any] | None:
    pairs = list(case.get("clash_report", {}).get("clash_pairs", []))
    severe = [pair for pair in pairs if pair.get("is_severe")]
    candidates = severe or pairs
    if not candidates:
        return None
    return max(candidates, key=lambda pair: float(pair.get("clash_depth") or 0.0))


def _write_single_atom_pdb(path: Path, coord: np.ndarray, element: str, resname: str) -> None:
    x, y, z = coord
    clean_element = _element(element)
    atom_name = f"{clean_element}1"[:4]
    lines = [
        f"HETATM{1:5d} {atom_name:<4s} {resname:>3s} A{1:4d}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {clean_element:>2s}",
        "END",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_pair_center_line_bild(path: Path, ligand_coord: np.ndarray, protein_coord: np.ndarray) -> None:
    lx, ly, lz = ligand_coord
    px, py, pz = protein_coord
    lines = [
        VISUAL_QC_BILD_COLOR["clash_line"],
        f".cylinder {lx:.3f} {ly:.3f} {lz:.3f} {px:.3f} {py:.3f} {pz:.3f} 0.05",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_target_displacement_bild(
    original: np.ndarray,
    failed: np.ndarray,
    indices: Iterable[int],
    path: Path,
) -> None:
    lines = [VISUAL_QC_BILD_COLOR["target_displacement"]]
    for idx in sorted(set(int(i) for i in indices)):
        if idx < 0 or idx >= len(original) or idx >= len(failed):
            continue
        if float(np.linalg.norm(failed[idx] - original[idx])) < 0.05:
            continue
        ox, oy, oz = original[idx]
        fx, fy, fz = failed[idx]
        lines.append(f".cylinder {ox:.3f} {oy:.3f} {oz:.3f} {fx:.3f} {fy:.3f} {fz:.3f} 0.04")
        lines.append(f".sphere {fx:.3f} {fy:.3f} {fz:.3f} 0.12")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_target_displacement_focus_json(original: np.ndarray, failed: np.ndarray, indices: Iterable[int], path: Path) -> None:
    moved_midpoints: list[np.ndarray] = []
    fallback_midpoints: list[np.ndarray] = []
    moved_deltas: list[np.ndarray] = []
    for idx in sorted(set(int(i) for i in indices)):
        if idx < 0 or idx >= len(original) or idx >= len(failed):
            continue
        midpoint = (original[idx] + failed[idx]) / 2.0
        delta = failed[idx] - original[idx]
        fallback_midpoints.append(midpoint)
        if float(np.linalg.norm(delta)) >= 0.05:
            moved_midpoints.append(midpoint)
            moved_deltas.append(delta)
    if moved_midpoints:
        focus = np.asarray(moved_midpoints, dtype=float).mean(axis=0)
        source = "moved_target_displacement_midpoint"
    elif fallback_midpoints:
        focus = np.asarray(fallback_midpoints, dtype=float).mean(axis=0)
        source = "target_midpoint_fallback"
    else:
        path.write_text(json.dumps({"available": False}, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    payload = {
        "available": True,
        "focus": [round(float(value), 6) for value in focus],
        "focus_source": source,
        "moved_target_atom_count": len(moved_midpoints),
        "target_atom_count": len(fallback_midpoints),
        "displacement_vector": [round(float(value), 6) for value in np.asarray(moved_deltas, dtype=float).mean(axis=0)] if moved_deltas else [],
        "displacement_axis_min_angle_degrees": DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES,
        "displacement_axis_max_angle_degrees": DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_target_displacement_camera_geometry(case_dir: Path) -> TargetDisplacementCameraGeometry | None:
    path = case_dir / "target_displacement_focus.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("available"):
        return None
    focus = np.asarray(payload.get("focus", []), dtype=float)
    if focus.shape != (3,):
        return None
    vector = np.asarray(payload.get("displacement_vector", []), dtype=float)
    axis = _unit(vector) if vector.shape == (3,) and float(np.linalg.norm(vector)) >= 1e-6 else None
    return TargetDisplacementCameraGeometry(focus=focus, axis=axis)


def _prepare_phase2_camera_views(
    cameras: Iterable[CameraView],
    geometry: TargetDisplacementCameraGeometry | None,
    *,
    num_views: int,
) -> list[CameraView]:
    selected = list(cameras)
    if geometry is not None and geometry.axis is not None:
        selected = _filter_camera_views_by_displacement_axis(selected, geometry.axis)
    selected = selected[: max(1, int(num_views))]
    if geometry is not None:
        selected = _retarget_camera_focus(selected, geometry.focus)
    return [replace(camera, label=f"clear_{idx:02d}") for idx, camera in enumerate(selected, start=1)]


def _filter_camera_views_by_displacement_axis(cameras: list[CameraView], axis: np.ndarray) -> list[CameraView]:
    passing = [camera for camera in cameras if _displacement_axis_angle_gate_pass(camera.direction, axis)]
    if passing:
        return passing
    return sorted(cameras, key=lambda camera: _displacement_axis_angle_gate_distance(camera.direction, axis))


def _retarget_camera_focus(cameras: Iterable[CameraView], focus: np.ndarray) -> list[CameraView]:
    if focus.shape != (3,):
        return list(cameras)
    focus_tuple = tuple(float(value) for value in focus)
    return [replace(camera, focus=focus_tuple) for camera in cameras]


def _displacement_axis_angle_degrees(direction: Iterable[float], axis: np.ndarray | Iterable[float] | None) -> float:
    if axis is None:
        return 90.0
    unit_axis = _unit(np.asarray(axis, dtype=float))
    unit_direction = _unit(np.asarray(tuple(direction), dtype=float))
    dot = min(1.0, max(0.0, abs(float(np.dot(unit_direction, unit_axis)))))
    return float(np.degrees(np.arccos(dot)))


def _displacement_axis_angle_gate_pass(direction: Iterable[float], axis: np.ndarray | Iterable[float] | None) -> bool:
    angle = _displacement_axis_angle_degrees(direction, axis)
    return DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES <= angle <= DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES


def _displacement_axis_angle_gate_distance(direction: Iterable[float], axis: np.ndarray | Iterable[float] | None) -> float:
    angle = _displacement_axis_angle_degrees(direction, axis)
    if angle < DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES:
        return DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES - angle
    if angle > DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES:
        return angle - DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES
    return 0.0


def _write_selection_aliases(case_dir: Path, *, ligand_mode: str) -> None:
    shutil.copy2(case_dir / "protein_pocket.pdb", case_dir / "protein.pdb")
    shutil.copy2(case_dir / "protein_pocket.pdb", case_dir / "protein_pocket_vdw_atoms.pdb")
    shutil.copy2(case_dir / "target_failed_atoms.pdb", case_dir / "valid_rgroup_atoms.pdb")
    shutil.copy2(case_dir / "severe_clashes.bild", case_dir / "close_contacts.bild")
    if ligand_mode == "union":
        _write_union_selection_sdf(case_dir / "original_ligand.sdf", case_dir / "failed_ligand.sdf", case_dir / "ligand.sdf")
    elif ligand_mode == "failed":
        shutil.copy2(case_dir / "failed_ligand.sdf", case_dir / "ligand.sdf")
    else:
        raise ValueError(f"Unsupported ligand selection mode: {ligand_mode}")


def _write_union_selection_sdf(original_sdf: Path, failed_sdf: Path, output_sdf: Path) -> None:
    original_coords, original_elements = _read_sdf_atoms(original_sdf)
    failed_coords, failed_elements = _read_sdf_atoms(failed_sdf)
    coords = np.concatenate([original_coords, failed_coords], axis=0)
    elements = [*original_elements, *failed_elements]
    lines = [
        "phase2_union_selection",
        "  Clash2Feedback",
        "",
        f"{len(coords):>3d}{0:>3d}  0  0  0  0            999 V2000",
    ]
    for coord, element in zip(coords, elements, strict=True):
        x, y, z = coord
        lines.append(f"{x:10.4f}{y:10.4f}{z:10.4f} {element:<3s} 0  0  0  0  0  0  0  0  0  0  0  0")
    lines.extend(["M  END", "$$$$"])
    output_sdf.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _build_case_render_tasks(
    *,
    case_id: str,
    case_dir: Path,
    views: Iterable[str],
    num_clear_views: int,
    candidate_directions: int,
) -> list[Phase2RenderTask]:
    tasks = []
    camera_geometry = _read_target_displacement_camera_geometry(case_dir)
    for view in views:
        selection_view, ligand_mode = VIEW_SELECTION[view]
        _write_selection_aliases(case_dir, ligand_mode=ligand_mode)
        camera_filter = _phase2_camera_filter(camera_geometry)
        selected_cameras = select_clear_camera_views(
            case_dir,
            view=selection_view,
            num_views=num_clear_views,
            num_candidates=candidate_directions,
            camera_filter=camera_filter,
        )
        cameras = tuple(_prepare_phase2_camera_views(selected_cameras, camera_geometry, num_views=num_clear_views))
        script_path = case_dir / "scripts" / f"{view}_{cameras[0].label}_{cameras[-1].label}.cxc"
        tasks.append(
            Phase2RenderTask(
                case_id=case_id,
                view=view,
                case_dir=case_dir,
                script_path=script_path,
                cameras=cameras,
                candidate_directions=int(candidate_directions),
            )
        )
    _write_selection_aliases(case_dir, ligand_mode="failed")
    return tasks


def _phase2_camera_filter(camera_geometry: TargetDisplacementCameraGeometry | None):
    if camera_geometry is None or camera_geometry.axis is None:
        return None

    def _passes_displacement_axis_angle(camera: CameraView) -> bool:
        return _displacement_axis_angle_gate_pass(camera.direction, camera_geometry.axis)

    return _passes_displacement_axis_angle


def _write_group_script(task: Phase2RenderTask, *, width: int, height: int) -> None:
    commands = _view_commands(task.view, task.case_dir)
    frame_spec = _view_frame_spec(task.view, task.case_dir)
    _write_camera_focus_helper(task.case_dir / "scripts" / CAMERA_FOCUS_HELPER_NAME)
    lines = [
        f"# Phase2 visual QC render for {task.case_id}: {task.view}.",
        "# Images are for manual visual QC, not automatic pass/fail judgement.",
        *commands,
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


def _view_frame_spec(view: str, case_dir: Path | None = None) -> str:
    if view == "overlay_sticks":
        return "#2-8"
    if view == "clash_pair_vdw":
        if case_dir is not None and not _top_clash_pair_available(case_dir):
            return "#1-2"
        return "#2-5"
    return "all"


def _view_commands(view: str, case_dir: Path | None = None) -> list[str]:
    common = ["set bgColor white", "lighting soft", "graphics silhouettes true width 1.4 depthJump 0.01"]
    if view == "clash":
        return [
            *common,
            "open protein_pocket.pdb",
            "open failed_ligand.sdf",
            "open target_failed_atoms.pdb",
            "open severe_clashes.bild",
            "show #1 atoms",
            "style #1 stick",
            f"color #1 {VISUAL_QC_CHIMERAX_COLOR['protein']}",
            "transparency #1 60 target a",
            "style #2 stick",
            f"color #2 {VISUAL_QC_CHIMERAX_COLOR['failed_ligand']}",
            "show #3 atoms",
            "style #3 sphere",
            "size #3 atomRadius 0.30",
            f"color #3 {VISUAL_QC_CHIMERAX_COLOR['target_failed']}",
        ]
    if view == "ligand_delta":
        return [
            *common,
            "open original_ligand.sdf",
            "open failed_ligand.sdf",
            "open scaffold_atoms.pdb",
            "open target_original_atoms.pdb",
            "open target_failed_atoms.pdb",
            "open target_displacement.bild",
            "style #1 stick",
            "style #2 stick",
            f"color #1 {VISUAL_QC_CHIMERAX_COLOR['original_ligand']}",
            f"color #2 {VISUAL_QC_CHIMERAX_COLOR['failed_ligand']}",
            "transparency #1 45 target a",
            "show #3 atoms",
            "style #3 sphere",
            "size #3 atomRadius 0.25",
            f"color #3 {VISUAL_QC_CHIMERAX_COLOR['scaffold']}",
            "show #4 atoms",
            "show #5 atoms",
            "style #4 sphere",
            "style #5 sphere",
            "size #4 atomRadius 0.30",
            "size #5 atomRadius 0.35",
            f"color #4 {VISUAL_QC_CHIMERAX_COLOR['target_original']}",
            f"color #5 {VISUAL_QC_CHIMERAX_COLOR['target_failed']}",
        ]
    if view == "rgroup":
        return [
            *common,
            "open failed_ligand.sdf",
            "open scaffold_atoms.pdb",
            "open target_failed_atoms.pdb",
            "open non_target_atoms.pdb",
            "open anchor_atoms.pdb",
            "style #1 stick",
            f"color #1 {VISUAL_QC_CHIMERAX_COLOR['failed_ligand']}",
            "show #2 atoms",
            "show #3 atoms",
            "show #4 atoms",
            "show #5 atoms",
            "style #2 sphere",
            "style #3 sphere",
            "style #4 sphere",
            "style #5 sphere",
            "size #2 atomRadius 0.28",
            "size #3 atomRadius 0.38",
            "size #4 atomRadius 0.28",
            "size #5 atomRadius 0.45",
            f"color #2 {VISUAL_QC_CHIMERAX_COLOR['scaffold']}",
            f"color #3 {VISUAL_QC_CHIMERAX_COLOR['target_failed']}",
            f"color #4 {VISUAL_QC_CHIMERAX_COLOR['non_target']}",
            f"color #5 {VISUAL_QC_CHIMERAX_COLOR['anchor']}",
        ]
    if view == "overlay_sticks":
        return [
            *common,
            "open protein_pocket.pdb",
            "open original_ligand.sdf",
            "open failed_ligand.sdf",
            "open scaffold_atoms.pdb",
            "open target_original_atoms.pdb",
            "open target_failed_atoms.pdb",
            "open severe_clashes.bild",
            "open target_displacement.bild",
            "show #1 atoms",
            "style #1 stick",
            f"color #1 {VISUAL_QC_CHIMERAX_COLOR['protein']}",
            "transparency #1 70 target a",
            "style #2 stick",
            "style #3 stick",
            f"color #2 {VISUAL_QC_CHIMERAX_COLOR['original_ligand']}",
            f"color #3 {VISUAL_QC_CHIMERAX_COLOR['failed_ligand']}",
            "transparency #2 45 target a",
            "show #4 atoms",
            "style #4 sphere",
            "size #4 atomRadius 0.25",
            f"color #4 {VISUAL_QC_CHIMERAX_COLOR['scaffold']}",
            "show #5 atoms",
            "show #6 atoms",
            "style #5 sphere",
            "style #6 sphere",
            "size #5 atomRadius 0.35",
            "size #6 atomRadius 0.28",
            f"color #5 {VISUAL_QC_CHIMERAX_COLOR['target_original']}",
            f"color #6 {VISUAL_QC_CHIMERAX_COLOR['target_failed']}",
        ]
    if view == "overlay_surface":
        return [
            *common,
            "open protein_pocket.pdb",
            "open original_ligand.sdf",
            "open failed_ligand.sdf",
            "open target_original_atoms.pdb",
            "open target_failed_atoms.pdb",
            "open surface_clash_spots.bild",
            "hide #1 atoms",
            "show #1 cartoons",
            "surface #1",
            "transparency #1 92 target s",
            "style #2 stick",
            "style #3 stick",
            f"color #1 {VISUAL_QC_CHIMERAX_COLOR['protein']}",
            f"color #2 {VISUAL_QC_CHIMERAX_COLOR['original_ligand']}",
            f"color #3 {VISUAL_QC_CHIMERAX_COLOR['failed_ligand']}",
            "transparency #2 45 target a",
            "show #4 atoms",
            "show #5 atoms",
            "style #4 sphere",
            "style #5 sphere",
            "size #4 atomRadius 0.24",
            "size #5 atomRadius 0.28",
            f"color #4 {VISUAL_QC_CHIMERAX_COLOR['target_original']}",
            f"color #5 {VISUAL_QC_CHIMERAX_COLOR['target_failed']}",
        ]
    if view == "clash_pair_vdw":
        if case_dir is not None and not _top_clash_pair_available(case_dir):
            return [
                *common,
                "open protein_pocket.pdb",
                "open failed_ligand.sdf",
                "show #1 atoms",
                "show #2 atoms",
                "style #1 stick",
                "style #2 stick",
                f"color #1 {VISUAL_QC_CHIMERAX_COLOR['protein']}",
                f"color #2 {VISUAL_QC_CHIMERAX_COLOR['failed_ligand']}",
                "transparency #1 78 target a",
                "transparency #2 45 target a",
            ]
        return [
            *common,
            "open protein_pocket.pdb",
            "open failed_ligand.sdf",
            "open top_clash_protein_vdw_atom.pdb",
            "open top_clash_ligand_vdw_atom.pdb",
            "open top_clash_pair_line.bild",
            "show #1 atoms",
            "show #2 atoms",
            "show #3 atoms",
            "show #4 atoms",
            "style #1 stick",
            "style #2 stick",
            "style #3 sphere",
            "style #4 sphere",
            f"color #1 {VISUAL_QC_CHIMERAX_COLOR['protein']}",
            f"color #2 {VISUAL_QC_CHIMERAX_COLOR['failed_ligand']}",
            "transparency #1 78 target a",
            "transparency #2 45 target a",
            f"color #3 {VISUAL_QC_CHIMERAX_COLOR['protein_clash']}",
            f"color #4 {VISUAL_QC_CHIMERAX_COLOR['ligand_clash']}",
            f"color #5 {VISUAL_QC_CHIMERAX_COLOR['clash_line']}",
            "transparency #3 72 target a",
            "transparency #4 72 target a",
        ]
    raise ValueError(f"Unsupported phase2 visual QC view: {view}")


def _top_clash_pair_available(case_dir: Path) -> bool:
    metadata_path = case_dir / "top_clash_pair_metadata.json"
    if not metadata_path.exists():
        return False
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(payload.get("available"))


def _clear_view_commands(model_spec: str, camera_view: CameraView) -> list[str]:
    axis_id = _axis_id(camera_view.label)
    center = np.asarray(camera_view.focus, dtype=float)
    direction = _unit(np.asarray(camera_view.direction, dtype=float))
    endpoint = center + direction * 10.0
    return [
        f"define axis fromPoint {_point_spec(center)} toPoint {_point_spec(endpoint)} id {axis_id} color white radius 0.01",
        f"hide {axis_id} models",
        f"view {model_spec} clip false pad 0.50 zalign {axis_id}",
        f"runscript scripts/{CAMERA_FOCUS_HELPER_NAME} {_point_spec(center).replace(',', ' ')}",
    ]


def _task_images_exist(task: Phase2RenderTask) -> bool:
    return all(
        (task.case_dir / "images" / f"{task.view}_{camera.label}.png").is_file()
        and (task.case_dir / "images" / f"{task.view}_{camera.label}.png").stat().st_size > 0
        for camera in task.cameras
    )


def _render_rows(
    task: Phase2RenderTask,
    *,
    status: str,
    render_action: str,
    returncode: int | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for camera in task.cameras:
        image_path = task.case_dir / "images" / f"{task.view}_{camera.label}.png"
        rows.append(
            _render_row(
                task,
                camera,
                image_path=image_path,
                status=status,
                returncode=returncode,
                stderr_tail=render_action,
                render_action=render_action,
            )
        )
    return rows


def _render_row(
    task: Phase2RenderTask,
    camera: CameraView,
    *,
    image_path: Path,
    status: str,
    returncode: int | None,
    stderr_tail: str,
    render_action: str,
) -> dict[str, Any]:
    camera_geometry = _read_target_displacement_camera_geometry(task.case_dir)
    axis_angle = (
        _displacement_axis_angle_degrees(camera.direction, camera_geometry.axis)
        if camera_geometry is not None and camera_geometry.axis is not None
        else 90.0
    )
    axis_angle_gate_pass = _displacement_axis_angle_gate_pass(
        camera.direction,
        camera_geometry.axis if camera_geometry is not None else None,
    )
    return {
        "case_id": task.case_id,
        "view": task.view,
        "angle": camera.label,
        "script_path": str(task.script_path),
        "image_path": str(image_path),
        "status": status,
        "render_action": render_action,
        "returncode": "" if returncode is None else int(returncode),
        "stderr_tail": stderr_tail,
        "camera_score": camera.score,
        "camera_focus": ",".join(f"{value:.6f}" for value in camera.focus),
        "camera_target": ",".join(f"{value:.6f}" for value in camera.focus),
        "camera_target_mode": "rgroup_displacement_midpoint",
        "displacement_axis_angle_degrees": round(float(axis_angle), 6),
        "displacement_axis_angle_gate_pass": bool(axis_angle_gate_pass),
        "ligand_occluded_fraction": camera.ligand_occluded_fraction,
        "center_line_blocked": camera.center_line_blocked,
        "camera_direction": ",".join(f"{value:.6f}" for value in camera.direction),
        "camera_selection_tier": camera.selection_tier,
        "candidate_directions": int(task.candidate_directions),
        "interest_occluded_fraction": camera.interest_occluded_fraction,
        "key_occluded_fraction": camera.key_occluded_fraction,
        "projection_area_score": camera.projection_area_score,
        "interest_area_score": camera.interest_area_score,
    }


def _write_metrics_json(case: dict[str, Any], manifest_row: dict[str, Any], visual_row: dict[str, Any], path: Path) -> None:
    keys = [
        "case_id",
        "oracle_split",
        "injection_mode",
        "target_rgroup",
        "target_num_severe_pairs",
        "non_target_num_severe_pairs",
        "scaffold_num_severe_pairs",
        "max_clash_depth",
        "target_score_ratio_valid",
        "energy_delta",
    ]
    metrics = {key: manifest_row.get(key, "") for key in keys}
    metrics["top_clash_residue"] = manifest_row.get("top_clash_residue", "")
    metrics["visual_qc_status"] = visual_row.get("visual_qc_status", "")
    metrics["base_sample_id"] = case.get("base_sample", {}).get("sample_id", "")
    path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_case_readme(case: dict[str, Any], manifest_row: dict[str, Any], path: Path) -> None:
    text = f"""# Phase 2 Visual QC: {case['case_id']}

## 1. Views

- `ligand_delta`: original vs failed ligand without protein, focused on local target movement.
- `overlay_sticks`: original/failed overlay with protein sticks, target displacement guides, ligand-side clash points, protein-side clash points and center lines.
- `overlay_surface`: high-transparency pocket context with target R-group atom markers and ligand-side clash spots; use as auxiliary evidence only.
- `clash_pair_vdw`: local top ligand-protein clash pair as vdW spheres.

Optional legacy views `clash` and `rgroup` can still be rendered explicitly for extra debugging.

## 2. Case Metrics

- oracle_split: {manifest_row.get('oracle_split')}.
- injection_mode: {manifest_row.get('injection_mode')}.
- target_rgroup: {manifest_row.get('target_rgroup')}.
- target_num_severe_pairs: {manifest_row.get('target_num_severe_pairs')}.
- non_target_num_severe_pairs: {manifest_row.get('non_target_num_severe_pairs')}.
- scaffold_num_severe_pairs: {manifest_row.get('scaffold_num_severe_pairs')}.
- max_clash_depth: {manifest_row.get('max_clash_depth')}.
- top_clash_residue: {manifest_row.get('top_clash_residue')}.

## 3. Manual Judgement

- `pass`: only target R-group visibly moves and clash is target-local.
- `minor_issue`: generally correct, but one view is ambiguous or marker visibility is imperfect.
- `fail`: scaffold/non-target moved substantially, clash is not target-local, or visual evidence contradicts oracle split.
"""
    path.write_text(text, encoding="utf-8")


def _point_spec(point: np.ndarray) -> str:
    return ",".join(f"{float(value):.4f}" for value in point)


def _unit(values: np.ndarray) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm < 1e-12:
        return np.asarray([1.0, 0.0, 0.0], dtype=float)
    return vector / norm


def _axis_id(label: str) -> str:
    try:
        index = int(label.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        index = 1
    return f"#{90 + max(1, min(index, 80))}"


def _element(value: Any) -> str:
    text = "".join(ch for ch in str(value).strip() if ch.isalpha())
    if not text:
        return "C"
    if len(text) >= 2 and text[:2].upper() in {"CL", "BR"}:
        return text[:2].title()
    return text[0].upper()


def _tail(text: str, max_chars: int = 600) -> str:
    compact = " ".join(str(text).split())
    return compact[-max_chars:]
