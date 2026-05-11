from __future__ import annotations

import csv
import math
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from shutil import which
from typing import Callable, Iterable

import numpy as np

from clash2feedback.utils.files import ensure_dir


DEFAULT_VIEWS = ("overview", "clash", "rgroup", "ligand")
DEFAULT_ANGLES = ("front", "back", "left", "right", "top", "bottom", "iso")
FOCUS_PAD = "0.45"
DEFAULT_CAMERA_MODE = "clear-views"
DEFAULT_NUM_CLEAR_VIEWS = 12
DEFAULT_CANDIDATE_DIRECTIONS = 1024
DEFAULT_CONTACT_SHEET_ROWS = 3
DEFAULT_CONTACT_SHEET_COLUMNS = 4
CONTACT_SHEET_GAP_PIXELS = 40
MAX_CLEAR_VIEWS_PER_PROCESS = DEFAULT_NUM_CLEAR_VIEWS
CAMERA_MODES = ("clear-views", "fixed-angles")

VDW_RADII = {
    "H": 1.20,
    "C": 1.70,
    "N": 1.55,
    "O": 1.52,
    "F": 1.47,
    "P": 1.80,
    "S": 1.80,
    "CL": 1.75,
    "BR": 1.85,
    "I": 1.98,
}

ANGLE_COMMANDS: dict[str, tuple[str, ...]] = {
    "front": (),
    "back": ("turn y 180",),
    "left": ("turn y -90",),
    "right": ("turn y 90",),
    "top": ("turn x 90",),
    "bottom": ("turn x -90",),
    "iso": ("turn y 45", "turn x 25"),
}


@dataclass(frozen=True)
class CameraView:
    label: str
    focus: tuple[float, float, float]
    direction: tuple[float, float, float]
    score: float
    ligand_occluded_fraction: float
    center_line_blocked: bool
    projection_area_score: float
    interest_occluded_fraction: float = 0.0
    key_occluded_fraction: float = 0.0
    interest_area_score: float = 0.0
    open_side_score: float = 0.0
    selection_tier: str = "unfiltered"


@dataclass(frozen=True)
class CameraFilterTier:
    name: str
    max_ligand_occluded_fraction: float
    max_interest_occluded_fraction: float
    max_key_occluded_fraction: float
    min_projection_area_score: float
    min_interest_area_score: float
    min_open_side_score: float
    allow_center_line_blocked: bool


@dataclass(frozen=True)
class CameraSelectionData:
    ligand_coords: np.ndarray
    protein_coords: np.ndarray
    protein_radii: np.ndarray
    ligand_center: np.ndarray
    protein_center: np.ndarray
    anchor_coords: np.ndarray
    scaffold_coords: np.ndarray
    rgroup_coords: np.ndarray
    close_contact_coords: np.ndarray
    interface_coords: np.ndarray
    interface_axis: np.ndarray | None


@dataclass(frozen=True)
class RenderTask:
    sample_id: str
    view: str
    angle: str
    sample_dir: Path
    script_path: Path
    image_path: Path
    camera_view: CameraView | None = None


@dataclass(frozen=True)
class RenderResult:
    sample_id: str
    view: str
    angle: str
    script_path: str
    image_path: str
    status: str
    returncode: int | None = None
    stderr_tail: str = ""
    camera_score: float | None = None
    ligand_occluded_fraction: float | None = None
    center_line_blocked: bool | None = None
    camera_direction: str = ""
    camera_selection_tier: str = ""
    interest_occluded_fraction: float | None = None
    key_occluded_fraction: float | None = None
    image_rotation_degrees: float | None = None
    image_orientation_status: str = ""


@dataclass(frozen=True)
class ContactSheetResult:
    sample_id: str
    view: str
    image_path: str
    status: str
    num_images: int
    rows: int
    columns: int
    message: str = ""


def discover_visual_sample_dirs(assets_root: str | Path) -> list[Path]:
    root = Path(assets_root)
    if not root.exists():
        raise FileNotFoundError(f"Visual check assets root not found: {root}")
    sample_dirs = [
        path
        for path in sorted(root.iterdir())
        if path.is_dir() and (path / "protein.pdb").exists() and (path / "ligand.sdf").exists()
    ]
    if not sample_dirs:
        raise ValueError(f"No visual check sample directories found under: {root}")
    return sample_dirs


def build_render_tasks(
    assets_root: str | Path,
    *,
    views: Iterable[str] = DEFAULT_VIEWS,
    angles: Iterable[str] = DEFAULT_ANGLES,
    sample_ids: Iterable[str] | None = None,
    max_samples: int | None = None,
    camera_mode: str = DEFAULT_CAMERA_MODE,
    num_clear_views: int = DEFAULT_NUM_CLEAR_VIEWS,
    candidate_directions: int = DEFAULT_CANDIDATE_DIRECTIONS,
) -> list[RenderTask]:
    selected_ids = {str(sample_id) for sample_id in sample_ids or []}
    sample_dirs = discover_visual_sample_dirs(assets_root)
    if selected_ids:
        sample_dirs = [path for path in sample_dirs if path.name in selected_ids]
    if max_samples is not None:
        sample_dirs = sample_dirs[: max(0, int(max_samples))]
    if not sample_dirs:
        raise ValueError("No sample directories selected for rendering")

    view_list = _validate_values("view", views, set(DEFAULT_VIEWS))
    if camera_mode not in CAMERA_MODES:
        raise ValueError(f"Unsupported camera_mode: {camera_mode}. Allowed: {CAMERA_MODES}")
    angle_list = _validate_values("angle", angles, set(ANGLE_COMMANDS)) if camera_mode == "fixed-angles" else []

    tasks: list[RenderTask] = []
    for sample_dir in sample_dirs:
        scripts_dir = ensure_dir(sample_dir / "headless_scripts")
        images_dir = ensure_dir(sample_dir / "images")
        for view in view_list:
            camera_views = (
                select_clear_camera_views(
                    sample_dir,
                    view=view,
                    num_views=num_clear_views,
                    num_candidates=candidate_directions,
                )
                if camera_mode == "clear-views"
                else []
            )
            if camera_mode == "clear-views":
                for camera_view in camera_views:
                    tasks.append(
                        RenderTask(
                            sample_id=sample_dir.name,
                            view=view,
                            angle=camera_view.label,
                            sample_dir=sample_dir,
                            script_path=scripts_dir / f"{view}_{camera_view.label}.cxc",
                            image_path=images_dir / f"{view}_{camera_view.label}.png",
                            camera_view=camera_view,
                        )
                    )
                continue
            for angle in angle_list:
                tasks.append(
                    RenderTask(
                        sample_id=sample_dir.name,
                        view=view,
                        angle=angle,
                        sample_dir=sample_dir,
                        script_path=scripts_dir / f"{view}_{angle}.cxc",
                        image_path=images_dir / f"{view}_{angle}.png",
                    )
                )
    return tasks


def write_headless_script(task: RenderTask, *, width: int = 1800, height: int = 1400) -> None:
    commands = _view_commands(task.view)
    image_rel = task.image_path.relative_to(task.sample_dir)
    content = "\n".join(
        [
            f"# Headless ChimeraX render for {task.sample_id}: {task.view}/{task.angle}.",
            "# Generated for phase0 manual visual triage; not a formal clash detector.",
            *commands,
            *(_orientation_helper_commands(task.view) if task.camera_view is None else ()),
            *_angle_commands(task.view, task.angle, camera_view=task.camera_view),
            f"save {image_rel.as_posix()} width {int(width)} height {int(height)}",
            "",
        ]
    )
    task.script_path.write_text(content, encoding="utf-8")


def write_headless_group_script(tasks: Iterable[RenderTask], *, width: int = 1800, height: int = 1400) -> Path:
    group = list(tasks)
    if not group:
        raise ValueError("At least one render task is required")
    sample_dir = group[0].sample_dir
    view = group[0].view
    if any(task.sample_dir != sample_dir or task.view != view for task in group):
        raise ValueError("Grouped render tasks must share one sample_dir and view")

    script_name = (
        f"{view}_{group[0].angle}_{group[-1].angle}.cxc"
        if group[0].camera_view is not None
        else f"{view}_all_angles.cxc"
    )
    script_path = sample_dir / "headless_scripts" / script_name
    commands = _view_commands(view)
    lines = [
        f"# Headless ChimeraX grouped render for {sample_dir.name}: {view}.",
        "# Generated for phase0 manual visual triage; not a formal clash detector.",
        *commands,
    ]
    if group[0].camera_view is None:
        lines.extend(_orientation_helper_commands(view))
    for task in group:
        image_rel = task.image_path.relative_to(task.sample_dir)
        lines.extend([*_angle_commands(task.view, task.angle, camera_view=task.camera_view), f"save {image_rel.as_posix()} width {int(width)} height {int(height)}"])
    lines.append("")
    script_path.write_text("\n".join(lines), encoding="utf-8")
    return script_path


def render_visual_check_images(
    tasks: Iterable[RenderTask],
    *,
    chimerax: str = "chimerax",
    dry_run: bool = False,
    timeout_seconds: int = 180,
    width: int = 1800,
    height: int = 1400,
) -> list[RenderResult]:
    executable = which(chimerax) or chimerax
    task_list = list(tasks)
    results: list[RenderResult] = []
    if dry_run:
        for task in task_list:
            write_headless_script(task, width=width, height=height)
        for group in _group_tasks_by_sample_and_view(task_list):
            write_headless_group_script(group, width=width, height=height)
        return [_result(task, "script_written") for task in task_list]

    for group in _group_tasks_by_sample_and_view(task_list):
        script_path = write_headless_group_script(group, width=width, height=height)
        script_rel = script_path.relative_to(group[0].sample_dir)
        command = [executable, "--nogui", "--offscreen", "--script", script_rel.as_posix(), "--exit"]
        try:
            completed = subprocess.run(
                command,
                cwd=group[0].sample_dir,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            for task in group:
                results.append(
                    _result(task, "timeout", script_path=script_path, returncode=None, stderr_tail=str(exc))
                )
            continue

        stderr_tail = _tail(completed.stderr or completed.stdout)
        for task in group:
            if completed.returncode == 0 and task.image_path.exists():
                status = "rendered"
            elif completed.returncode == 0:
                status = "missing_image"
            else:
                status = "failed"
            image_rotation_degrees = 0.0
            image_orientation_status = "not_applicable"
            if status == "rendered":
                image_rotation_degrees, image_orientation_status = _orient_rendered_image_protein_lower(
                    task.image_path,
                    view=task.view,
                )
            results.append(
                _result(
                    task,
                    status,
                    script_path=script_path,
                    returncode=completed.returncode,
                    stderr_tail=stderr_tail,
                    image_rotation_degrees=image_rotation_degrees,
                    image_orientation_status=image_orientation_status,
                )
            )
    return results


def write_render_manifest(results: Iterable[RenderResult], path: str | Path) -> None:
    rows = list(results)
    manifest_path = Path(path)
    ensure_dir(manifest_path.parent)
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample_id",
                "view",
                "angle",
                "script_path",
                "image_path",
                "status",
                "returncode",
                "stderr_tail",
                "camera_score",
                "ligand_occluded_fraction",
                "center_line_blocked",
                "camera_direction",
                "camera_selection_tier",
                "interest_occluded_fraction",
                "key_occluded_fraction",
                "image_rotation_degrees",
                "image_orientation_status",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def write_render_contact_sheets(
    results: Iterable[RenderResult],
    *,
    rows: int = DEFAULT_CONTACT_SHEET_ROWS,
    columns: int = DEFAULT_CONTACT_SHEET_COLUMNS,
) -> list[ContactSheetResult]:
    row_count = max(1, int(rows))
    column_count = max(1, int(columns))
    max_images = row_count * column_count
    grouped: dict[tuple[str, str], list[RenderResult]] = {}
    for row in results:
        if row.status != "rendered" or not row.image_path:
            continue
        image_path = Path(row.image_path)
        if not image_path.exists():
            continue
        grouped.setdefault((row.sample_id, row.view), []).append(row)

    sheets: list[ContactSheetResult] = []
    for (sample_id, view), group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda row: _angle_sort_key(row.angle))[:max_images]
        sheet_path = Path(ordered[0].image_path).parent / f"{view}_contact_sheet.png"
        try:
            _write_contact_sheet_image(ordered, sheet_path, rows=row_count, columns=column_count)
        except Exception as exc:  # pragma: no cover - defensive around optional image backends.
            sheets.append(
                ContactSheetResult(
                    sample_id=sample_id,
                    view=view,
                    image_path=str(sheet_path),
                    status="failed",
                    num_images=len(ordered),
                    rows=row_count,
                    columns=column_count,
                    message=str(exc),
                )
            )
            continue
        sheets.append(
            ContactSheetResult(
                sample_id=sample_id,
                view=view,
                image_path=str(sheet_path),
                status="written",
                num_images=len(ordered),
                rows=row_count,
                columns=column_count,
            )
        )
    return sheets


def write_batch_review_markdown(
    results: Iterable[RenderResult],
    path: str | Path,
    *,
    assets_root: str | Path,
    contact_sheets: Iterable[ContactSheetResult] | None = None,
) -> None:
    rows = list(results)
    sheets = list(contact_sheets or [])
    summary_path = Path(path)
    ensure_dir(summary_path.parent)
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
    sheet_status_counts: dict[str, int] = {}
    for sheet in sheets:
        sheet_status_counts[sheet.status] = sheet_status_counts.get(sheet.status, 0) + 1
    lines = [
        "# 阶段 0 ChimeraX 批量出图初筛记录",
        "",
        "## 1. 状态",
        "",
        f"- assets_root: `{assets_root}`.",
        f"- render tasks: {len(rows)}.",
        f"- status counts: {status_counts}.",
        f"- contact sheets: {sheet_status_counts}.",
        "- 这些 PNG 只用于人工初筛, 不替代阶段 1 正式 clash detector.",
        "- `clear_*` 图片来自按当前样本坐标和当前视图用途自动选择的 ligand-centered 少遮挡视角.",
        f"- 每个 `sample_id + view` 默认生成 `{DEFAULT_CONTACT_SHEET_ROWS} x {DEFAULT_CONTACT_SHEET_COLUMNS}` contact sheet, 单图保持渲染分辨率用于放大检查.",
        "",
        "## 2. 初筛方法",
        "",
        "- 先扫 `overview_contact_sheet.png`: ligand 是否在 pocket 内.",
        "- 再扫 `clash_contact_sheet.png`: 是否有肉眼明显严重重叠或红色 close-contact 标记.",
        "- 再扫 `rgroup_contact_sheet.png` 和 `ligand_contact_sheet.png`: scaffold, valid R-group, anchor 标记是否合理.",
        "- contact sheet 用于快速筛查; 可疑视角再打开对应 `clear_*.png` 单图或本地 ChimeraX 旋转精查.",
        "- `rgroup_*` 和 `ligand_*` 会缩小 scaffold/R-group marker, 避免 marker 本身遮住 ligand 拆分关系.",
        "- 默认角度会先以 ligand 为中心采样候选方向, 再按 `strict`, `relaxed`, `fallback`, `score_only` 分层筛选; manifest 中的 `camera_selection_tier` 可用于定位是否发生回退.",
        "- 视角硬过滤优先保证 ligand center line 不被 protein 阻挡, ligand 和关键坐标可见, 再按视图用途评分: `overview` 偏向口袋入口无遮挡, `clash` 偏向接触界面可见, `rgroup` 偏向 anchor/R-group 连接无遮挡, `ligand` 偏向配体投影展开.",
        "- 非 ligand-only 图片会在渲染后做 PNG 方向校正, 尽量让 protein pocket 位于 ligand 下方, 改善画面重心.",
        "- 可疑样本再下载对应 `complex_xxx/` 目录到本地 ChimeraX 旋转精查.",
        "",
        "## 3. 拼图索引",
        "",
        "| sample_id | view | status | num_images | contact_sheet |",
        "|---|---|---|---|---|",
    ]
    for sheet in sheets:
        image = sheet.image_path if sheet.status == "written" else ""
        lines.append(f"| {sheet.sample_id} | {sheet.view} | {sheet.status} | {sheet.num_images} | `{image}` |")
    lines.extend(
        [
            "",
            "## 4. 单图索引",
            "",
            "| sample_id | view | angle | status | image |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        image = row.image_path if row.status == "rendered" else ""
        lines.append(f"| {row.sample_id} | {row.view} | {row.angle} | {row.status} | `{image}` |")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_contact_sheet_image(
    render_rows: list[RenderResult],
    output_path: Path,
    *,
    rows: int = DEFAULT_CONTACT_SHEET_ROWS,
    columns: int = DEFAULT_CONTACT_SHEET_COLUMNS,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    row_count = max(1, int(rows))
    column_count = max(1, int(columns))
    images = [_load_contact_sheet_image(Path(row.image_path)) for row in render_rows]
    if not images:
        raise ValueError("No rendered images available for contact sheet")
    tile_width = max(image.width for image in images)
    tile_height = max(image.height for image in images)
    title_height = max(72, tile_height // 18)
    gap = CONTACT_SHEET_GAP_PIXELS
    canvas_width = column_count * tile_width + (column_count + 1) * gap
    canvas_height = row_count * (tile_height + title_height) + (row_count + 1) * gap
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
    draw = ImageDraw.Draw(canvas)
    font = _load_contact_sheet_font(max(32, tile_height // 32))

    for idx, row in enumerate(render_rows[: row_count * column_count]):
        image = images[idx]
        if image.size != (tile_width, tile_height):
            image = _fit_image_to_tile(image, tile_width=tile_width, tile_height=tile_height)
        grid_row = idx // column_count
        grid_col = idx % column_count
        x = gap + grid_col * (tile_width + gap)
        y = gap + grid_row * (tile_height + title_height + gap)
        title = row.angle
        title_box = draw.textbbox((0, 0), title, font=font)
        title_width = title_box[2] - title_box[0]
        draw.text((x + (tile_width - title_width) // 2, y), title, fill=(0, 0, 0), font=font)
        canvas.paste(image, (x, y + title_height))
    ensure_dir(output_path.parent)
    canvas.save(output_path)


def _load_contact_sheet_image(path: Path):
    from PIL import Image

    with Image.open(path) as raw:
        image = raw.convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    return Image.alpha_composite(background, image).convert("RGB")


def _fit_image_to_tile(image, *, tile_width: int, tile_height: int):
    from PIL import Image

    fitted = image.copy()
    fitted.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tile_width, tile_height), "white")
    x = (tile_width - fitted.width) // 2
    y = (tile_height - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return canvas


def _load_contact_sheet_font(size: int):
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


def _angle_sort_key(angle: str) -> tuple[int, str]:
    if angle.startswith("clear_"):
        try:
            return (0, f"{int(angle.split('_', 1)[1]):04d}")
        except ValueError:
            return (0, angle)
    if angle in DEFAULT_ANGLES:
        return (1, f"{DEFAULT_ANGLES.index(angle):04d}")
    return (2, angle)


def select_clear_camera_views(
    sample_dir: str | Path,
    *,
    view: str = "overview",
    num_views: int = DEFAULT_NUM_CLEAR_VIEWS,
    num_candidates: int = DEFAULT_CANDIDATE_DIRECTIONS,
    camera_filter: Callable[[CameraView], bool] | None = None,
) -> list[CameraView]:
    sample_path = Path(sample_dir)
    if view not in DEFAULT_VIEWS:
        raise ValueError(f"Unsupported view for camera selection: {view}")

    data = _load_camera_selection_data(sample_path)
    interest_coords = _interest_coords_for_view(view, data)
    directions = _candidate_camera_directions(
        data.ligand_coords,
        data.protein_center,
        interest_coords=interest_coords,
        num_candidates=num_candidates,
    )
    directions.extend(_extra_view_directions(view, data))
    directions = _dedupe_directions(directions)

    ligand_areas = {idx: _projection_area(data.ligand_coords, direction) for idx, direction in enumerate(directions)}
    interest_areas = {idx: _projection_area(interest_coords, direction) for idx, direction in enumerate(directions)}
    max_ligand_area = max(ligand_areas.values(), default=1e-6)
    max_interest_area = max(interest_areas.values(), default=1e-6)

    selected: list[CameraView] = []
    for idx, direction in enumerate(directions):
        candidate = _score_camera_direction(
            view,
            data,
            direction,
            interest_coords=interest_coords,
            ligand_area_score=ligand_areas[idx] / max(max_ligand_area, 1e-6),
            interest_area_score=interest_areas[idx] / max(max_interest_area, 1e-6),
        )
        selected.append(candidate)

    ranked = sorted(selected, key=lambda item: item.score, reverse=True)
    if camera_filter is not None:
        filtered = [candidate for candidate in ranked if camera_filter(candidate)]
        if filtered:
            ranked = filtered
    diverse = _select_clear_views_by_quality(ranked, view=view, num_views=max(1, int(num_views)))
    return [
        replace(
            camera_view,
            label=f"clear_{idx:02d}",
        )
        for idx, camera_view in enumerate(diverse, start=1)
    ]


def _view_commands(view: str) -> tuple[str, ...]:
    common = ("set bgColor white", "lighting soft")
    if view == "overview":
        return (
            "open protein.pdb",
            "open ligand.sdf",
            *common,
            "hide #1 atoms",
            "show #1 cartoons",
            "surface #1",
            "transparency #1 82 target s",
            "show #2 atoms",
            "style #2 stick",
            "color #1 gray",
            "color #2 orange",
        )
    if view == "clash":
        return (
            "open protein.pdb",
            "open ligand.sdf",
            "open protein_pocket_vdw_atoms.pdb",
            "open ligand_vdw_atoms.pdb",
            "open close_contacts.bild",
            *common,
            "graphics silhouettes true width 1.5 depthJump 0.01",
            "hide #1 cartoons",
            "show #1 atoms",
            "show #2 atoms",
            "show #3 atoms",
            "show #4 atoms",
            "style #1 stick",
            "style #2 stick",
            "style #3 sphere",
            "style #4 sphere",
            "color #1 gray",
            "color #2 orange",
            "color #3 gray",
            "color #4 royalblue",
            "transparency #1 70 target a",
            "transparency #3 45 target a",
            "transparency #4 25 target a",
        )
    if view == "rgroup":
        return (
            "open protein.pdb",
            "open ligand.sdf",
            "open scaffold_atoms.pdb",
            "open valid_rgroup_atoms.pdb",
            "open valid_anchors.bild",
            *common,
            "hide #1 atoms",
            "show #1 cartoons",
            "surface #1",
            "transparency #1 97 target s",
            "show #2 atoms",
            "style #2 stick",
            "color #1 gray",
            "color #2 gray",
            "show #3 atoms",
            "show #4 atoms",
            "style #3 sphere",
            "style #4 sphere",
            "size #3 atomRadius 0.35",
            "size #4 atomRadius 0.35",
            "color #3 blue",
            "color #4 orange",
            "color #5 magenta",
        )
    if view == "ligand":
        return (
            "open ligand.sdf",
            "open scaffold_atoms.pdb",
            "open valid_rgroup_atoms.pdb",
            "open valid_anchors.bild",
            *common,
            "show #1 atoms",
            "style #1 stick",
            "color #1 gray",
            "show #2 atoms",
            "show #3 atoms",
            "style #2 sphere",
            "style #3 sphere",
            "size #2 atomRadius 0.35",
            "size #3 atomRadius 0.35",
            "color #2 blue",
            "color #3 orange",
            "color #4 magenta",
        )
    raise ValueError(f"Unsupported view: {view}")


def _orientation_helper_commands(view: str) -> tuple[str, ...]:
    ligand = _ligand_model_spec(view)
    return (
        f"define plane {ligand} id #90 color white",
        "hide #90 models",
    )


def _angle_commands(view: str, angle: str, *, camera_view: CameraView | None = None) -> tuple[str, ...]:
    ligand = _ligand_model_spec(view)
    if camera_view is not None:
        return _clear_view_commands(ligand, camera_view)
    protein = _protein_context_spec(view)
    center = f"center {ligand}"
    ligand_face = (f"view {ligand} clip false pad {FOCUS_PAD} zalign #90",)
    if angle == "front":
        return _pocket_or_ligand_face(ligand, protein)
    if angle == "back":
        return (*_pocket_or_ligand_face(ligand, protein), f"turn y 180 {center}")
    if angle == "left":
        return (*ligand_face, f"turn y -70 {center}")
    if angle == "right":
        return (*ligand_face, f"turn y 70 {center}")
    if angle == "top":
        return (*ligand_face, f"turn x 65 {center}")
    if angle == "bottom":
        return (*ligand_face, f"turn x -65 {center}")
    if angle == "iso":
        return (*_pocket_or_ligand_face(ligand, protein), f"turn y 35 {center}", f"turn x 25 {center}")
    raise ValueError(f"Unsupported angle: {angle}")


def _clear_view_commands(ligand: str, camera_view: CameraView) -> tuple[str, ...]:
    axis_id = _axis_id(camera_view.label)
    center = np.asarray(_camera_center(camera_view), dtype=float)
    direction = np.asarray(camera_view.direction, dtype=float)
    endpoint = center + _unit(direction) * 10.0
    return (
        f"define axis fromPoint {_point_spec(center)} toPoint {_point_spec(endpoint)} id {axis_id} color white radius 0.01",
        f"hide {axis_id} models",
        f"view {ligand} clip false pad {FOCUS_PAD} zalign {axis_id}",
    )


def _pocket_or_ligand_face(ligand: str, protein: str | None) -> tuple[str, ...]:
    if protein is None:
        return (f"view {ligand} clip false pad {FOCUS_PAD} zalign #90",)
    return (f"view {ligand} clip false pad {FOCUS_PAD} zalign {ligand} inFrontOf {protein}",)


def _ligand_model_spec(view: str) -> str:
    if view == "ligand":
        return "#1"
    return "#2"


def _protein_context_spec(view: str) -> str | None:
    if view == "clash":
        return "#3"
    if view in {"overview", "rgroup"}:
        return "#1"
    return None


def _read_sdf_coords(path: Path) -> tuple[np.ndarray, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing ligand SDF for camera selection: {path}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 4:
        raise ValueError(f"Invalid SDF, missing counts line: {path}")
    counts = lines[3].split()
    if not counts:
        raise ValueError(f"Invalid SDF counts line: {path}")
    num_atoms = int(counts[0])
    coords: list[list[float]] = []
    elements: list[str] = []
    for line in lines[4 : 4 + num_atoms]:
        parts = line.split()
        if len(parts) < 4:
            continue
        coords.append([float(parts[0]), float(parts[1]), float(parts[2])])
        elements.append(_normalize_element(parts[3]))
    if not coords:
        raise ValueError(f"No ligand atom coordinates found in SDF: {path}")
    return np.asarray(coords, dtype=float), elements


def _read_pdb_coords(path: Path) -> tuple[np.ndarray, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing PDB for camera selection: {path}")
    coords: list[list[float]] = []
    elements: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        try:
            xyz = [float(line[30:38]), float(line[38:46]), float(line[46:54])]
        except ValueError:
            parts = line.split()
            if len(parts) < 9:
                continue
            xyz = [float(parts[6]), float(parts[7]), float(parts[8])]
        element = line[76:78].strip() if len(line) >= 78 else ""
        if not element:
            atom_name = line[12:16].strip() if len(line) >= 16 else ""
            element = "".join(ch for ch in atom_name if ch.isalpha())[:2]
        coords.append(xyz)
        elements.append(_normalize_element(element))
    if not coords:
        return np.zeros((0, 3), dtype=float), []
    return np.asarray(coords, dtype=float), elements


def _read_bild_coords(path: Path) -> np.ndarray:
    if not path.exists():
        return np.zeros((0, 3), dtype=float)
    coords: list[list[float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == ".sphere" and len(parts) >= 5:
            coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif parts[0] == ".cylinder" and len(parts) >= 7:
            coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
            coords.append([float(parts[4]), float(parts[5]), float(parts[6])])
    if not coords:
        return np.zeros((0, 3), dtype=float)
    return np.asarray(coords, dtype=float)


def _load_camera_selection_data(sample_path: Path) -> CameraSelectionData:
    ligand_coords, _ = _read_sdf_coords(sample_path / "ligand.sdf")
    protein_path = sample_path / "protein_pocket_vdw_atoms.pdb"
    if not protein_path.exists():
        protein_path = sample_path / "protein.pdb"
    protein_coords, protein_elements = _read_pdb_coords(protein_path)
    protein_radii = np.asarray([VDW_RADII.get(element.upper(), 1.70) for element in protein_elements], dtype=float)

    scaffold_coords, _ = _read_pdb_coords(sample_path / "scaffold_atoms.pdb") if (sample_path / "scaffold_atoms.pdb").exists() else (np.zeros((0, 3), dtype=float), [])
    rgroup_coords, _ = _read_pdb_coords(sample_path / "valid_rgroup_atoms.pdb") if (sample_path / "valid_rgroup_atoms.pdb").exists() else (np.zeros((0, 3), dtype=float), [])
    anchor_coords = _read_bild_coords(sample_path / "valid_anchors.bild")
    close_contact_coords = _read_bild_coords(sample_path / "close_contacts.bild")
    interface_coords, interface_axis = _closest_interface_geometry(ligand_coords, protein_coords)

    ligand_center = ligand_coords.mean(axis=0)
    protein_center = protein_coords.mean(axis=0) if len(protein_coords) else ligand_center
    return CameraSelectionData(
        ligand_coords=ligand_coords,
        protein_coords=protein_coords,
        protein_radii=protein_radii,
        ligand_center=ligand_center,
        protein_center=protein_center,
        anchor_coords=anchor_coords,
        scaffold_coords=scaffold_coords,
        rgroup_coords=rgroup_coords,
        close_contact_coords=close_contact_coords,
        interface_coords=interface_coords,
        interface_axis=interface_axis,
    )


def _interest_coords_for_view(view: str, data: CameraSelectionData) -> np.ndarray:
    if view == "overview":
        return _concat_coords([data.anchor_coords, data.ligand_coords])
    if view == "clash":
        return _concat_coords([data.close_contact_coords, data.interface_coords, data.ligand_coords])
    if view == "rgroup":
        return _concat_coords([data.anchor_coords, data.scaffold_coords, data.rgroup_coords, data.ligand_coords])
    if view == "ligand":
        return data.ligand_coords
    raise ValueError(f"Unsupported view: {view}")


def _score_camera_direction(
    view: str,
    data: CameraSelectionData,
    direction: np.ndarray,
    *,
    interest_coords: np.ndarray,
    ligand_area_score: float,
    interest_area_score: float,
) -> CameraView:
    direction = _unit(direction)
    focus = _focus_for_view(view, data)
    if view == "ligand":
        score = ligand_area_score * 5.0 + interest_area_score
        return _camera_view(
            focus=focus,
            direction=direction,
            score=score,
            ligand_occluded_fraction=0.0,
            center_line_blocked=False,
            projection_area_score=ligand_area_score,
            interest_occluded_fraction=0.0,
            key_occluded_fraction=0.0,
            interest_area_score=interest_area_score,
            open_side_score=0.0,
        )

    occluded_fraction, center_blocked, interest_blocked_fraction = _visibility_occlusion(
        data.ligand_coords,
        data.protein_coords,
        data.protein_radii,
        direction,
        key_coords=interest_coords,
    )
    open_score = _open_side_score(direction, data.ligand_center, data.protein_center)

    if view == "overview":
        key_blocked = interest_blocked_fraction
        score = (1.0 - occluded_fraction) * 4.0 + ligand_area_score * 1.4 + open_score * 2.0
        score -= (3.0 if center_blocked else 0.0) + interest_blocked_fraction * 1.2
    elif view == "clash":
        contact_blocked = _key_blocked_fraction(data, direction, _clash_key_coords(data))
        key_blocked = contact_blocked
        interface_side_score = _interface_side_score(direction, data.interface_axis)
        score = (1.0 - occluded_fraction) * 2.0 + (1.0 - contact_blocked) * 3.2
        score += interest_area_score * 1.8 + ligand_area_score * 0.8 + interface_side_score * 1.6 + open_score * 0.6
        score -= 2.0 if center_blocked else 0.0
    elif view == "rgroup":
        anchor_blocked = _key_blocked_fraction(data, direction, data.anchor_coords)
        key_blocked = anchor_blocked
        connection_score = _rgroup_connection_score(direction, data)
        score = (1.0 - occluded_fraction) * 1.8 + (1.0 - anchor_blocked) * 3.6
        score += interest_area_score * 1.9 + ligand_area_score * 0.9 + connection_score * 1.4 + open_score * 0.4
        score -= 2.2 if center_blocked else 0.0
    else:
        raise ValueError(f"Unsupported view: {view}")

    return _camera_view(
        focus=focus,
        direction=direction,
        score=score,
        ligand_occluded_fraction=occluded_fraction,
        center_line_blocked=center_blocked,
        projection_area_score=ligand_area_score,
        interest_occluded_fraction=interest_blocked_fraction,
        key_occluded_fraction=key_blocked,
        interest_area_score=interest_area_score,
        open_side_score=open_score,
    )


def _camera_view(
    *,
    focus: np.ndarray,
    direction: np.ndarray,
    score: float,
    ligand_occluded_fraction: float,
    center_line_blocked: bool,
    projection_area_score: float,
    interest_occluded_fraction: float,
    key_occluded_fraction: float,
    interest_area_score: float,
    open_side_score: float,
) -> CameraView:
    return CameraView(
        label="pending",
        focus=_to_tuple(focus),
        direction=_to_tuple(direction),
        score=round(float(score), 6),
        ligand_occluded_fraction=round(float(ligand_occluded_fraction), 6),
        center_line_blocked=bool(center_line_blocked),
        projection_area_score=round(float(projection_area_score), 6),
        interest_occluded_fraction=round(float(interest_occluded_fraction), 6),
        key_occluded_fraction=round(float(key_occluded_fraction), 6),
        interest_area_score=round(float(interest_area_score), 6),
        open_side_score=round(float(open_side_score), 6),
    )


def _focus_for_view(view: str, data: CameraSelectionData) -> np.ndarray:
    if view == "clash" and len(data.interface_coords):
        return data.interface_coords.mean(axis=0)
    if view == "rgroup" and len(data.anchor_coords):
        return data.anchor_coords.mean(axis=0)
    return data.ligand_center


def _extra_view_directions(view: str, data: CameraSelectionData) -> list[np.ndarray]:
    directions: list[np.ndarray] = []
    if view == "clash" and data.interface_axis is not None:
        directions.extend(_orthogonal_directions(data.interface_axis))
        directions.extend([_unit(data.interface_axis), _unit(-data.interface_axis)])
    if view == "rgroup":
        marker_axis = _marker_axis(data.scaffold_coords, data.rgroup_coords)
        if marker_axis is not None:
            directions.extend(_orthogonal_directions(marker_axis))
            directions.extend([_unit(marker_axis), _unit(-marker_axis)])
    return directions


def _closest_interface_geometry(
    ligand_coords: np.ndarray,
    protein_coords: np.ndarray,
    *,
    max_pairs: int = 18,
    preferred_distance: float = 3.6,
) -> tuple[np.ndarray, np.ndarray | None]:
    if len(ligand_coords) == 0 or len(protein_coords) == 0:
        return np.zeros((0, 3), dtype=float), None
    distances = np.linalg.norm(protein_coords[:, None, :] - ligand_coords[None, :, :], axis=2)
    flat_order = np.argsort(distances, axis=None)
    selected: list[tuple[int, int, float]] = []
    for flat_idx in flat_order:
        protein_idx, ligand_idx = np.unravel_index(int(flat_idx), distances.shape)
        distance = float(distances[protein_idx, ligand_idx])
        if distance <= preferred_distance or len(selected) < min(6, max_pairs):
            selected.append((int(protein_idx), int(ligand_idx), distance))
        if len(selected) >= max_pairs:
            break
    if not selected:
        return np.zeros((0, 3), dtype=float), None

    coords: list[np.ndarray] = []
    axes: list[np.ndarray] = []
    for protein_idx, ligand_idx, _ in selected:
        protein_coord = protein_coords[protein_idx]
        ligand_coord = ligand_coords[ligand_idx]
        coords.extend([protein_coord, ligand_coord, (protein_coord + ligand_coord) / 2.0])
        axes.append(_unit(protein_coord - ligand_coord))
    axis = _unit(np.asarray(axes, dtype=float).mean(axis=0)) if axes else None
    return np.asarray(coords, dtype=float), axis


def _clash_key_coords(data: CameraSelectionData) -> np.ndarray:
    return _concat_coords([data.close_contact_coords, data.interface_coords])


def _key_blocked_fraction(data: CameraSelectionData, direction: np.ndarray, key_coords: np.ndarray) -> float:
    if len(key_coords) == 0 or len(data.protein_coords) == 0:
        return 0.0
    blocked = [
        _point_occluded(point, data.protein_coords, data.protein_radii, _unit(direction))
        for point in key_coords
    ]
    return float(np.mean(blocked)) if blocked else 0.0


def _interface_side_score(direction: np.ndarray, interface_axis: np.ndarray | None) -> float:
    if interface_axis is None:
        return 0.0
    return 1.0 - abs(float(np.dot(_unit(direction), _unit(interface_axis))))


def _rgroup_connection_score(direction: np.ndarray, data: CameraSelectionData) -> float:
    marker_axis = _marker_axis(data.scaffold_coords, data.rgroup_coords)
    if marker_axis is None:
        return 0.0
    return 1.0 - abs(float(np.dot(_unit(direction), _unit(marker_axis))))


def _marker_axis(scaffold_coords: np.ndarray, rgroup_coords: np.ndarray) -> np.ndarray | None:
    if len(scaffold_coords) == 0 or len(rgroup_coords) == 0:
        return None
    axis = rgroup_coords.mean(axis=0) - scaffold_coords.mean(axis=0)
    if np.linalg.norm(axis) < 1e-6:
        return None
    return _unit(axis)


def _concat_coords(arrays: Iterable[np.ndarray]) -> np.ndarray:
    valid = [np.asarray(array, dtype=float) for array in arrays if np.asarray(array).ndim == 2 and len(array)]
    if not valid:
        return np.zeros((0, 3), dtype=float)
    return np.concatenate(valid, axis=0)


def _candidate_camera_directions(
    ligand_coords: np.ndarray,
    protein_center: np.ndarray,
    *,
    interest_coords: np.ndarray | None = None,
    num_candidates: int,
) -> list[np.ndarray]:
    ligand_center = ligand_coords.mean(axis=0)
    directions = [_unit(direction) for direction in _fibonacci_sphere(max(32, int(num_candidates)))]
    open_direction = ligand_center - protein_center
    if np.linalg.norm(open_direction) > 1e-6:
        directions.append(_unit(open_direction))

    pca_coords = ligand_coords if interest_coords is None or len(interest_coords) < 3 else _concat_coords([ligand_coords, interest_coords])
    centered = pca_coords - pca_coords.mean(axis=0)
    if len(pca_coords) >= 3:
        try:
            _, _, vh = np.linalg.svd(centered, full_matrices=False)
            for axis in vh[:3]:
                directions.append(_unit(axis))
                directions.append(_unit(-axis))
        except np.linalg.LinAlgError:
            pass
    return _dedupe_directions(directions)


def _orthogonal_directions(axis: np.ndarray) -> list[np.ndarray]:
    axis = _unit(axis)
    basis1 = np.cross(axis, np.asarray([0.0, 1.0, 0.0]))
    if np.linalg.norm(basis1) < 1e-6:
        basis1 = np.cross(axis, np.asarray([1.0, 0.0, 0.0]))
    basis1 = _unit(basis1)
    basis2 = _unit(np.cross(axis, basis1))
    return [basis1, -basis1, basis2, -basis2]


def _fibonacci_sphere(count: int) -> list[np.ndarray]:
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    directions: list[np.ndarray] = []
    for i in range(count):
        y = 1.0 - (2.0 * (i + 0.5) / count)
        radius = math.sqrt(max(0.0, 1.0 - y * y))
        theta = golden_angle * i
        directions.append(np.asarray([math.cos(theta) * radius, y, math.sin(theta) * radius], dtype=float))
    return directions


def _visibility_occlusion(
    ligand_coords: np.ndarray,
    protein_coords: np.ndarray,
    protein_radii: np.ndarray,
    direction: np.ndarray,
    *,
    key_coords: np.ndarray,
) -> tuple[float, bool, float]:
    if len(protein_coords) == 0:
        return 0.0, False, 0.0
    direction = _unit(direction)
    ligand_center = ligand_coords.mean(axis=0)
    blocked = [_point_occluded(point, protein_coords, protein_radii, direction) for point in ligand_coords]
    center_blocked = _point_occluded(ligand_center, protein_coords, protein_radii, direction)
    if len(key_coords):
        key_blocked = [_point_occluded(point, protein_coords, protein_radii, direction) for point in key_coords]
        key_fraction = float(np.mean(key_blocked))
    else:
        key_fraction = 0.0
    return float(np.mean(blocked)), bool(center_blocked), key_fraction


def _point_occluded(point: np.ndarray, protein_coords: np.ndarray, protein_radii: np.ndarray, direction: np.ndarray) -> bool:
    rel = protein_coords - point
    depth = rel @ direction
    in_front = depth > 0.25
    if not np.any(in_front):
        return False
    rel = rel[in_front]
    depth = depth[in_front]
    radii = protein_radii[in_front]
    perp2 = np.einsum("ij,ij->i", rel, rel) - depth * depth
    thresholds = np.maximum(0.9, radii * 0.82)
    return bool(np.any(perp2 < thresholds * thresholds))


def _projection_area(coords: np.ndarray, direction: np.ndarray) -> float:
    direction = _unit(direction)
    basis1 = np.cross(direction, np.asarray([0.0, 1.0, 0.0]))
    if np.linalg.norm(basis1) < 1e-6:
        basis1 = np.cross(direction, np.asarray([1.0, 0.0, 0.0]))
    basis1 = _unit(basis1)
    basis2 = _unit(np.cross(direction, basis1))
    projected = np.column_stack((coords @ basis1, coords @ basis2))
    spans = projected.max(axis=0) - projected.min(axis=0)
    return float(spans[0] * spans[1])


def _open_side_score(direction: np.ndarray, ligand_center: np.ndarray, protein_center: np.ndarray) -> float:
    protein_to_ligand = ligand_center - protein_center
    if np.linalg.norm(protein_to_ligand) < 1e-6:
        return 0.0
    return float((np.dot(_unit(direction), _unit(protein_to_ligand)) + 1.0) / 2.0)


def _select_clear_views_by_quality(candidates: list[CameraView], *, view: str, num_views: int) -> list[CameraView]:
    if not candidates:
        raise ValueError("No camera view candidates available")

    selected: list[CameraView] = []
    for tier in _camera_filter_tiers(view):
        pool = [
            candidate
            for candidate in candidates
            if _camera_passes_filter(candidate, tier) and not _matches_selected_direction(candidate, selected)
        ]
        picked = _select_diverse_views(pool, num_views=num_views - len(selected), existing=selected)
        selected.extend(replace(candidate, selection_tier=tier.name) for candidate in picked)
        if len(selected) >= num_views:
            return selected[:num_views]
    return selected[:num_views]


def _camera_filter_tiers(view: str) -> tuple[CameraFilterTier, ...]:
    if view == "ligand":
        return (
            CameraFilterTier("strict", 1.0, 1.0, 1.0, 0.45, 0.45, 0.0, True),
            CameraFilterTier("relaxed", 1.0, 1.0, 1.0, 0.25, 0.25, 0.0, True),
            CameraFilterTier("fallback", 1.0, 1.0, 1.0, 0.05, 0.05, 0.0, True),
            CameraFilterTier("score_only", 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, True),
        )
    if view == "overview":
        return (
            CameraFilterTier("strict", 0.25, 0.35, 0.35, 0.25, 0.20, 0.55, False),
            CameraFilterTier("relaxed", 0.40, 0.55, 0.55, 0.15, 0.10, 0.35, False),
            CameraFilterTier("fallback", 0.65, 0.80, 0.80, 0.05, 0.00, 0.00, True),
            CameraFilterTier("score_only", 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, True),
        )
    if view == "clash":
        return (
            CameraFilterTier("strict", 0.30, 0.45, 0.25, 0.15, 0.25, 0.20, False),
            CameraFilterTier("relaxed", 0.50, 0.65, 0.45, 0.08, 0.15, 0.00, False),
            CameraFilterTier("fallback", 0.75, 0.85, 0.70, 0.03, 0.05, 0.00, True),
            CameraFilterTier("score_only", 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, True),
        )
    if view == "rgroup":
        return (
            CameraFilterTier("strict", 0.30, 0.45, 0.20, 0.15, 0.25, 0.15, False),
            CameraFilterTier("relaxed", 0.50, 0.65, 0.45, 0.08, 0.15, 0.00, False),
            CameraFilterTier("fallback", 0.75, 0.85, 0.70, 0.03, 0.05, 0.00, True),
            CameraFilterTier("score_only", 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, True),
        )
    raise ValueError(f"Unsupported view: {view}")


def _camera_passes_filter(candidate: CameraView, tier: CameraFilterTier) -> bool:
    if candidate.center_line_blocked and not tier.allow_center_line_blocked:
        return False
    return (
        candidate.ligand_occluded_fraction <= tier.max_ligand_occluded_fraction
        and candidate.interest_occluded_fraction <= tier.max_interest_occluded_fraction
        and candidate.key_occluded_fraction <= tier.max_key_occluded_fraction
        and candidate.projection_area_score >= tier.min_projection_area_score
        and candidate.interest_area_score >= tier.min_interest_area_score
        and candidate.open_side_score >= tier.min_open_side_score
    )


def _matches_selected_direction(candidate: CameraView, selected: Iterable[CameraView]) -> bool:
    direction = np.asarray(candidate.direction, dtype=float)
    return any(float(np.dot(direction, np.asarray(existing.direction, dtype=float))) > 0.999 for existing in selected)


def _select_diverse_views(
    candidates: list[CameraView],
    *,
    num_views: int,
    existing: Iterable[CameraView] = (),
) -> list[CameraView]:
    if not candidates:
        return []
    if num_views <= 0:
        return []
    existing_views = list(existing)
    for min_degrees in [55.0, 45.0, 35.0, 25.0, 0.0]:
        selected: list[CameraView] = []
        min_cos = math.cos(math.radians(min_degrees))
        for candidate in candidates:
            direction = np.asarray(candidate.direction, dtype=float)
            compared = [*existing_views, *selected]
            if all(float(np.dot(direction, np.asarray(existing.direction, dtype=float))) < min_cos for existing in compared):
                selected.append(candidate)
            if len(selected) >= num_views:
                return selected
    return [
        candidate
        for candidate in candidates
        if not _matches_selected_direction(candidate, existing_views)
    ][:num_views]


def _dedupe_directions(directions: Iterable[np.ndarray]) -> list[np.ndarray]:
    unique: list[np.ndarray] = []
    for direction in directions:
        candidate = _unit(direction)
        if not any(float(np.dot(candidate, existing)) > 0.995 for existing in unique):
            unique.append(candidate)
    return unique


def _orient_rendered_image_protein_lower(path: Path, *, view: str) -> tuple[float, str]:
    if view == "ligand":
        return 0.0, "not_applicable_ligand_only"
    try:
        import matplotlib.image as mpimg
        from scipy import ndimage
    except Exception as exc:  # pragma: no cover - depends on optional image stack
        return 0.0, f"image_stack_unavailable:{exc}"

    image = mpimg.imread(path)
    if image.ndim != 3 or image.shape[0] < 16 or image.shape[1] < 16:
        return 0.0, "unsupported_image_shape"

    candidates = list(range(-180, 181, 15))
    scoring_image = image[:: max(1, image.shape[0] // 450), :: max(1, image.shape[1] // 450)]
    best_angle = 0
    best_score = -1e9
    best_status = "protein_ligand_masks_missing"
    for angle in candidates:
        rotated_small = ndimage.rotate(scoring_image, angle, reshape=False, order=1, mode="constant", cval=1.0)
        score, status = _protein_lower_image_score(rotated_small)
        if status != "ok":
            continue
        score -= abs(float(angle)) * 0.0005
        if score > best_score:
            best_score = score
            best_angle = angle
            best_status = "ok"

    if best_status != "ok":
        return 0.0, best_status
    if abs(best_angle) < 1:
        return 0.0, "already_oriented"

    rotated = ndimage.rotate(image, best_angle, reshape=False, order=1, mode="constant", cval=1.0)
    mpimg.imsave(path, np.clip(rotated, 0.0, 1.0))
    return float(best_angle), "protein_lower_image_rotation_applied"


def _protein_lower_image_score(image: np.ndarray) -> tuple[float, str]:
    rgb = np.asarray(image[..., :3], dtype=float)
    red = rgb[..., 0]
    green = rgb[..., 1]
    blue = rgb[..., 2]
    ligand_mask = (
        ((red > 0.62) & (green > 0.35) & (blue < 0.38))
        | ((green > 0.55) & (blue > 0.55) & (red < 0.45))
        | ((blue > 0.50) & (red < 0.45) & (green < 0.55))
        | ((red > 0.50) & (blue > 0.45) & (green < 0.42))
    )
    grayish = (np.abs(red - green) < 0.10) & (np.abs(green - blue) < 0.10)
    protein_mask = grayish & (red > 0.18) & (red < 0.96) & ~ligand_mask
    if int(ligand_mask.sum()) < 25:
        return -1e9, "ligand_mask_missing"
    if int(protein_mask.sum()) < 25:
        return -1e9, "protein_mask_missing"

    ligand_center = _mask_center(ligand_mask)
    protein_center = _mask_center(protein_mask)
    delta = protein_center - ligand_center
    distance = float(np.linalg.norm(delta))
    if distance < 1e-6:
        return -1e9, "centers_overlap"
    height = float(image.shape[0])
    width = float(image.shape[1])
    down = float(delta[0]) / distance
    sideways = abs(float(delta[1])) / distance
    protein_lower_half = float(protein_center[0]) / max(height, 1.0)
    ligand_centered = 1.0 - abs(float(ligand_center[1]) - width / 2.0) / max(width / 2.0, 1.0)
    score = down * 2.0 - sideways * 0.7 + protein_lower_half * 0.35 + ligand_centered * 0.15
    return score, "ok"


def _mask_center(mask: np.ndarray) -> np.ndarray:
    coords = np.argwhere(mask)
    if len(coords) == 0:
        return np.asarray([0.0, 0.0], dtype=float)
    return coords.mean(axis=0)


def _axis_id(label: str) -> str:
    try:
        index = int(label.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        index = 1
    return f"#{90 + max(1, min(index, 80))}"


def _camera_center(camera_view: CameraView) -> tuple[float, float, float]:
    return camera_view.focus


def _point_spec(point: np.ndarray) -> str:
    return ",".join(f"{float(value):.4f}" for value in point)


def _to_tuple(values: np.ndarray) -> tuple[float, float, float]:
    return tuple(float(x) for x in values[:3])


def _unit(values: np.ndarray) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm < 1e-12:
        return np.asarray([1.0, 0.0, 0.0], dtype=float)
    return vector / norm


def _normalize_element(value: str) -> str:
    text = "".join(ch for ch in str(value).strip() if ch.isalpha())
    if not text:
        return "C"
    if len(text) >= 2 and text[:2].upper() in VDW_RADII:
        return text[:2].upper()
    return text[0].upper()


def _validate_values(name: str, values: Iterable[str], allowed: set[str]) -> list[str]:
    result = [str(value).strip() for value in values if str(value).strip()]
    invalid = [value for value in result if value not in allowed]
    if invalid:
        raise ValueError(f"Unsupported {name}(s): {invalid}. Allowed: {sorted(allowed)}")
    if not result:
        raise ValueError(f"At least one {name} is required")
    return result


def _group_tasks_by_sample_and_view(tasks: Iterable[RenderTask]) -> list[list[RenderTask]]:
    groups: dict[tuple[Path, str], list[RenderTask]] = {}
    for task in tasks:
        groups.setdefault((task.sample_dir, task.view), []).append(task)
    result: list[list[RenderTask]] = []
    for group in groups.values():
        if group and group[0].camera_view is not None:
            for start in range(0, len(group), MAX_CLEAR_VIEWS_PER_PROCESS):
                result.append(group[start : start + MAX_CLEAR_VIEWS_PER_PROCESS])
        else:
            result.append(group)
    return result


def _result(
    task: RenderTask,
    status: str,
    *,
    script_path: str | Path | None = None,
    returncode: int | None = None,
    stderr_tail: str = "",
    image_rotation_degrees: float | None = None,
    image_orientation_status: str = "",
) -> RenderResult:
    camera = task.camera_view
    return RenderResult(
        sample_id=task.sample_id,
        view=task.view,
        angle=task.angle,
        script_path=str(script_path or task.script_path),
        image_path=str(task.image_path),
        status=status,
        returncode=returncode,
        stderr_tail=stderr_tail,
        camera_score=camera.score if camera else None,
        ligand_occluded_fraction=camera.ligand_occluded_fraction if camera else None,
        center_line_blocked=camera.center_line_blocked if camera else None,
        camera_direction=",".join(f"{value:.6f}" for value in camera.direction) if camera else "",
        camera_selection_tier=camera.selection_tier if camera else "",
        interest_occluded_fraction=camera.interest_occluded_fraction if camera else None,
        key_occluded_fraction=camera.key_occluded_fraction if camera else None,
        image_rotation_degrees=image_rotation_degrees,
        image_orientation_status=image_orientation_status,
    )


def _tail(text: str, max_chars: int = 600) -> str:
    compact = " ".join(text.split())
    return compact[-max_chars:]
