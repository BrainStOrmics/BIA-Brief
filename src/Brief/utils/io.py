import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

def check_file_exists(file_path):
    try:
        with open(file_path, "rb"):
            return True
    except FileNotFoundError:
        return False


def check_image_exists(image_path):
    return check_file_exists(image_path)

# local image to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    return image_base64


def _trim_image_whitespace(image, threshold: int = 245):
    """Crop near-white margins from a figure when possible."""
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    rgb_image = image.convert("RGB")
    background = Image.new("RGB", rgb_image.size, (255, 255, 255))
    diff = ImageChops.difference(rgb_image, background)
    diff = ImageOps.grayscale(diff)
    mask = diff.point(lambda pixel: 255 if pixel > (255 - threshold) else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)


def _encode_image_with_budget(image, *, max_input_chars: int, prefer_lossless: bool = True):
    """Encode an image into base64 while staying under a request-size budget."""
    candidate = image

    def _to_bytes(img, fmt: str, **save_kwargs):
        buffer = BytesIO()
        img.save(buffer, format=fmt, **save_kwargs)
        return buffer.getvalue()

    def _to_base64(img, fmt: str, **save_kwargs):
        encoded_bytes = _to_bytes(img, fmt, **save_kwargs)
        encoded_text = base64.b64encode(encoded_bytes).decode("utf-8")
        return encoded_text, encoded_bytes

    def _try_png(img):
        encoded_text, encoded_bytes = _to_base64(img, "PNG", optimize=True)
        return encoded_text, encoded_bytes, "image/png"

    def _try_jpeg(img):
        rgb_image = img.convert("RGB")
        for quality in (92, 88, 84, 80, 76, 72, 68, 64, 60):
            encoded_text, encoded_bytes = _to_base64(
                rgb_image,
                "JPEG",
                quality=quality,
                optimize=True,
            )
            if len(encoded_text) <= max_input_chars:
                return encoded_text, encoded_bytes, "image/jpeg"
        encoded_text, encoded_bytes = _to_base64(rgb_image, "JPEG", quality=60, optimize=True)
        return encoded_text, encoded_bytes, "image/jpeg"

    # First try lossless PNG.
    png_text, png_bytes, png_mime = _try_png(candidate)
    if len(png_text) <= max_input_chars and prefer_lossless:
        return png_text, png_mime

    # Iteratively shrink the figure until the payload fits.
    current = candidate
    for scale in (0.92, 0.84, 0.76, 0.68, 0.60, 0.52, 0.44):
        new_width = max(1, int(current.width * scale))
        new_height = max(1, int(current.height * scale))
        current = current.resize((new_width, new_height), Image.Resampling.LANCZOS)

        png_text, png_bytes, png_mime = _try_png(current)
        if len(png_text) <= max_input_chars:
            return png_text, png_mime

        jpeg_text, jpeg_bytes, jpeg_mime = _try_jpeg(current)
        if len(jpeg_text) <= max_input_chars:
            return jpeg_text, jpeg_mime

    # Return the smallest attempt we have; caller can decide whether to fail.
    jpeg_text, jpeg_bytes, jpeg_mime = _try_jpeg(current)
    if len(jpeg_text) < len(png_text):
        return jpeg_text, jpeg_mime
    return png_text, png_mime


def image_to_base64_for_llm(
    image_path,
    *,
    max_input_chars: int = 18_000_000,
    trim_whitespace: bool = True,
    max_side: int = 1600,
    prefer_lossless: bool = True,
):
    """Prepare a figure for multimodal LLM input and return (base64, mime_type)."""
    with Image.open(image_path) as image:
        working_image = image.copy()

    if trim_whitespace:
        working_image = _trim_image_whitespace(working_image)

    width, height = working_image.size
    longest_side = max(width, height)
    if longest_side > max_side:
        scale = max_side / float(longest_side)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        working_image = working_image.resize(new_size, Image.Resampling.LANCZOS)

    encoded_text, mime_type = _encode_image_with_budget(
        working_image,
        max_input_chars=max_input_chars,
        prefer_lossless=prefer_lossless,
    )
    return encoded_text, mime_type


# 帮我写一个代码，以文本形式读取代码文件
def read_code_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        code_content = file.read()
    return code_content


def load_report_template_file(report_template: str, project_path: str):
    """Resolve and read a report template file from absolute or relative path."""
    template_path = Path(report_template).expanduser()
    if template_path.is_absolute():
        candidate_paths = [template_path]
    else:
        candidate_paths = [
            Path.cwd() / template_path,
            Path(project_path).expanduser().resolve() / template_path,
        ]

    resolved_template_path = None
    for candidate in candidate_paths:
        candidate = candidate.resolve()
        if candidate.exists() and candidate.is_file():
            resolved_template_path = candidate
            break

    if resolved_template_path is None:
        raise FileNotFoundError(
            f"Could not find report template file: {report_template}. "
            f"Checked: {[str(path.resolve()) for path in candidate_paths]}"
        )

    with resolved_template_path.open("r", encoding="utf-8") as f:
        report_template_text = f.read()

    return report_template_text, str(resolved_template_path)

def tree_dir(
        target_dir, 
        prefix: str = '',
        exclude_dirs: list[str] = None):
    "print directory tree"
    if exclude_dirs is None:
        # Exclude unused directories
        exclude_dirs = ['__pycache__', 'venv', '.venv']
        
    path = Path(target_dir)
    contents = sorted([p for p in path.iterdir() if p.name not in exclude_dirs])
    
    pointers = ['├── '] * (len(contents) - 1) + ['└── ']
    for pointer, child in zip(pointers, contents):
        print(prefix + pointer + child.name)
        if child.is_dir():
            extension = '│   ' if pointer == '├── ' else '    '
            tree_dir(child, prefix + extension, exclude_dirs)

