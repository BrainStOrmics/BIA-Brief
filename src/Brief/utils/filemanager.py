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

    pic_abs_dirs = sorted(
        str(pic_path.resolve())
        for pic_path in pic_dir.rglob("*")
        if pic_path.is_file() and pic_path.suffix.lower() in pic_exts
    )
    if len(pic_abs_dirs) == 0:
        raise FileNotFoundError(f"No image files found in {pic_dir}")

    script_exts = {".py", ".r", ".R", ".ipynb", ".sh", ".jl", ".m"}
    script_dir = project_root / "scripts"

    script_abs_dir = ""
    if not script_dir.exists() or not script_dir.is_dir():
        logger.info("No scripts directory found under %s, proceeding without script context.", project_root)
    else:
        script_files = sorted(
            script_path
            for script_path in script_dir.rglob("*")
            if script_path.is_file() and script_path.suffix in script_exts
        )
        if len(script_files) == 0:
            logger.info("No script files found in %s, proceeding without script context.", script_dir)
        else:
            script_abs_dir = str(script_files[0].resolve())
            if len(script_files) > 1:
                logger.warning(
                    "Found %s script files in %s. Using the first one: %s",
                    len(script_files),
                    script_dir,
                    script_abs_dir,
                )

    logger.info(
        "Discovered %s images and script context: %s",
        len(pic_abs_dirs),
        script_abs_dir if len(script_abs_dir) > 0 else "<none>",
    )

    return {
        "pic_abs_dirs": pic_abs_dirs,
        "script_abs_dir": script_abs_dir,
    }
