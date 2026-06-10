import logging
from pathlib import Path
from typing import Any

from .io import tree_dir


logger = logging.getLogger(__name__)


def discover_project_files(project_path: str) -> dict[str, Any]:
    project_root = Path(project_path).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise FileNotFoundError(f"Project path does not exist or is not a directory: {project_root}")

    tree_dir(project_root)

    pic_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
    pic_dir = project_root / "pics"
    if not pic_dir.exists() or not pic_dir.is_dir():
        raise FileNotFoundError(f"Could not find picture directory: {pic_dir}")

    # Prefer pics/figures/ subdirectory if it exists, otherwise scan pics/ root
    figures_dir = pic_dir / "figures"
    if figures_dir.exists() and figures_dir.is_dir():
        pic_search_dir = figures_dir
        logger.info("Found figures subdirectory, scanning: %s", pic_search_dir)
    else:
        pic_search_dir = pic_dir

    pic_abs_dirs = sorted(
        str(pic_path.resolve())
        for pic_path in pic_search_dir.rglob("*")
        if pic_path.is_file() and pic_path.suffix.lower() in pic_exts
    )
    if len(pic_abs_dirs) == 0:
        raise FileNotFoundError(f"No image files found in {pic_dir}")

    script_exts = {".py", ".r", ".R", ".ipynb", ".sh", ".jl", ".m"}
    script_dir = project_root / "scripts"

    script_abs_dirs: list[str] = []
    if not script_dir.exists() or not script_dir.is_dir():
        logger.info("No scripts directory found under %s, proceeding without script context.", project_root)
    else:
        script_files = sorted(
            script_path
            for script_path in script_dir.rglob("*")
            if script_path.is_file() and script_path.suffix in script_exts
        )
        script_abs_dirs = [str(sf.resolve()) for sf in script_files]
        if len(script_abs_dirs) == 0:
            logger.info("No script files found in %s, proceeding without script context.", script_dir)

    logger.info(
        "Discovered %s images and %s scripts: %s",
        len(pic_abs_dirs),
        len(script_abs_dirs),
        ", ".join(Path(s).name for s in script_abs_dirs) if script_abs_dirs else "<none>",
    )

    return {
        "pic_abs_dirs": pic_abs_dirs,
        "script_abs_dirs": script_abs_dirs,
    }
